---
name: daily-world-news
description: >
  Daily news curation with two pillars: world affairs (9 regions, multi-country perspectives)
  and tech news (RSS + GitHub + Reddit + web search with quality scoring).
  Generates combined podcast audio and delivers to Telegram.
  Use when: running daily news cron, manually generating news, creating podcast, or sending news to Telegram.
  NOT for: general web research, non-news content, or historical analysis.
---

# Daily World News + Tech Digest

Two-pillar daily news system: **時事新聞** (world affairs) + **科技新聞** (tech digest), combined into one podcast.

## Key Config
- All dates/filenames use **JST (Asia/Tokyo)**: `TZ=Asia/Tokyo date +%Y-%m-%d` → `$TODAY`
- Summaries dir: `/home/node/.openclaw/workspace/projects/daily-world-news/summaries/`
- Skill dir: `/home/node/.openclaw/workspace/projects/daily-world-news/`

---

## 🔍 Search Fallback

If `web_search` is unavailable or returns errors (quota exhausted, rate limited):

```bash
python3 ~/.openclaw/workspace/skills/smart-search/scripts/smart_search.py \
  --query "your query" --type news --freshness day --limit 10 --json
```

Fallback chain: Brave API → SearXNG (local) → DuckDuckGo. Use `--type news` for current events, `--type text` for general search.

---

## PHASE 0 — Pre-flight

1. `TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)`
2. If `summaries/${TODAY}.md` AND `summaries/${TODAY}-tech.md` both exist and were delivered → STOP

## PHASE 1 — 科技新聞 (Tech Digest)

### Step 1.1 — Run Data Gatherer Script (DETERMINISTIC)

Run the Python script to collect, score, and deduplicate articles:

```bash
cd /home/node/.openclaw/workspace/projects/daily-world-news
YESTERDAY=$(TZ=Asia/Tokyo date -d '1 day ago' +%Y-%m-%d 2>/dev/null || TZ=Asia/Tokyo date -v-1d +%Y-%m-%d)
python3 gather_tech.py \
  --sources TECH_SOURCES.json \
  --yesterday "summaries/${YESTERDAY}-tech.md" \
  --output "summaries/${TODAY}-raw-tech.json"
```

This script handles ALL data collection deterministically:
- Fetches ~40 RSS feeds (parallel, 8 workers)
- Checks ~18 GitHub repos for releases (filters trunk/nightly noise)
- Fetches ~10 subreddits (score filtered)
- Applies scoring algorithm (priority +3, multi-source +5, recency +2, Reddit score bonus, yesterday penalty -5)
- Deduplicates at 85% title similarity
- Groups by topic, outputs structured JSON

### Step 1.2 — X (Twitter) Search Supplement (DETERMINISTIC)

Run the X search script to gather trending tech discussions from X:

```bash
cd /home/node/.openclaw/workspace/projects/x-monitor
python3 x-search.py "AI OR LLM OR GPT min_faves:100 lang:en" --count 10 --mode top -o /tmp/x-tech-ai.json
python3 x-search.py "crypto OR bitcoin OR ethereum min_faves:100 lang:en" --count 5 --mode top -o /tmp/x-tech-crypto.json
python3 x-search.py "AI OR 人工智能 OR LLM min_faves:50 lang:zh" --count 5 --mode top -o /tmp/x-tech-zh.json
```

Review the X results for:
- Breaking news not yet covered by RSS/Reddit
- Expert opinions and insider perspectives
- Trending topics and viral discussions
- Add noteworthy X posts as supplementary sources (credit with 📎 x.com link)

### Step 1.3 — Web Search Supplement (LLM-DRIVEN)

The script output (`raw_tech.json`) includes `web_search_queries` for topics underrepresented in RSS/Reddit.
Run web_search for each query with `freshness: "day"` to find breaking news missed by feeds.（若 web_search 失敗，改用 smart_search.py —— 見上方 Search Fallback）
Focus on topics with fewer articles in the script output.

**Topics:** 🧠 LLM (max 6) | 🤖 AI Agent (max 5) | 💰 Crypto (max 5) | 🔬 Frontier Tech (max 6) | 🚀 Space & Science (max 3) | 📱 Consumer Tech & Hardware (max 3) | 🛡️ Cybersecurity (max 3) | 🧬 Biotech & Health Tech (max 2)

**Diversity rule:** The final output MUST cover at least 4 different topic categories. No single topic may exceed 40% of total stories. If a topic is underrepresented, prioritize web_search results for it.

### Step 1.4 — Write Tech Summary (LLM-DRIVEN)

Using the script's structured data + web search + X search results:
1. **Select** the most newsworthy stories (top scored + editorially significant)
2. **Summarize** each in 2-3 sentences (this is where LLM judgment matters)
3. **Write trend analysis** connecting the dots

**Output format:** Top 3 headlines → topic sections (by score desc) → GitHub Releases → Blog Picks → Crypto market snapshot. Each story: `• 🔥{score} **[Title]** — [2-3 sentence summary] 📎 URL`. No markdown tables.

**⚖️ 科技新聞反面觀點要求：**
- 每個重大 LLM/AI Agent 進展需加一句「批評或風險視角」（例：效能提升的代價、安全疑慮、競爭威脅）
- 加密貨幣報導需同時提及看多和看空觀點，附具體數字佐證（鏈上數據、交易量、持倉分布）
- Save to `summaries/${TODAY}-tech.md`

### Step 1.5 — Send Tech Summary to Telegram
- Use message tool: action=send, channel=telegram, target=${TELEGRAM_CHAT_ID}, threadId=${TELEGRAM_THREAD_ID}
- **⚠️ Telegram 4096 char limit**: If summary > 3800 chars, split into multiple messages:
  1. Split at section boundaries (## headers) to keep logical grouping
  2. Each chunk must be ≤ 3800 chars (leave margin for formatting)
  3. First chunk: include title + top headlines
  4. Subsequent chunks: continue with remaining sections
  5. Send each chunk as a separate message call
  6. Never cut in the middle of a story or source link

---

## PHASE 2 — 時事新聞 (World Affairs)

### Step 2.1 — Read Config
- Read [FORMAT.md](FORMAT.md) for output format (STRICT)
- Read [SOURCES.md](SOURCES.md) for approved media sources

### Step 2.2 — Read Yesterday's World Summary
- Read yesterday's summary to avoid duplicates
- Only carry forward stories with significant new developments

### Step 2.3 — Gather World News
- Run X search for breaking world news: `python3 /home/node/.openclaw/workspace/projects/x-monitor/x-search.py "breaking news min_faves:500 lang:en" --count 10 --mode top -o /tmp/x-world-news.json`
- Review X results for breaking stories that may not yet appear in web search
- Run 15-25 web_search queries across all 9 regions（若 web_search 失敗，改用 smart_search.py —— 見上方 Search Fallback）
- For major international events → Format A (multi-country perspectives from different media)
- For regional news → Format B (standard)
- Curate 15-20 stories, 3-5 using Format A
- **Every story MUST have 📎 source links** — zero tolerance

#### ⚖️ 反面觀點要求（Counter-Perspective Mandate）
- 每則重大新聞（Format A）**必須包含至少一個反對觀點或批評聲音**
- 反面觀點需來自不同國家、立場或利益相關方（例：政府官方 vs 反對黨、西方媒體 vs 當地媒體、行業受益方 vs 受損方）
- 反面觀點格式：`🔻 [來源/立場]：[觀點摘要]`
- 禁止只呈現單一敘事——即便主流媒體一面倒，仍需尋找少數聲音

#### 📊 數據佐證要求（Data Evidence Mandate）
- 涉及經濟、軍事、科技、氣候的報導**必須附具體數字**：
  - ❌ 「大幅增長」→ ✅ 「同比增長 12.3%（IMF 數據）」
  - ❌ 「傷亡慘重」→ ✅ 「已造成 47 人死亡（聯合國人道協調廳）」
  - ❌ 「氣溫異常」→ ✅ 「較往年同期高出 3.2°C（WMO）」
- 數據來源需標注機構縮寫（IMF, UN, WHO, WTO, WMO, OECD 等）
- 若暫無官方數據，寫「數據待核實」，不得杜撰數字

### Step 2.4 — Verify Sources (MANDATORY — zero exceptions)
- Review EVERY story one by one. Missing 📎 link → run web_search to find a source URL and add it（若 web_search 失敗，改用 smart_search.py —— 見上方 Search Fallback）
- Every story MUST end up with at least one real URL — no exceptions
- **Do NOT proceed to Step 2.5 until every story has at least one real URL**
- NOTE: If you found the news, you found a source. Track URLs during Step 2.3 gathering, not after the fact.

### Step 2.5 — Write World Summary
- Format per [FORMAT.md](FORMAT.md)
- Save to `summaries/${TODAY}.md`

### Step 2.6 — Send World Summary to Telegram
- Use message tool: action=send, channel=telegram, target=${TELEGRAM_CHAT_ID}, threadId=${TELEGRAM_THREAD_ID}
- **⚠️ Telegram 4096 char limit**: If summary > 3800 chars, split into multiple messages:
  1. Split at section boundaries (## headers or region headers) to keep logical grouping
  2. Each chunk must be ≤ 3800 chars (leave margin for formatting)
  3. First chunk: include title + top 3 headlines
  4. Subsequent chunks: continue with remaining regions, add "(續)" in first line
  5. Send each chunk as a separate message call
  6. Never cut in the middle of a story or source link

---

## PHASE 3 — Combined Podcast

### Step 3.1 — Read Podcast Guide
- Read [PODCAST_PROMPT.md](PODCAST_PROMPT.md) for style guide

### Step 3.2 — Write Combined Podcast Script
- **Target: 6000-10000 字** (繁體中文, ~15-25 分鐘語音)
- **⚠️ HARD MINIMUM: 4000 中文字** — 低於此字數的稿件不合格，必須重寫擴充
- **驗證方法：** 寫完後執行 `python3 -c "print(len(open('summaries/${TODAY}-podcast.md').read()))"` 確認檔案大小 **≥ 12000 bytes**（中文字約 3 bytes/字，4000字 ≈ 12000 bytes）。如不足 → 回到 Step 3.2 重寫擴充
- **注意：4000 字 ≠ 4000 bytes！** 中文字每字佔 3 bytes，不要混淆
- Structure:
  1. **開場** (~1 min) — 打招呼 + 預告今天時事和科技各 2-3 件大事
  2. **時事新聞** (~8-12 min) — 依重要性排序，5-8 個主題段落，融入多國視角
  3. **過場** — 自然轉場到科技：「聊完國際局勢，我們來看看科技圈今天有什麼動靜...」
  4. **科技新聞** (~5-8 min) — 依重要性排序，3-5 個主題段落，帶出技術觀點
  5. **市場快報** (~1 min) — 股市 + 加密貨幣重點數字
  6. **結尾** (~30 sec) — 簡短收尾
- Maintain depth and multi-country perspectives (praised — keep it up!)
- Save to `summaries/${TODAY}-podcast.md`

### Step 3.3 — Generate Audio
```bash
cd /home/node/.openclaw/workspace/projects/daily-world-news && \
python3 scripts/generate-audio.py summaries/${TODAY}-podcast.md summaries/${TODAY}.mp3
```
- Verify mp3 exists after running
- **If TTS fails (503 or other error):** wait 30 seconds, then retry up to 2 more times. Edge TTS 503 is usually transient.

### Step 3.4 — Send Audio to Telegram
- Use message tool: action=send, channel=telegram, target=${TELEGRAM_CHAT_ID}, threadId=${TELEGRAM_THREAD_ID}
- asVoice=true, filePath=summaries/${TODAY}.mp3, message="🎙️ 每日新聞 Podcast"

---

## PHASE 4 — Validate & Wrap Up

### Step 4.1 — Run Validation
```bash
cd /home/node/.openclaw/workspace/projects/daily-world-news && python3 scripts/validate.py ${TODAY}
```
- If validation **FAILS** (exit code 1): FIX the issues before proceeding. Re-run the failed phase.
- If validation passes with warnings: proceed but note the warnings in your summary.

### Step 4.2 — Git Push
```bash
cd /home/node/.openclaw/workspace/openclaw-projects && git add -A && git commit -m "📰 每日新聞摘要 ${TODAY}" && git push origin main
```
- **⚠️ MUST verify push succeeded** — run `git log --oneline -1` and confirm the commit hash matches
- If push fails, retry once. If still fails, report the error.

---

## Key Rules
- All dates/filenames use **JST (Asia/Tokyo)**
- No fabricated news or URLs
- Compare perspectives by **COUNTRY**, not East/West
- No duplicates with yesterday
- Every story needs source links (📎) — track URLs during gathering, not after. If you found the news, you have the URL.
- Tech news scored and ranked by quality_score
- Telegram messages: 時事 and 科技 sent **separately**, Podcast is **combined**
