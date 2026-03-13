#!/usr/bin/env python3
"""
validate.py — 驗證每日新聞產出是否合格
用法: python3 validate.py <DATE>  (e.g. 2026-03-08)
退出碼: 0=通過, 1=有問題
"""
import os
import sys

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
    podcast_path = os.path.join(base, required["podcast"])
    if os.path.exists(podcast_path):
        with open(podcast_path, "r") as f:
            content = f.read()
        byte_size = len(content.encode("utf-8"))
        # 粗估中文字數：扣除 ASCII 後除以 3
        ascii_chars = sum(1 for c in content if ord(c) < 128)
        non_ascii_chars = len(content) - ascii_chars
        estimated_cn_chars = non_ascii_chars + ascii_chars // 4  # ASCII 大約 4 字母算 1 字
        
        if byte_size < 12000:
            errors.append(f"❌ Podcast 太短: {byte_size} bytes (需 ≥12000), 估計 ~{estimated_cn_chars} 中文字 (需 ≥4000)")
        elif byte_size < 18000:
            warnings.append(f"⚠️ Podcast 偏短: {byte_size} bytes, 估計 ~{estimated_cn_chars} 字 (目標 6000-10000)")
        else:
            print(f"✅ Podcast 字數: ~{estimated_cn_chars} 字 ({byte_size} bytes)")

    # 3. World summary 要有 source links
    world_path = os.path.join(base, required["world"])
    if os.path.exists(world_path):
        with open(world_path, "r") as f:
            world_content = f.read()
        link_count = world_content.count("http")
        story_count = world_content.count("###") + world_content.count("• ")
        if link_count < 3:
            errors.append(f"❌ World summary 幾乎沒有 source links ({link_count} 個)")
        elif link_count < story_count // 2:
            warnings.append(f"⚠️ Source links 不足: {link_count} links vs ~{story_count} stories")

    # 4. MP3 命名檢查
    mp3_path = os.path.join(base, f"{date}.mp3")
    alt_mp3 = os.path.join(base, f"{date}-podcast.mp3")
    if not os.path.exists(mp3_path) and os.path.exists(alt_mp3):
        warnings.append(f"⚠️ MP3 命名不一致: 應為 {date}.mp3，實際為 {date}-podcast.mp3")

    # 輸出結果
    if errors:
        for e in errors:
            print(e)
        for w in warnings:
            print(w)
        print(f"\n🔴 驗證失敗 — {len(errors)} 個錯誤")
        sys.exit(1)
    elif warnings:
        for w in warnings:
            print(w)
        print(f"\n🟡 驗證通過（有 {len(warnings)} 個警告）")
        sys.exit(0)
    else:
        print(f"✅ {date} 所有檢查通過")
        sys.exit(0)

if __name__ == "__main__":
    main()
