#!/usr/bin/env python3
"""
build_dedup_digest.py — compact digest of the past 3 days' summaries for LLM dedup gate.

Replaces: "Read past 3 days' tech/world summaries" (~15K tokens)
With:     one ~1-2K digest of event titles + key numbers.

Usage:
    python3 scripts/build_dedup_digest.py tech   > summaries/YYYY-MM-DD-dedup-tech.txt
    python3 scripts/build_dedup_digest.py world  > summaries/YYYY-MM-DD-dedup-world.txt
"""
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
SKILL_DIR = Path(__file__).resolve().parent.parent
SUMMARIES = SKILL_DIR / "summaries"


def past_dates(n=3):
    today = datetime.now(JST).date()
    return [(today - timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(n)]


def extract_highlights(text: str, max_items: int = 25) -> list[str]:
    """Pull bold titles + any inline numbers/dates. One line per event."""
    items = []
    seen = set()
    # Bold titles: **...** (tech format) and •/- **...** (world format)
    for m in re.finditer(r"\*\*([^*\n]{3,120})\*\*", text):
        title = m.group(1).strip().strip("[]")
        # Skip section headers like "美洲", "今日頭條"
        if re.fullmatch(r"[\u4e00-\u9fff\s&/]+", title) and len(title) < 8:
            continue
        key = re.sub(r"\s+", "", title.lower())
        if key in seen:
            continue
        seen.add(key)
        # Look ahead ~200 chars for a key number (percentages, counts, prices)
        tail = text[m.end(): m.end() + 200]
        nums = re.findall(r"\d[\d,\.]*\s?(?:%|億|萬|人|美元|港元|日圓|元|％)", tail)
        snippet = " / ".join(nums[:3])
        items.append(f"- {title}" + (f"  [{snippet}]" if snippet else ""))
        if len(items) >= max_items:
            break
    return items


def build(kind: str) -> str:
    if kind not in ("tech", "world"):
        print(f"unknown kind: {kind}", file=sys.stderr)
        sys.exit(2)
    suffix = "-tech.md" if kind == "tech" else ".md"
    out = [f"# Past 3 days {kind} dedup digest", ""]
    for d in past_dates(3):
        path = SUMMARIES / f"{d}{suffix}"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        items = extract_highlights(text)
        if not items:
            continue
        out.append(f"## {d}")
        out.extend(items)
        out.append("")
    out.append("以上是過去 3 天已充分報導的故事，**預設一律不進新事區**。")
    out.append("有 1 句新 fact → 延續區（1 句封頂）；發生類別變化事件 → 深度區（每集最多 1 則）；")
    out.append("其他 → 直接刪除。詳見 SKILL.md「三區制」與「類別變化事件清單」。")
    return "\n".join(out)


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "tech"
    sys.stdout.write(build(kind))
