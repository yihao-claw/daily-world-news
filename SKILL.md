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

**References:**
- Environment & secrets: [config/ENV.md](config/ENV.md)
- World affairs sources: [config/SOURCES.md](config/SOURCES.md)
- Tech sources & topics: [config/TECH_SOURCES.json](config/TECH_SOURCES.json)
- Quality & scoring: [guidelines/QUALITY.md](guidelines/QUALITY.md)
- World format: [guidelines/FORMAT.md](guidelines/FORMAT.md)
- Tech format: [guidelines/TECH_FORMAT.md](guidelines/TECH_FORMAT.md)
- Podcast style: [guidelines/PODCAST.md](guidelines/PODCAST.md)

---

## PHASE 0 — Pre-flight

1. `TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)` / `export PATH="/opt/homebrew/bin:$PATH"`
2. `source "${SKILL_DIR}/scripts/load-secrets.sh"` (see [config/ENV.md](config/ENV.md))
3. If `summaries/${TODAY}.md` AND `summaries/${TODAY}-tech.md` both exist and were delivered -> STOP
4. Install deps (first run): `pip3 install feedparser requests thefuzz yfinance edge-tts --break-system-packages -q && which ffmpeg || brew install ffmpeg`
5. Fetch market data: `python3 scripts/fetch_market.py -o summaries/${TODAY}-market.json`

## PHASE 1 — 科技新聞

1. **Gather (deterministic):** `python3 gather_tech.py --sources config/TECH_SOURCES.json --yesterday "summaries/${YESTERDAY}-tech.md" --output "summaries/${TODAY}-raw-tech.json"`
2. **X search supplement:** Run x-search.py for AI/crypto/Chinese tech tweets (see x-monitor project)
3. **Web search supplement:** Fill gaps from `web_search_queries` in TECH_SOURCES.json
4. **Dedup gate:** Read past 3 days' tech summaries, apply New Development Test (see [guidelines/QUALITY.md](guidelines/QUALITY.md))
5. **Write summary:** Per [guidelines/TECH_FORMAT.md](guidelines/TECH_FORMAT.md), with counter-perspectives per [guidelines/QUALITY.md](guidelines/QUALITY.md). Save to `summaries/${TODAY}-tech.md`
6. **Fact verification:** Check version numbers, benchmarks, funding amounts, release dates
7. **Send to Telegram** (split at 3800 chars per message)

## PHASE 2 — 時事新聞

1. **Read config:** [guidelines/FORMAT.md](guidelines/FORMAT.md) + [config/SOURCES.md](config/SOURCES.md)
2. **Dedup gate:** Read past 3 days' world summaries, build dedup list, apply New Development Test
3. **Gather:** X search + 15-25 web_search queries across 9 regions. Apply counter-perspective & data evidence mandates (see [guidelines/QUALITY.md](guidelines/QUALITY.md))
4. **Verify sources:** Every story MUST have at least one real URL
5. **Write summary:** Per [guidelines/FORMAT.md](guidelines/FORMAT.md). Market snapshot uses `market.json` exact numbers with date awareness (see [guidelines/QUALITY.md](guidelines/QUALITY.md)). Save to `summaries/${TODAY}.md`
6. **Fact verification:**人名/職稱, 數字, 日期, 因果, 引述 (see [guidelines/QUALITY.md](guidelines/QUALITY.md))
7. **Send to Telegram** (split at 3800 chars per message)

## PHASE 3 — Combined Podcast

1. Read [guidelines/PODCAST.md](guidelines/PODCAST.md)
2. Increment `episode-counter.txt` -> EP number
3. **Write script** (6000-10000 字, min 4000 字 = 12000 bytes). Structure: 開場 -> 時事 -> 過場(口語，不用轉場標記) -> 科技 -> 市場快報(日期校正必做) -> 結尾. Save to `summaries/${TODAY}-podcast.md`
4. **Validate:** `python3 scripts/validate.py ${TODAY}`
5. **Generate audio:** `python3 scripts/generate-audio.py summaries/${TODAY}-podcast.md summaries/${TODAY}.mp3` (retry TTS 503 up to 2x)
6. **Send to Telegram** (review copy, asVoice=true)

## PHASE 4 — Validate & Git Push

1. `python3 scripts/validate.py ${TODAY}` — fix any failures
2. `git add -A && git commit -m "📰 每日新聞摘要 ${TODAY}" && git push`

## PHASE 5 — Publish (排程自動 / 手動需觸發)

1. `bash scripts/upload-r2.sh summaries/${TODAY}.mp3 podcasts/${TODAY}.mp3`
2. `python3 scripts/generate-rss.py`
3. `bash scripts/upload-r2.sh summaries/feed.xml feed.xml`

---

## Key Rules
- All dates use **JST (Asia/Tokyo)**
- No fabricated news or URLs — every story needs 📎 source links
- Compare perspectives by **country**, not East/West
- No duplicates with past 3 days (see dedup gate)
- Tech news scored by quality_score (min 5 to publish)
- Telegram: 時事 and 科技 sent separately, podcast is combined
- Market data: check `date` field per indicator, 休市就說休市
