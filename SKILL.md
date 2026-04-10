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
5. Write `summaries/${TODAY}.md` using **World format** below. Market snapshot uses `-market.json` with date-correction (see Rules).
6. Fact-check: 人名/職稱, 數字, 日期, 因果, 引述.
7. Send to Telegram, split at 3800 chars.

## PHASE 3 — Combined Podcast

1. Bump `episode-counter.txt` → EP number.
2. Write `summaries/${TODAY}-podcast.md` (6000–10000 字, min 4000 字 / 12000 bytes). Structure: 開場 → 時事 → 過場(口語，**不要 `[🎵 轉場]` 標記**) → 科技 → 市場快報(日期校正必做) → 結尾. Style in Rules.
3. `bash scripts/run.sh audio` — validates + generates `summaries/${TODAY}.mp3` (TTS retry 2x on 503).
4. Send to Telegram as voice (asVoice=true).

## PHASE 4 — Finalize (validate + push to GitHub)

```
bash scripts/run.sh finalize
```

執行內容：`validate.py` → `git add -A` → `git commit -m "📰 每日新聞摘要 ${TODAY}"` → **`git push` 推回 GitHub**（必做，不可略過）。若 push 失敗必須檢查原因並重試，不能只靠 `|| echo "push skipped"` 默默放過。

## PHASE 5 — Publish (auto by cron / manual on demand)

```
bash scripts/run.sh publish    # upload-r2 mp3 + generate-rss + upload feed.xml
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

### Market date correction (必做，最高優先級)
**核心原則：用「抓取當下最新可得」的數據，但必須依實際日期如實敘述，絕不把舊數字說成今天的。**

每個指標在 `-market.json` 都帶三個欄位：`date`（bar 日期）、`age_hours`（距抓取時的小時數）、`is_fresh`（**age_hours ≤ 24** 才算 true，所有市場統一標準）。

規則：

1. **只報 `is_fresh == true` 的指標**。24 小時內的就是最新可用，要報；超過 24h 的全部省略或標「數據待更新」，不管是股指、匯率、商品還是加密貨幣。
2. **依實際日期敘述，禁止改寫成「今天」**：`date == $TODAY` 才能用「今天」「此刻」「目前」；否則必須明說「昨天（日期）」「週X 收盤」。每個市場各自報各自日期，禁止「今天全球股市都漲了」這種混講。
3. **`is_fresh == false` 一律省略**。例如 `age_hours > 24` 或 `date` 比 `$TODAY` 早超過 1 天（長假、週末、資料源延遲），直接寫「休市」「數據待更新」，不可硬報。
4. **假日/週末判斷**：週六、週日 → 股市休市；逢復活節/清明/聖誕/元旦等真正不交易。若週一早上跑，週五收盤通常 `age_hours > 24`，屬於 stale，直接說「上週五收盤（日期）」並註明數據超過 24h 或省略。
5. **加密貨幣 / 匯率**：通常 `age_hours` 很小；`< 6` 可用「目前」「此刻」，6–24h 用「最新收盤／最新報價」，> 24h 不新鮮就省略。
6. **交叉驗證**：寫完市場快報後，逐個數字回頭對照 `-market.json` 的 `date` 與 `age_hours`，確認全部 ≤ 24 且敘述與日期一致。

### World format (summaries/${TODAY}.md)
```
# 🌍 每日世界新聞摘要 — YYYY年M月D日（週X）
> 📡 資料來源：[主要媒體]
> ⏰ 更新時間：UTC HH:MM

## 🔥 今日頭條（Top 3）
## 🇺🇸 美洲 / 🇪🇺 歐洲 / 🇯🇵🇰🇷🇨🇳 東亞 / 🇹🇼 台灣 / 🇮🇳 南亞&東南亞 / 🇸🇦 中東 / 🌍 非洲 / 🇦🇺 大洋洲 / 🌐 科技&財經
## 📊 市場快照
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
## 📊 市場快照（加密貨幣）
```
- 單一 topic ≤ 40%，至少涵蓋 4 個 topic.
- 標準: `• 🔥{score} **[標題]** — [2-3 句] \n  📎 來源：[媒體](URL)`
- 多來源(score>10): `📎 來源：[A](URL) | [B](URL) | [C](URL)`
- GitHub: `• **owner/repo** \`vX.Y.Z\` — 重點\n  📎 <url>`
- Telegram: 不用 markdown 表格, 純 bullet + bold.

### Podcast style
轉角國際 / The Daily 風格的 podcast 主持人. 繁中口語. 用「你」稱呼聽眾. 有觀點有分析. 數字口語化（「跌了超過兩個百分點」而非「2.3%」）. 禁: emoji、markdown、`[🎵 轉場]`、「根據報導/據悉」、逐條念標題、重複昨天. 延續新聞：有新進展就「昨天跟你聊過X，今天又變了」；無新進展直接跳過. 結構: **開場 30s（只提最重要的 1-2 個重點，不要逐條預告）** → 時事 **6-10 min**(4-6 主題段) → 自然過場 → 科技 5-8 min(3-5 段) → 市場 1 min(必做日期校正) → 結尾 30s.

---

## Key invariants
- All dates = **JST (Asia/Tokyo)**
- 無 fabricated 新聞/URL — 每則必附 📎
- 時事/科技分開發 Telegram，podcast 合併
- 市場數據必做日期校正，休市就說休市
