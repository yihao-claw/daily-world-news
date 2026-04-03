#!/usr/bin/env python3
"""
generate-audio.py — 從新聞摘要 markdown 生成語音 mp3
用法: python3 generate-audio.py <input.md> [output.mp3]
依賴: edge-tts, ffmpeg
"""

import asyncio
import os
import re
import subprocess
import sys
import tempfile
import shutil

VOICE = os.environ.get("VOICE", "zh-TW-HsiaoChenNeural")
RATE = os.environ.get("RATE", "+10%")
CHUNK_SIZE = 2000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSITION_SFX = os.path.join(SCRIPT_DIR, "..", "assets", "transition.mp3")

# Sentinel inserted where [🎵 ...] markers appear
SFX_SENTINEL = "___SFX_TRANSITION___"


def md_to_script(text: str) -> str:
    """將 markdown 轉成適合播報的純文字"""
    # 將 [🎵 ...] 標記替換為哨兵（稍後用音效替代）
    text = re.sub(r'\[🎵[^\]]*\]', SFX_SENTINEL, text)
    # 移除 markdown 連結，保留文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 移除 📎 來源行（包含各種格式）
    text = re.sub(r'📎.*', '', text)
    # 移除獨立的 URL 行
    text = re.sub(r'^\s*https?://\S+\s*$', '', text, flags=re.MULTILINE)
    # 移除 > 引言行
    text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)
    # 移除 --- 分隔線
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    # 移除 # 但保留標題文字
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # 移除 bold/italic markdown
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    # 移除 bullet point 符號
    text = re.sub(r'^[•\-\*]\s*', '', text, flags=re.MULTILINE)
    # 清理多餘空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def split_chunks(text: str) -> list[str]:
    """將文字分成約 CHUNK_SIZE 字的段落"""
    chunks = []
    current = ""
    for line in text.split('\n'):
        if len(current) + len(line) > CHUNK_SIZE and current:
            chunks.append(current)
            current = line + '\n'
        else:
            current += line + '\n'
    if current.strip():
        chunks.append(current)
    return chunks


async def generate_tts(text: str, output: str):
    """用 edge-tts 生成語音"""
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(output)


def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <input.md> [output.mp3]")
        sys.exit(1)

    input_path = sys.argv[1]
    date = os.path.splitext(os.path.basename(input_path))[0]
    output_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(input_path), f"{date}.mp3"
    )

    print(f"📰 讀取新聞摘要: {input_path}")
    print(f"🎙️ 語音: {VOICE} (速度: {RATE})")

    with open(input_path, 'r') as f:
        md_text = f.read()

    script = md_to_script(md_text)
    print(f"📝 播報稿: {len(script)} 字")

    # Split script on SFX sentinels to interleave TTS with transition audio
    segments = script.split(SFX_SENTINEL)
    has_sfx = os.path.isfile(TRANSITION_SFX) and len(segments) > 1
    if has_sfx:
        print(f"🎵 過場音效: {TRANSITION_SFX} ({len(segments)-1} 處)")

    tmpdir = tempfile.mkdtemp()
    try:
        mp3_files = []
        tts_idx = 0
        for seg_i, segment in enumerate(segments):
            segment = segment.strip()
            if segment:
                seg_chunks = split_chunks(segment)
                for chunk in seg_chunks:
                    mp3_path = os.path.join(tmpdir, f"chunk_{tts_idx:03d}.mp3")
                    tts_idx += 1
                    print(f"🔊 生成第 {tts_idx} 段...")
                    asyncio.run(generate_tts(chunk, mp3_path))
                    mp3_files.append(mp3_path)
            # Insert transition SFX between segments (not after last)
            if has_sfx and seg_i < len(segments) - 1:
                mp3_files.append(TRANSITION_SFX)

        print(f"📦 共 {len(mp3_files)} 段（含音效）")

        # 合併
        if len(mp3_files) == 1:
            shutil.copy2(mp3_files[0], output_path)
        else:
            concat_path = os.path.join(tmpdir, "concat.txt")
            with open(concat_path, 'w') as f:
                for p in mp3_files:
                    f.write(f"file '{p}'\n")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", concat_path, "-c", "copy", output_path],
                capture_output=True, check=True
            )

        # 取得時長
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", output_path],
            capture_output=True, text=True
        )
        duration = int(float(result.stdout.strip()))
        minutes, seconds = divmod(duration, 60)

        print(f"✅ 完成: {output_path}")
        print(f"⏱️ 時長: {minutes}分{seconds}秒")
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
