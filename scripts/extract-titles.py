#!/usr/bin/env python3
"""Extract episode titles from podcast scripts."""
import re, os, glob
from pathlib import Path

SUMMARIES = Path(__file__).parent.parent / "summaries"

for f in sorted(SUMMARIES.glob("*-podcast.md")):
    date = re.search(r"\d{4}-\d{2}-\d{2}", f.name).group()
    text = f.read_text(encoding="utf-8")[:2000]
    
    # Remove opening greeting (first ~200 chars usually)
    # Look for key topic mentions after greeting
    # Strategy: find sentences with key news topics
    lines = text.split("。")
    topics = []
    skip_words = {"早安", "今天是", "歡迎", "大家好", "嗨", "你好", "收聽", "星期", "月", "日"}
    
    for line in lines[1:8]:  # skip first sentence (greeting), check next 7
        line = line.strip()
        if len(line) < 10:
            continue
        if any(w in line[:20] for w in skip_words):
            continue
        # Clean up
        line = re.sub(r'[，、。！？\s]+$', '', line)
        if len(line) > 8:
            topics.append(line[:40])
        if len(topics) >= 2:
            break
    
    title = "｜".join(topics) if topics else f"{date} 每日新聞"
    print(f"{date} | {title[:80]}")
