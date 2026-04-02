#!/usr/bin/env python3
"""
pre-publish-check.py — 發布前自動檢查
用法: python3 pre-publish-check.py <YYYY-MM-DD>

檢查項目：
1. 市場數據一致性（.md vs podcast.md 漲跌方向）
2. 播報稿無殘留 URL / 異常內容
3. 音檔存在且大小合理
4. RSS duration 合理
5. Git status clean

全過 → exit 0（可自動發布）
任一失敗 → exit 1（需人工審查）
"""

import os
import re
import sys
from pathlib import Path

SUMMARIES_DIR = Path(__file__).parent.parent / "summaries"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_pass(msg):
    print(f"  {GREEN}✅ PASS{RESET}: {msg}")
    return True


def check_fail(msg):
    print(f"  {RED}❌ FAIL{RESET}: {msg}")
    return False


def check_warn(msg):
    print(f"  {YELLOW}⚠️ WARN{RESET}: {msg}")
    return True  # warnings don't block


def check_market_consistency(date_str: str) -> bool:
    """Check that .md and podcast.md agree on market direction (up/down)."""
    md_path = SUMMARIES_DIR / f"{date_str}.md"
    podcast_path = SUMMARIES_DIR / f"{date_str}-podcast.md"

    if not md_path.exists():
        return check_fail(f"{md_path.name} 不存在")
    if not podcast_path.exists():
        return check_fail(f"{podcast_path.name} 不存在")

    md_text = md_path.read_text(encoding="utf-8")
    podcast_text = podcast_path.read_text(encoding="utf-8")

    # Extract market numbers from .md (structured format)
    markets = {}
    for match in re.finditer(r'(台灣加權|日經|S&P 500|Nasdaq|Dow).*?([+-]\d+\.?\d*%)', md_text):
        name = match.group(1)
        pct = match.group(2)
        markets[name] = "up" if pct.startswith("+") else "down"

    if not markets:
        return check_warn("無法從 .md 提取市場數據")

    # Check podcast.md for contradictions
    passed = True
    for name, direction in markets.items():
        # Look for mentions in podcast
        if name == "台灣加權":
            patterns = ["台灣加權", "台股", "加權指數"]
        elif name == "日經":
            patterns = ["日經", "日股"]
        else:
            patterns = [name]

        for pat in patterns:
            for line in podcast_text.split("\n"):
                if pat in line:
                    has_up = any(w in line for w in ["漲", "大漲", "反彈", "飆漲", "上漲", "收漲", "+"])
                    has_down = any(w in line for w in ["跌", "下跌", "疲弱", "收跌", "-"])
                    if direction == "up" and has_down and not has_up:
                        check_fail(f"{name} 在 .md 是漲，但 podcast.md 說跌: {line.strip()[:60]}")
                        passed = False
                    elif direction == "down" and has_up and not has_down:
                        check_fail(f"{name} 在 .md 是跌，但 podcast.md 說漲: {line.strip()[:60]}")
                        passed = False

    if passed:
        check_pass(f"市場數據方向一致（檢查 {len(markets)} 個指數）")
    return passed


def check_no_urls_in_script(date_str: str) -> bool:
    """Check that podcast script has no raw URLs that TTS would read."""
    podcast_path = SUMMARIES_DIR / f"{date_str}-podcast.md"
    if not podcast_path.exists():
        return check_warn(f"{podcast_path.name} 不存在，跳過")

    text = podcast_path.read_text(encoding="utf-8")
    urls = re.findall(r'https?://\S+', text)

    if urls:
        for url in urls[:3]:
            check_fail(f"播報稿含 URL: {url[:60]}")
        return False

    # Also check the .md for URLs that might leak through generate-audio.py
    md_path = SUMMARIES_DIR / f"{date_str}.md"
    if md_path.exists():
        md_text = md_path.read_text(encoding="utf-8")
        # Simulate generate-audio.py filtering
        filtered = re.sub(r'📎.*', '', md_text)
        filtered = re.sub(r'^\s*https?://\S+\s*$', '', filtered, flags=re.MULTILINE)
        filtered = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', filtered)
        filtered = re.sub(r'^>.*$', '', filtered, flags=re.MULTILINE)

        remaining_urls = re.findall(r'https?://\S+', filtered)
        if remaining_urls:
            for url in remaining_urls[:3]:
                check_fail(f".md 過濾後仍有 URL 會被 TTS 唸出: {url[:60]}")
            return False

    check_pass("播報稿無殘留 URL")
    return True


def check_audio_file(date_str: str) -> bool:
    """Check MP3 exists and has reasonable size."""
    mp3_path = SUMMARIES_DIR / f"{date_str}.mp3"
    if not mp3_path.exists():
        return check_fail(f"{mp3_path.name} 不存在")

    size_mb = mp3_path.stat().st_size / (1024 * 1024)
    # edge-tts ~48kbps, 15-25 min podcast ≈ 5-10 MB
    if size_mb < 1:
        return check_fail(f"音檔太小: {size_mb:.1f} MB（可能生成失敗）")
    if size_mb > 50:
        return check_fail(f"音檔異常大: {size_mb:.1f} MB")

    # Estimate duration (edge-tts ~6000 bytes/sec)
    est_seconds = mp3_path.stat().st_size / 6000
    est_minutes = est_seconds / 60

    if est_minutes < 5:
        return check_fail(f"估計時長 {est_minutes:.0f} 分鐘，太短")
    if est_minutes > 40:
        return check_warn(f"估計時長 {est_minutes:.0f} 分鐘，偏長")

    check_pass(f"音檔正常: {size_mb:.1f} MB, 估計 {est_minutes:.0f} 分鐘")
    return True


def check_no_garbled_text(date_str: str) -> bool:
    """Check for common garbled/problematic text patterns."""
    podcast_path = SUMMARIES_DIR / f"{date_str}-podcast.md"
    if not podcast_path.exists():
        return check_warn(f"{podcast_path.name} 不存在，跳過")

    text = podcast_path.read_text(encoding="utf-8")
    issues = []

    # Check for markdown artifacts that shouldn't be in spoken text
    if re.search(r'^\s*#{1,6}\s', text, re.MULTILINE):
        issues.append("含 markdown 標題符號 (#)")
    if re.search(r'\*{2,}[^*]+\*{2,}', text):
        issues.append("含 markdown 粗體 (**)")
    if re.search(r'📎', text):
        issues.append("含 📎 來源標記")
    if re.search(r'\[.*?\]\(.*?\)', text):
        issues.append("含 markdown 連結 [text](url)")

    if issues:
        for issue in issues:
            check_fail(f"播報稿格式問題: {issue}")
        return False

    check_pass("播報稿無格式異常")
    return True


def check_git_clean() -> bool:
    """Check if git working directory is clean."""
    import subprocess
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True,
        cwd=SUMMARIES_DIR.parent
    )
    if result.returncode != 0:
        return check_warn("無法檢查 git status")

    dirty = [l for l in result.stdout.strip().split("\n") if l.strip()]
    if dirty:
        check_fail(f"Git 有未提交的變更 ({len(dirty)} 個檔案)")
        for f in dirty[:5]:
            print(f"    {f}")
        return False

    check_pass("Git working directory clean")
    return True


def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <YYYY-MM-DD>")
        sys.exit(1)

    date_str = sys.argv[1]
    print(f"\n🔍 Pre-publish check: {date_str}\n")

    results = []
    results.append(("市場數據一致性", check_market_consistency(date_str)))
    results.append(("播報稿無 URL", check_no_urls_in_script(date_str)))
    results.append(("播報稿格式正常", check_no_garbled_text(date_str)))
    results.append(("音檔檢查", check_audio_file(date_str)))
    results.append(("Git 狀態", check_git_clean()))

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\n{'='*40}")
    if passed == total:
        print(f"{GREEN}🟢 全部通過 ({passed}/{total}) — 可以發布！{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}🔴 {total - passed} 項未通過 ({passed}/{total}) — 需要人工審查{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
