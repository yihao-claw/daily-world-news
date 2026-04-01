#!/usr/bin/env python3
"""
validate.py — 驗證每日新聞產出是否合格
用法: python3 validate.py <DATE>  (e.g. 2026-03-08)
退出碼: 0=通過, 1=有問題
"""
import os
import re
import sys
from collections import Counter


def extract_names(text):
    """Extract CJK person names (2-4 chars patterns near titles/roles)."""
    # Common title patterns in the news
    titles = r'(?:總統|主席|總理|部長|發言人|領袖|領導人|外長|防長|書記|院長|署長|司令|將軍)'
    pattern = rf'([\u4e00-\u9fff]{{2,4}})\s*(?:的|：|,|，)?{titles}'
    return set(re.findall(pattern, text))


def check_name_consistency(world_content, podcast_content):
    """Check if names in podcast match names in world summary."""
    world_names = extract_names(world_content)
    podcast_names = extract_names(podcast_content)
    inconsistencies = []
    # Find names in podcast that don't appear in world summary at all
    for pname in podcast_names:
        if pname not in world_names and pname not in world_content:
            inconsistencies.append(pname)
    return inconsistencies


def check_market_snapshot(content):
    """Check if market snapshot has real numbers, not placeholders."""
    issues = []
    market_section = ""
    in_market = False
    for line in content.split("\n"):
        if "市場快照" in line or "市場快報" in line:
            in_market = True
            continue
        if in_market:
            if line.startswith("---") or line.startswith("#"):
                break
            market_section += line + "\n"

    if not market_section.strip():
        issues.append("市場快照段落為空")
        return issues

    # Check for placeholder text
    placeholders = ["待確認", "待更新", "N/A", "TBD", "---"]
    for p in placeholders:
        if p in market_section:
            issues.append(f"市場快照含佔位符: '{p}'")

    # Check for at least some numbers (percentages, dollar amounts)
    numbers = re.findall(r'[\d,.]+%|[$¥€£]\s?[\d,.]+|\d+[.,]\d+', market_section)
    if len(numbers) < 3:
        issues.append(f"市場快照數字太少 ({len(numbers)} 個，建議至少 5 個)")

    return issues


def check_dedup_with_yesterday(today_content, yesterday_content):
    """Rough check: extract headlines and compare overlap."""
    if not yesterday_content:
        return []

    def extract_headlines(text):
        # Match bold titles: **...** at start of bullet
        return set(re.findall(r'\*\*([^*]{10,80})\*\*', text))

    today_h = extract_headlines(today_content)
    yesterday_h = extract_headlines(yesterday_content)

    # Simple substring overlap check
    overlaps = []
    for th in today_h:
        for yh in yesterday_h:
            # Check if >60% of words overlap
            tw = set(th)
            yw = set(yh)
            if len(tw & yw) / max(len(tw | yw), 1) > 0.6:
                overlaps.append(f"'{th[:40]}...' ≈ 昨日 '{yh[:40]}...'")
    return overlaps


def check_source_links_per_story(content):
    """Check each story bullet has at least one URL."""
    stories_without_links = []
    current_story = ""
    story_title = ""

    for line in content.split("\n"):
        if line.strip().startswith("• **"):
            # Save previous story check
            if current_story and "http" not in current_story:
                stories_without_links.append(story_title[:50])
            # Start new story
            m = re.search(r'\*\*(.+?)\*\*', line)
            story_title = m.group(1) if m else line[:50]
            current_story = line
        elif current_story:
            if line.strip().startswith("• **") or line.strip().startswith("## ") or line.strip().startswith("---"):
                if "http" not in current_story:
                    stories_without_links.append(story_title[:50])
                current_story = ""
                story_title = ""
                if line.strip().startswith("• **"):
                    m = re.search(r'\*\*(.+?)\*\*', line)
                    story_title = m.group(1) if m else line[:50]
                    current_story = line
            else:
                current_story += "\n" + line

    # Last story
    if current_story and "http" not in current_story:
        stories_without_links.append(story_title[:50])

    return stories_without_links


def main():
    if len(sys.argv) < 2:
        print("用法: python3 validate.py <YYYY-MM-DD>")
        sys.exit(1)

    date = sys.argv[1]
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "summaries")
    errors = []
    warnings = []

    # 1. 檢查必要檔案
    required = {
        "world": f"{date}.md",
        "tech": f"{date}-tech.md",
        "podcast": f"{date}-podcast.md",
        "mp3": f"{date}.mp3",
    }

    for label, fname in required.items():
        path = os.path.join(base, fname)
        if not os.path.exists(path):
            errors.append(f"❌ 缺少 {label}: {fname}")
        else:
            size = os.path.getsize(path)
            if label == "mp3" and size < 500_000:
                errors.append(f"❌ MP3 太小 ({size} bytes): {fname}")
            elif label != "mp3" and size < 100:
                errors.append(f"❌ 檔案幾乎是空的 ({size} bytes): {fname}")

    # 2. Podcast 字數驗證
    podcast_content = ""
    podcast_path = os.path.join(base, required["podcast"])
    if os.path.exists(podcast_path):
        with open(podcast_path, "r") as f:
            podcast_content = f.read()
        byte_size = len(podcast_content.encode("utf-8"))
        ascii_chars = sum(1 for c in podcast_content if ord(c) < 128)
        non_ascii_chars = len(podcast_content) - ascii_chars
        estimated_cn_chars = non_ascii_chars + ascii_chars // 4

        if byte_size < 12000:
            errors.append(f"❌ Podcast 太短: {byte_size} bytes (需 ≥12000), 估計 ~{estimated_cn_chars} 中文字 (需 ≥4000)")
        elif byte_size < 18000:
            warnings.append(f"⚠️ Podcast 偏短: {byte_size} bytes, 估計 ~{estimated_cn_chars} 字 (目標 6000-10000)")
        else:
            print(f"✅ Podcast 字數: ~{estimated_cn_chars} 字 ({byte_size} bytes)")

    # 3. World summary source links — per-story check
    world_content = ""
    world_path = os.path.join(base, required["world"])
    if os.path.exists(world_path):
        with open(world_path, "r") as f:
            world_content = f.read()
        link_count = world_content.count("http")
        if link_count < 3:
            errors.append(f"❌ World summary 幾乎沒有 source links ({link_count} 個)")

        # Per-story link check
        missing = check_source_links_per_story(world_content)
        if missing:
            for title in missing[:5]:  # Show first 5
                warnings.append(f"⚠️ 缺少來源連結: {title}")
            if len(missing) > 5:
                warnings.append(f"  ...還有 {len(missing) - 5} 則缺少連結")

    # 4. MP3 命名檢查
    mp3_path = os.path.join(base, f"{date}.mp3")
    alt_mp3 = os.path.join(base, f"{date}-podcast.mp3")
    if not os.path.exists(mp3_path) and os.path.exists(alt_mp3):
        warnings.append(f"⚠️ MP3 命名不一致: 應為 {date}.mp3，實際為 {date}-podcast.mp3")

    # 5. 名稱一致性檢查 (world vs podcast)
    if world_content and podcast_content:
        inconsistent = check_name_consistency(world_content, podcast_content)
        if inconsistent:
            for name in inconsistent:
                errors.append(f"❌ Podcast 出現人名 '{name}' 但 World Summary 中未見此人 — 可能誤植")

    # 6. 市場快照品質檢查
    if world_content:
        market_issues = check_market_snapshot(world_content)
        for issue in market_issues:
            warnings.append(f"⚠️ 市場快照: {issue}")

    # 7. 與昨日重複度檢查
    from datetime import datetime as dt, timedelta
    try:
        today_dt = dt.strptime(date, "%Y-%m-%d")
        yesterday = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_path = os.path.join(base, f"{yesterday}.md")
        yesterday_content = ""
        if os.path.exists(yesterday_path):
            with open(yesterday_path, "r") as f:
                yesterday_content = f.read()
        overlaps = check_dedup_with_yesterday(world_content, yesterday_content)
        if overlaps:
            warnings.append(f"⚠️ 與昨日可能重複的主題 ({len(overlaps)} 則):")
            for o in overlaps[:3]:
                warnings.append(f"   {o}")
    except Exception:
        pass  # Skip dedup check on date parse failure

    # 8. Tech summary 基本檢查
    tech_path = os.path.join(base, f"{date}-tech.md")
    if os.path.exists(tech_path):
        with open(tech_path, "r") as f:
            tech_content = f.read()
        tech_links = tech_content.count("http")
        if tech_links < 5:
            warnings.append(f"⚠️ Tech summary links 偏少: {tech_links} 個")

        # Topic diversity: count topic emojis
        topic_emojis = ['🧠', '🤖', '💰', '🔬', '🚀', '📱', '🛡️', '🧬']
        found_topics = sum(1 for e in topic_emojis if e in tech_content)
        if found_topics < 4:
            warnings.append(f"⚠️ Tech 主題多樣性不足: 只涵蓋 {found_topics}/8 個分類 (建議 ≥4)")

    # 輸出結果
    print(f"\n{'='*50}")
    print(f"📋 驗證報告: {date}")
    print(f"{'='*50}")

    if errors:
        for e in errors:
            print(e)
    if warnings:
        for w in warnings:
            print(w)

    if errors:
        print(f"\n🔴 驗證失敗 — {len(errors)} 個錯誤, {len(warnings)} 個警告")
        sys.exit(1)
    elif warnings:
        print(f"\n🟡 驗證通過（有 {len(warnings)} 個警告）")
        sys.exit(0)
    else:
        print(f"\n✅ {date} 所有檢查通過")
        sys.exit(0)


if __name__ == "__main__":
    main()
