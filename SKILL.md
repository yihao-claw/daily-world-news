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

Two-pillar daily pipeline: **時事** (world) + **科技** (tech) → combined podcast.
All deterministic work is wrapped in `scripts/run.sh`. Do NOT read any `guidelines/*.md` or `config/*.md` — every rule you need is inlined below.

---

## PHASE 0 — Preflight (1 bash call)

```
bash scripts/run.sh preflight
```

- If exit code = **42** → already delivered today, STOP the entire run.
- On success, stdout prints `TODAY=YYYY-MM-DD` / `YESTERDAY=YYYY-MM-DD`. Use those.
- This call: idempotency check, loads secrets, installs deps, fetches `summaries/${TODAY}-market.json`.

## PHASE 1 — 科技新聞

1. `bash scripts/run.sh tech-gather` — produces `summaries/${TODAY}-raw-tech.json` (already scored, deduped, filtered to score≥5) and `summaries/${TODAY}-dedup-tech.txt` (compact past-3-days digest).
2. Read ONLY these two files. Do not read prior tech summaries directly.
3. Optional: web_search for gaps listed in `raw-tech.json.web_search_queries`. Skip if raw-tech is rich enough.
4. Apply New Development Test against the dedup digest (see Rules below).
5. Write `summaries/${TODAY}-tech.md` using **Tech format** below.
6. Fact-check: version numbers, benchmarks, 融資金額, release state (released/announced/coming-soon).
7. Send to Telegram, split at 3800 chars.

## PHASE 2 — 時事新聞

1. `bash scripts/run.sh world-prep` — produces `summaries/${TODAY}-dedup-world.txt`.
2. Read that digest only.
3. Gather: 15–25 web_search queries across 9 regions. Every story MUST have ≥1 real URL.
4. Apply dedup rules + counter-perspective + data-evidence mandates (see Rules).
5. Write `summaries/${TODAY}.md` using **World format** below.
6. Fact-check: 人名/職稱, 數字, 日期, 因果, 引述.
7. Send to Telegram, split at 3800 chars.

## PHASE 3 — Combined Podcast

1. Bump `episode-counter.txt` → EP number.
2. Write `summaries/${TODAY}-podcast.md` (6000–10000 字, min 4000 字 / 12000 bytes). Structure: 開場 → 時事 → 過場(口語，**不要 `[🎵 轉場]` 標記**) → 科技 → 結尾. **Podcast 不含市場快報區段**（市場數據只留在 Telegram 時事/科技 digest），釋出的時間用來加深時事與科技的分析。Style in Rules.
3. `bash scripts/run.sh audio` — validates + generates `summaries/${TODAY}.mp3` (TTS retry 2x on 503).

## PHASE 4 — Finalize (validate + push to GitHub)

```
bash scripts/run.sh finalize
```

執行內容：`validate.py` → `git add -A` → `git commit -m "📰 每日新聞摘要 ${TODAY}"` → **`git push` 推回 GitHub**（必做，不可略過）。若 push 失敗必須檢查原因並重試，不能只靠 `|| echo "push skipped"` 默默放過。

## PHASE 5 — Publish (auto by cron / manual on demand)

```
bash scripts/run.sh publish    # upload-r2 mp3 + generate-rss + upload feed.xml + 推 Apple Podcasts 連結到 Telegram
```

---

## Rules (inlined — do not fetch)

### Tech scoring (already done by gather_tech.py)
Base 5; +3 priority source; +3 multi-source; +2 <24h; +3 Reddit>500 / +1 >200; +3 GitHub trending; −5 yesterday dup; −2 unknown source. Min publish = 5. `raw-tech.json` is already filtered.

### Dedup (New Development Test)
For every candidate, compare to dedup digest: **new facts/numbers/reactions → keep**; 同題微更新(如價格變動 1%) → 壓縮一句或合併; 無新進展 → 刪除; 連續 3 天無實質變化 → 必刪. 標題相似度 >85% → 合併. 跨區塊: 時事保留政治角度、科技保留技術角度.

### Counter-perspective (mandatory)
- 時事格式 A: 每則重大新聞必含至少一個反對觀點，格式 `🔻 [來源/立場]：[觀點]`.
- 科技: LLM/AI Agent 進展加一句風險/批評視角；加密貨幣同時提看多/看空 + 具體數字.

### Data evidence
涉及經濟/軍事/氣候/科技 → 必附具體數字 + 機構縮寫 (IMF/UN/WHO/WTO/WMO/OECD). 無官方數據寫「數據待核實」，禁杜撰.

### Market date correction (僅適用於加密貨幣 / 金價 / 原油)
僅 BTC、ETH、Gold、WTI/Brent 這幾個指標會被引用，從 `-market.json` 讀。

1. 只報 `is_fresh == true`（`age_hours ≤ 24`）；超過就省略或寫「數據待更新」。
2. `date == $TODAY` 才能用「今天」「目前」；否則明說「昨天（日期）」或「最新報價」。
3. 加密貨幣 `age_hours < 6` 可用「目前」「此刻」；6–24h 用「最新報價」；> 24h 省略。
4. 金價 / 原油沿用同規則；遇假日/週末若 stale，直接寫「上週五收盤（日期）」或省略。
5. 寫完逐項對照 `date` / `age_hours`，確認全部 ≤ 24 且敘述與日期一致。

### World format (summaries/${TODAY}.md)
```
# 🌍 每日世界新聞摘要 — YYYY年M月D日（週X）
> 📡 資料來源：[主要媒體]
> ⏰ 更新時間：UTC HH:MM

## 🔥 今日頭條（Top 3）
## 🇺🇸 美洲 / 🇪🇺 歐洲 / 🇯🇵🇰🇷🇨🇳 東亞 / 🇹🇼 台灣 / 🇮🇳 南亞&東南亞 / 🇸🇦 中東 / 🌍 非洲 / 🇦🇺 大洋洲 / 🌐 科技&財經
```
- 總計 15–20 則，區塊動態分配（不強制每區都有）.
- 3–5 則用**格式 A**（多元視角）, 其餘**格式 B**.
- 格式 A:
  ```
  • **[標題]**
    [摘要 1-2 句]
    🇺🇸 美國：[立場/措辭]
    🇨🇳 中國：[立場/措辭]
    💡 觀點差異：[一句話]
    📎 來源：
    https://...
    https://...
  ```
- 格式 B: `• **[標題]** — [2-3 句深入，含背景+影響]\n  📎 https://...`
- 按**國家**列觀點，不要東/西分類. 每則必含事件+背景+影響.

### Tech format (summaries/${TODAY}-tech.md)
```
# 🔬 每日科技新聞 — YYYY年M月D日（週X）
> 📡 資料來源：RSS {N} | GitHub {N} | Reddit {N} | Web Search {N}
> ⏰ JST HH:MM

## 🔥 科技頭條（Top 3）
## 🧠 LLM (max 6) / 🤖 AI Agent (max 5) / 💰 加密貨幣 (max 5) / 🔬 前沿科技 (max 6)
## 🚀 Space & Science (max 3) / 📱 Consumer Tech (max 3) / 🛡️ Cybersecurity (max 3) / 🧬 Biotech (max 2)
## 📦 GitHub Releases / 📝 Blog Picks (3)
## 📊 市場快照（加密貨幣 + 金價 + 原油）
```
- 市場快照只列 BTC、ETH、Gold、原油（從 `-market.json` 讀），其他指標（股指、FX）一律不寫.
- 單一 topic ≤ 40%，至少涵蓋 4 個 topic.
- 標準: `• 🔥{score} **[標題]** — [2-3 句] \n  📎 來源：[媒體](URL)`
- 多來源(score>10): `📎 來源：[A](URL) | [B](URL) | [C](URL)`
- GitHub: `• **owner/repo** \`vX.Y.Z\` — 重點\n  📎 <url>`
- Telegram: 不用 markdown 表格, 純 bullet + bold.

### Podcast style
轉角國際 / The Daily 風格的 podcast 主持人. 繁中口語. 用「你」稱呼聽眾. 有觀點有分析. 數字口語化（「跌了超過兩個百分點」而非「2.3%」）. 禁: emoji、markdown、`[🎵 轉場]`、「根據報導/據悉」、逐條念標題、重複昨天、**獨立的市場快報段**(禁止 podcast 出現「市場快報」「股市」「指數」等專門段落；股價/匯率/加密幣數字若要出現，只能順帶帶過，不另闢段落). 延續新聞：有新進展就「昨天跟你聊過X，今天又變了」；無新進展直接跳過. 結構: **開場 30s（只提最重要的 1-2 個重點，不要逐條預告）** → 時事 **7-11 min**(5-7 主題段，比過去多 1 段或加深 1 段背景/觀點) → 自然過場 → 科技 **6-9 min**(4-6 段，多一段深入解析或加碼一個 topic) → 結尾 30s. 總長維持原本 13-19 分鐘區間，把原本市場 1 min 的時間平均分回時事與科技。

---

## Key invariants
- All dates = **JST (Asia/Tokyo)**
- 無 fabricated 新聞/URL — 每則必附 📎
- 時事/科技分開發 Telegram；podcast 不發音檔，publish 時 poll iTunes 後送 Apple Podcasts 連結
- 市場數據只保留 BTC / ETH / Gold / WTI / Brent；股指、FX 全面拿掉
- Podcast **不含市場快報段**；市場數據只出現在 Telegram 科技 digest 的「市場快照」，且必做日期校正
