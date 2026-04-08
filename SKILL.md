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
**核心原則：絕對不能把舊數字當成今天的數字播報。** 每次寫市場快報前必做：

1. **逐指標比對 `date` field vs `$TODAY`**：打開 `-market.json`，對每個指標（美股、歐股、亞股、匯率、原油、黃金、加密貨幣）逐一檢查 `date`。不可偷懶只看第一個。
2. **`date` ≠ `$TODAY` 就是舊數據**：這個數字昨天（或更早）已經播報過了，**今天不能再用**。只能說「休市」或「尚未開盤」或「週X 收盤數據」並明確標出日期。
3. **判斷 `$TODAY` 星期幾 + 假日**：週六、週日 → 全球股市休市；美股看美東、亞股看 JST、歐股看 CET 的交易日；逢復活節/清明/聖誕/元旦等假日也休市。休市就直接說休市，**不要改寫舊數字假裝是今天的**。
4. **不同市場可能各自在不同日期**：美股可能停在週五、亞股可能停在週四、加密貨幣永遠最新。禁止用「今天全球股市都漲了」這種混講。每個市場講自己的日期。
5. **加密貨幣 24/7 例外**：`date` 通常就是當下，可以用「目前」「此刻」；但仍要比對 `date` 是否在 24h 內，超過就不可用「目前」。
6. **寧可不報也不要誤植**：任何數字有疑慮 → 省略該市場，podcast 裡說「今天休市」「數據待更新」。絕對禁止「根據昨天的收盤」後硬講成今天。
7. **交叉驗證**：寫完市場快報後，回頭對照 `-market.json` 每一個你提到的數字，逐個確認 `date` 欄位與敘述一致。這是寫完後必做的最後檢查。

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
