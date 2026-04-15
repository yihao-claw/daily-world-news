#!/usr/bin/env python3
"""Send text/audio to Telegram. Usage:
  tg_send.py text <file> [--header HDR]
  tg_send.py voice <file> [--caption CAP]
"""
import os, sys, requests, argparse, pathlib

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "-1003767828002")
API = f"https://api.telegram.org/bot{TOKEN}"

def chunk(s, n=3800):
    parts, cur = [], []
    cur_len = 0
    for line in s.splitlines(keepends=True):
        if cur_len + len(line) > n and cur:
            parts.append("".join(cur)); cur=[]; cur_len=0
        cur.append(line); cur_len += len(line)
    if cur: parts.append("".join(cur))
    return parts

def send_text(path, header=None):
    body = pathlib.Path(path).read_text()
    if header: body = f"{header}\n\n{body}"
    for i, part in enumerate(chunk(body), 1):
        r = requests.post(f"{API}/sendMessage",
            data={"chat_id": CHAT, "text": part, "disable_web_page_preview": "true"}, timeout=30)
        r.raise_for_status()
        print(f"sent part {i} ({len(part)} chars)")

def send_voice(path, caption=None):
    with open(path, "rb") as f:
        r = requests.post(f"{API}/sendVoice",
            data={"chat_id": CHAT, "caption": caption or ""},
            files={"voice": f}, timeout=300)
    if r.status_code != 200:
        print(r.text); r.raise_for_status()
    print(f"sent voice {path}")

if __name__ == "__main__":
    mode = sys.argv[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--header")
    ap.add_argument("--caption")
    args = ap.parse_args(sys.argv[2:])
    if mode == "text": send_text(args.path, args.header)
    elif mode == "voice": send_voice(args.path, args.caption)
    else: sys.exit("mode must be text|voice")
