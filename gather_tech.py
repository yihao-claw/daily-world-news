#!/usr/bin/env python3
"""
Tech news gatherer — deterministic data collection layer.
Fetches RSS, GitHub releases, Reddit hot posts.
Scores, deduplicates, and outputs structured JSON for LLM summarization.

Usage:
    python3 gather_tech.py [--sources TECH_SOURCES.json] [--yesterday summaries/YYYY-MM-DD-tech.md] [--output raw_tech.json]
"""

import argparse
import json
import sys
import time
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests
from thefuzz import fuzz

JST = timezone(timedelta(hours=9))
NOW = datetime.now(timezone.utc)
CUTOFF_48H = NOW - timedelta(hours=48)
CUTOFF_7D = NOW - timedelta(days=7)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "DailyTechDigest/1.0"})
REQUEST_TIMEOUT = 15


# ─── Helpers ───

def parse_date(entry):
    """Extract datetime from a feed entry, return UTC datetime or None."""
    for field in ("published_parsed", "updated_parsed"):
        t = entry.get(field)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    # Try parsing date strings
    for field in ("published", "updated"):
        s = entry.get(field, "")
        if s:
            for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                         "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(s.strip(), fmt).astimezone(timezone.utc)
                except Exception:
                    continue
    return None


def clean_html(text):
    """Strip HTML tags."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def title_hash(title):
    """Normalize title for dedup."""
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", title.lower())
    return t


# ─── Fetchers ───

def fetch_rss(source):
    """Fetch and parse one RSS feed. Returns list of article dicts."""
    articles = []
    try:
        resp = SESSION.get(source["url"], timeout=REQUEST_TIMEOUT)
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:20]:  # cap per feed
            pub = parse_date(entry)
            if pub and pub < CUTOFF_48H:
                continue  # too old
            title = clean_html(entry.get("title", ""))
            if not title:
                continue
            link = entry.get("link", "")
            summary = clean_html(entry.get("summary", ""))[:500]
            articles.append({
                "source_id": source["id"],
                "source_name": source["name"],
                "source_type": "rss",
                "title": title,
                "url": link,
                "summary": summary,
                "published": pub.isoformat() if pub else None,
                "topics": source.get("topics", []),
                "priority": source.get("priority", False),
            })
    except Exception as e:
        print(f"  ⚠ RSS error [{source['name']}]: {e}", file=sys.stderr)
    return articles


def fetch_github_releases(repo_cfg):
    """Fetch recent releases from a GitHub repo via Atom feed."""
    articles = []
    repo = repo_cfg["repo"]
    url = f"https://github.com/{repo}/releases.atom"
    try:
        resp = SESSION.get(url, timeout=REQUEST_TIMEOUT)
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:5]:
            pub = parse_date(entry)
            if pub and pub < CUTOFF_7D:
                continue
            title = clean_html(entry.get("title", ""))
            if not title:
                continue
            link = entry.get("link", "")
            summary = clean_html(entry.get("summary", ""))[:300]
            # Skip trunk/nightly/CI commits — only real releases
            if re.search(r"(trunk/|nightly|^[0-9a-f]{7,40}$)", title, re.IGNORECASE):
                continue
            articles.append({
                "source_id": repo_cfg["id"],
                "source_name": repo,
                "source_type": "github",
                "title": f"[GitHub] {repo}: {title}",
                "url": link,
                "summary": summary,
                "published": pub.isoformat() if pub else None,
                "topics": repo_cfg.get("topics", []),
                "priority": repo_cfg.get("priority", False),
            })
    except Exception as e:
        print(f"  ⚠ GitHub error [{repo}]: {e}", file=sys.stderr)
    return articles


def fetch_reddit(sub_cfg):
    """Fetch hot posts from a subreddit."""
    articles = []
    sub = sub_cfg.get("subreddit") or sub_cfg.get("sub")
    min_score = sub_cfg.get("min_score", 100)
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit=15"
    try:
        resp = SESSION.get(url, timeout=REQUEST_TIMEOUT,
                          headers={"User-Agent": "DailyTechDigest/1.0"})
        data = resp.json()
        for post in data.get("data", {}).get("children", []):
            d = post["data"]
            created = datetime.fromtimestamp(d["created_utc"], tz=timezone.utc)
            if created < CUTOFF_48H:
                continue
            score = d.get("score", 0)
            if score < min_score:
                continue
            title = d.get("title", "")
            permalink = f"https://reddit.com{d.get('permalink', '')}"
            selftext = (d.get("selftext", "") or "")[:300]
            articles.append({
                "source_id": f"reddit-{sub}",
                "source_name": f"r/{sub}",
                "source_type": "reddit",
                "title": title,
                "url": permalink,
                "summary": selftext,
                "published": created.isoformat(),
                "topics": sub_cfg.get("topics", []),
                "priority": False,
                "reddit_score": score,
            })
    except Exception as e:
        print(f"  ⚠ Reddit error [r/{sub}]: {e}", file=sys.stderr)
    return articles


# ─── Scoring ───

def score_article(article, yesterday_titles):
    """Apply deterministic scoring. Returns updated article with quality_score."""
    base = 5
    s = base

    # Priority source
    if article.get("priority"):
        s += 3

    # Recency (within 24h)
    if article.get("published"):
        try:
            pub = datetime.fromisoformat(article["published"])
            if (NOW - pub).total_seconds() < 86400:
                s += 2
        except Exception:
            pass

    # Reddit score bonus
    reddit_score = article.get("reddit_score", 0)
    if reddit_score > 500:
        s += 3
    elif reddit_score > 200:
        s += 1

    # GitHub trending bonus
    if article.get("source_type") == "github":
        s += 3

    # Yesterday duplicate penalty
    t_hash = title_hash(article["title"])
    for yt in yesterday_titles:
        if fuzz.ratio(t_hash, title_hash(yt)) > 85:
            s -= 5
            article["is_followup"] = True
            break

    article["quality_score"] = max(0, s)
    return article


# ─── Deduplication ───

def deduplicate(articles, threshold=85):
    """Remove near-duplicate articles by title similarity."""
    seen = []
    unique = []
    for a in articles:
        t = title_hash(a["title"])
        is_dup = False
        for st in seen:
            if fuzz.ratio(t, st) > threshold:
                is_dup = True
                break
        if not is_dup:
            seen.append(t)
            unique.append(a)
    return unique


# ─── Yesterday loader ───

def load_yesterday_titles(path):
    """Extract titles from yesterday's tech summary markdown."""
    titles = []
    if not path or not Path(path).exists():
        return titles
    text = Path(path).read_text(encoding="utf-8")
    # Extract bold titles: **Title**
    for m in re.finditer(r"\*\*\[?([^\]*]+)\]?\*\*", text):
        titles.append(m.group(1))
    # Extract ### headers
    for m in re.finditer(r"^###?\s+\d*\.?\s*(.+)", text, re.MULTILINE):
        titles.append(m.group(1).strip())
    return titles


# ─── Topic classification ───

def classify_topics(articles):
    """Group articles by primary topic and enforce diversity."""
    topic_groups = {}
    for a in articles:
        primary = a["topics"][0] if a.get("topics") else "frontier-tech"
        topic_groups.setdefault(primary, []).append(a)
    return topic_groups


# ─── Main ───

def main():
    parser = argparse.ArgumentParser(description="Gather tech news from configured sources")
    parser.add_argument("--sources", default="TECH_SOURCES.json", help="Sources config file")
    parser.add_argument("--yesterday", default=None, help="Yesterday's tech summary .md file")
    parser.add_argument("--output", default="raw_tech.json", help="Output JSON file")
    args = parser.parse_args()

    # Load sources
    sources_path = Path(args.sources)
    if not sources_path.exists():
        # Try relative to script dir
        sources_path = Path(__file__).parent / args.sources
    with open(sources_path) as f:
        config = json.load(f)

    rss_sources = [s for s in config.get("sources", []) if s.get("type") == "rss"]
    github_repos = config.get("github_repos", [])
    reddit_subs = config.get("reddit_subs", [])
    web_queries = config.get("web_search_queries", {})

    yesterday_titles = load_yesterday_titles(args.yesterday)

    all_articles = []
    stats = {"rss_fetched": 0, "rss_errors": 0, "github_fetched": 0, "reddit_fetched": 0}

    # Fetch RSS (parallel, 8 workers)
    print(f"📡 Fetching {len(rss_sources)} RSS feeds...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_rss, s): s for s in rss_sources}
        for future in as_completed(futures):
            articles = future.result()
            if articles:
                stats["rss_fetched"] += 1
                all_articles.extend(articles)
            else:
                stats["rss_errors"] += 1

    # Fetch GitHub releases (parallel)
    print(f"📦 Checking {len(github_repos)} GitHub repos...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_github_releases, r): r for r in github_repos}
        for future in as_completed(futures):
            articles = future.result()
            if articles:
                stats["github_fetched"] += 1
                all_articles.extend(articles)

    # Fetch Reddit
    print(f"🔥 Checking {len(reddit_subs)} subreddits...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_reddit, s): s for s in reddit_subs}
        for future in as_completed(futures):
            articles = future.result()
            if articles:
                stats["reddit_fetched"] += 1
                all_articles.extend(articles)

    print(f"📊 Raw articles collected: {len(all_articles)}", file=sys.stderr)

    # Score
    all_articles = [score_article(a, yesterday_titles) for a in all_articles]

    # Deduplicate
    all_articles = deduplicate(all_articles)
    print(f"📊 After dedup: {len(all_articles)}", file=sys.stderr)

    # Filter by min threshold
    all_articles = [a for a in all_articles if a["quality_score"] >= 5]
    print(f"📊 After score filter (≥5): {len(all_articles)}", file=sys.stderr)

    # Sort by score desc
    all_articles.sort(key=lambda x: x["quality_score"], reverse=True)

    # Group by topic
    topic_groups = classify_topics(all_articles)

    # Build output
    output = {
        "generated_at": NOW.isoformat(),
        "today_jst": datetime.now(JST).strftime("%Y-%m-%d"),
        "stats": stats,
        "total_articles": len(all_articles),
        "topic_distribution": {k: len(v) for k, v in topic_groups.items()},
        "web_search_queries": web_queries,
        "articles_by_topic": {},
        "top_articles": all_articles[:30],  # Top 30 for LLM to pick from
    }

    # Include top articles per topic (for diversity)
    topic_limits = {
        "llm": 6, "ai-agent": 5, "crypto": 5, "frontier-tech": 6,
        "space-science": 3, "consumer-tech": 3, "cybersecurity": 3, "biotech": 2
    }
    for topic, arts in topic_groups.items():
        limit = topic_limits.get(topic, 4)
        output["articles_by_topic"][topic] = arts[:limit]

    # Write output
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Output written to {output_path}", file=sys.stderr)
    print(f"   Topics: {', '.join(f'{k}({v})' for k,v in output['topic_distribution'].items())}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
