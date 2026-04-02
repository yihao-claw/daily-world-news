#!/usr/bin/env python3
"""Generate podcast RSS feed from summaries directory and upload to R2."""

import os
import re
import datetime
import subprocess
import sys
from email.utils import formatdate
from pathlib import Path

R2_BASE_URL = "https://pub-1bc6fb66c5ba4be1b405c18499c18bb0.r2.dev"
SUMMARIES_DIR = Path(__file__).parent.parent / "summaries"
UPLOAD_SCRIPT = Path(__file__).parent / "upload-r2.sh"

PODCAST_TITLE = "AI 每日新聞"
PODCAST_DESC = "每日精選國際時事與科技趨勢，AI 自動蒐集、整理、播報。涵蓋地緣政治、科技產業、加密貨幣等多元視角，讓你用 15 分鐘掌握世界動態。"
PODCAST_AUTHOR = "AI 每日新聞"
PODCAST_LANG = "zh-tw"
PODCAST_IMAGE = f"{R2_BASE_URL}/cover.jpg?v=3"
PODCAST_CATEGORY = "News"
PODCAST_SUBCATEGORY = "Daily News"
PODCAST_EMAIL = "zero5011@gmail.com"

RSS_HEADER = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>{PODCAST_TITLE}</title>
    <description>{PODCAST_DESC}</description>
    <language>{PODCAST_LANG}</language>
    <itunes:author>{PODCAST_AUTHOR}</itunes:author>
    <itunes:category text="{PODCAST_CATEGORY}">
      <itunes:category text="{PODCAST_SUBCATEGORY}"/>
    </itunes:category>
    <itunes:image href="{PODCAST_IMAGE}"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:owner>
      <itunes:name>{PODCAST_AUTHOR}</itunes:name>
      <itunes:email>{PODCAST_EMAIL}</itunes:email>
    </itunes:owner>
    <itunes:type>episodic</itunes:type>
    <link>{R2_BASE_URL}/feed.xml</link>
"""

RSS_FOOTER = """  </channel>
</rss>
"""


def xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def get_episode_date(filename: str):
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if match:
        return datetime.date.fromisoformat(match.group(1))
    return None


def extract_title(date_str: str) -> str:
    """Extract a concise title from Top 3 headlines in news summary."""
    md_path = SUMMARIES_DIR / f"{date_str}.md"
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")[:4000]
        
        # Extract bold headlines from Top 3 section: **headline text**
        # These appear as numbered list items or bullet points
        top3_match = re.search(r'頭條.*?\n(.*?)(?=\n---|\n## [^🔥])', text, re.DOTALL)
        if top3_match:
            section = top3_match.group(1)
            # Extract first bold phrase from each item
            bolds = re.findall(r'\*\*([^*]+?)\*\*', section)
            topics = []
            seen = set()
            for b in bolds:
                if len(topics) >= 3:
                    break
                # Take just the short headline part (before comma/dash details)
                short = re.split(r'[，,—;；]', b)[0].strip()
                # Remove leading numbers like "1. " or "至少 1"
                short = re.sub(r'^\d+\.?\s*', '', short).strip()
                if len(short) < 5:
                    continue
                if len(short) > 30:
                    short = short[:28] + "…"
                # Deduplicate similar topics
                key = short[:10]
                if key in seen:
                    continue
                seen.add(key)
                topics.append(short)
            if topics:
                return "｜".join(topics)

    return f"{date_str} 每日新聞"


def get_episode_description(date_str: str) -> str:
    md_path = SUMMARIES_DIR / f"{date_str}-podcast.md"
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")[:500]
        text = re.sub(r"[#*_\[\]()]", "", text).strip()[:300]
        return xml_escape(text)
    return xml_escape(f"{date_str} 每日新聞 Podcast")


def estimate_duration(file_size: int) -> str:
    # edge-tts outputs ~48kbps mp3 (6000 bytes/sec)
    seconds = max(1, file_size // 6000)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def get_canonical_mp3(date_str: str) -> Path | None:
    """Return the single canonical MP3 for a date. Prefer YYYY-MM-DD.mp3 over parts/podcast variants."""
    main = SUMMARIES_DIR / f"{date_str}.mp3"
    if main.exists() and main.stat().st_size > 0:
        return main
    # Fallback to -podcast.mp3
    podcast = SUMMARIES_DIR / f"{date_str}-podcast.mp3"
    if podcast.exists() and podcast.stat().st_size > 0:
        return podcast
    return None


def build_item(date_str: str, mp3_file: Path) -> str:
    file_size = mp3_file.stat().st_size
    if file_size == 0:
        return ""

    date = datetime.date.fromisoformat(date_str)
    # 台灣時間 (UTC+8) 早上 7 點發布
    pub_date = formatdate(
        datetime.datetime.combine(date, datetime.time(7, 0),
                                   tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp(),
        usegmt=True
    )

    # Always use consistent key format: podcasts/YYYY-MM-DD.mp3
    url = f"{R2_BASE_URL}/podcasts/{date_str}.mp3"
    title = xml_escape(extract_title(date_str))
    desc = get_episode_description(date_str)

    return f"""    <item>
      <title>{title}</title>
      <description>{desc}</description>
      <enclosure url="{url}" length="{file_size}" type="audio/mpeg"/>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="true">{url}</guid>
      <itunes:duration>{estimate_duration(file_size)}</itunes:duration>
      <itunes:episode>{int(date_str.replace('-', ''))}</itunes:episode>
    </item>
"""


def main():
    # Find all unique dates that have MP3s
    dates = set()
    for f in SUMMARIES_DIR.glob("*.mp3"):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if m:
            dates.add(m.group(1))

    items = []
    for date_str in sorted(dates, reverse=True):
        mp3 = get_canonical_mp3(date_str)
        if mp3:
            item = build_item(date_str, mp3)
            if item:
                items.append(item)

    rss = RSS_HEADER + "\n".join(items) + RSS_FOOTER

    feed_path = SUMMARIES_DIR / "feed.xml"
    feed_path.write_text(rss, encoding="utf-8")
    print(f"✅ RSS feed generated: {feed_path} ({len(items)} episodes)")

    # Upload to R2
    result = subprocess.run(
        ["bash", str(UPLOAD_SCRIPT), str(feed_path), "feed.xml"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"✅ Uploaded to R2: {R2_BASE_URL}/feed.xml")
    else:
        print(f"❌ Upload failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
