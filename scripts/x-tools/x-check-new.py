#!/usr/bin/env python3
"""
x-check-new.py — Parse scraped X profile markdown, extract tweets, deduplicate against state.

Usage:
    cat scraped.md | python3 x-check-new.py --handle @karpathy --state state.json
    cat scraped.md | python3 x-check-new.py --handle @karpathy --state state.json --update-state

Outputs JSON: {"hasNew": true/false, "newTweets": [...], "handle": "@..."}
"""

import argparse, json, re, sys, os, hashlib
from datetime import datetime, timezone


def extract_tweets(markdown: str, handle: str) -> list[dict]:
    """Extract tweets from Brightdata's scraped X profile markdown.

    Brightdata output pattern per tweet:
        [handle] · [date link like /handle/status/ID]
        <tweet text, possibly multi-line>
        <optional "Show more">
        <optional Quote block>
        <engagement: numbers on separate lines>
        [analytics link like /handle/status/ID/analytics]
    """
    tweets = []
    lines = markdown.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect tweet start: a line with status link containing tweet ID
        # Pattern: [Mon DD, YYYY](/handle/status/TWEET_ID) or [DD mon.](/handle/status/TWEET_ID)
        status_match = re.search(r'\(/\w+/status/(\d+)\)', line)
        if status_match and 'analytics' not in line:
            tweet_id = status_match.group(1)

            # Extract date text
            date_text = re.sub(r'\[|\]\(.*?\)', '', line).strip()

            # Collect tweet text lines until we hit engagement numbers or next tweet
            i += 1
            text_lines = []
            while i < len(lines):
                l = lines[i].strip()

                # Stop at analytics link (end of tweet)
                if re.search(r'/status/\d+/analytics', l):
                    i += 1
                    break

                # Stop at next tweet's status link
                if re.search(r'\(/\w+/status/(\d+)\)', l) and 'analytics' not in l:
                    break

                # Skip engagement number lines (standalone numbers like "1.7K", "60K", "10M")
                if re.match(r'^[\d,.]+\s*[KMkm]?$', l):
                    i += 1
                    continue

                # Skip markdown link-only lines (navigation)
                if re.match(r'^\\\[', l) or l == '' or re.match(r'^\]\(/', l):
                    i += 1
                    continue

                # Skip "Show more"
                if l.lower() in ('show more', 'mostrar más'):
                    i += 1
                    continue

                # Skip image markers
                if l in ('Image', 'Video'):
                    i += 1
                    continue

                text_lines.append(l)
                i += 1

            text = '\n'.join(text_lines).strip()
            # Clean up remaining markdown artifacts
            text = re.sub(r'\\\[|\\\]', '', text)
            text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)  # [text](link) → text
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()

            if len(text) > 10:
                tweets.append({
                    'id': tweet_id,
                    'date': date_text,
                    'text': text,
                    'url': f'https://x.com/{handle.lstrip("@")}/status/{tweet_id}',
                    'hash': hashlib.sha256(tweet_id.encode()).hexdigest()[:16],
                })
            continue

        i += 1

    return tweets


def load_state(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"seenIds": {}, "lastCheck": None}


def save_state(path: str, state: dict):
    with open(path, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--handle', required=True, help='X handle e.g. @karpathy')
    parser.add_argument('--state', default='x-tracker-state.json')
    parser.add_argument('--update-state', action='store_true',
                        help='Mark new tweets as seen in state')
    parser.add_argument('--max', type=int, default=10, help='Max new tweets to return')
    args = parser.parse_args()

    markdown = sys.stdin.read()
    if not markdown.strip():
        print(json.dumps({"hasNew": False, "error": "empty input", "handle": args.handle}))
        sys.exit(0)

    # Check for "This account doesn't exist"
    if "This account doesn't exist" in markdown:
        print(json.dumps({"hasNew": False, "error": "account_not_found", "handle": args.handle}))
        sys.exit(1)

    state = load_state(args.state)
    handle_key = args.handle.lower().lstrip('@')
    seen = set(state.get("seenIds", {}).get(handle_key, []))

    all_tweets = extract_tweets(markdown, args.handle)
    new_tweets = [t for t in all_tweets if t['id'] not in seen][:args.max]

    if args.update_state and new_tweets:
        if "seenIds" not in state:
            state["seenIds"] = {}
        if handle_key not in state["seenIds"]:
            state["seenIds"][handle_key] = []
        state["seenIds"][handle_key].extend([t['id'] for t in new_tweets])
        # Keep last 200 IDs per handle
        state["seenIds"][handle_key] = state["seenIds"][handle_key][-200:]
        state["lastCheck"] = datetime.now(timezone.utc).isoformat()
        save_state(args.state, state)

    result = {
        "hasNew": len(new_tweets) > 0,
        "newCount": len(new_tweets),
        "totalScraped": len(all_tweets),
        "handle": args.handle,
        "newTweets": new_tweets,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
