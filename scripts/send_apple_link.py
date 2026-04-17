#!/usr/bin/env python3
"""Poll iTunes Lookup API for today's episode, send Apple Podcasts link to Telegram.

Usage: send_apple_link.py [--date YYYY-MM-DD] [--max-wait-sec N]

Behavior:
  - Polls itunes.apple.com/lookup every 30s for up to --max-wait-sec (default 600).
  - Matches the first podcastEpisode whose releaseDate starts with the target date.
  - Sends Telegram message with episode title + trackViewUrl.
  - On timeout, falls back to the show URL.
"""
import os, sys, time, json, argparse, urllib.request, urllib.parse, datetime, requests

PODCAST_ID = 1888903136
SHOW_URL = "https://podcasts.apple.com/jp/podcast/ai-%E6%AF%8F%E6%97%A5%E6%96%B0%E8%81%9E/id1888903136?l=en-US"
LOOKUP_URL = f"https://itunes.apple.com/lookup?id={PODCAST_ID}&entity=podcastEpisode&limit=10"


def lookup_episode(date_str: str):
    req = urllib.request.Request(LOOKUP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    for item in data.get("results", []):
        if item.get("wrapperType") != "podcastEpisode":
            continue
        if (item.get("releaseDate") or "").startswith(date_str):
            return item
    return None


def send_telegram(text: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ.get("TELEGRAM_CHAT_ID", "-1003767828002")
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": text, "disable_web_page_preview": "false"},
        timeout=30,
    )
    r.raise_for_status()
    print(f"sent telegram ({len(text)} chars)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=os.environ.get("TODAY"))
    ap.add_argument("--max-wait-sec", type=int, default=600)
    ap.add_argument("--interval-sec", type=int, default=30)
    args = ap.parse_args()

    date = args.date or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    deadline = time.time() + args.max_wait_sec
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            ep = lookup_episode(date)
        except Exception as e:
            print(f"[{attempt}] lookup error: {e}", file=sys.stderr)
            ep = None
        if ep:
            title = ep.get("trackName", date)
            url = ep.get("trackViewUrl") or SHOW_URL
            text = f"🎙️ AI 每日新聞 EP — {date}\n{title}\n\n{url}"
            send_telegram(text)
            print(f"OK: episode found on attempt {attempt}")
            return
        remaining = int(deadline - time.time())
        print(f"[{attempt}] not yet indexed, sleeping {args.interval_sec}s ({remaining}s left)")
        time.sleep(args.interval_sec)

    print(f"timeout after {args.max_wait_sec}s — falling back to show URL", file=sys.stderr)
    text = f"🎙️ AI 每日新聞 EP — {date}\n（episode 連結未及時 index，先附節目首頁）\n\n{SHOW_URL}"
    send_telegram(text)


if __name__ == "__main__":
    main()
