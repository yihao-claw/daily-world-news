# Daily World News + Tech Digest 🌍🔬

自動化新聞整理系統。每天早上產出兩份摘要 — **國際時事** + **科技新聞** — 以及一份合併的 **Podcast 語音播報**。

## 每日產出

| 產出 | 檔案 | 說明 |
|------|------|------|
| 📝 時事摘要 | `summaries/YYYY-MM-DD.md` | 15-20 則國際新聞，重大事件附多國觀點 |
| 🔬 科技摘要 | `summaries/YYYY-MM-DD-tech.md` | 科技新聞，品質評分排序 |
| 🎙️ Podcast 稿 | `summaries/YYYY-MM-DD-podcast.md` | 時事+科技合併，口語化播報 |
| 🔊 語音檔 | `summaries/YYYY-MM-DD.mp3` | 約 15-25 分鐘 |
| 📬 Telegram | 自動推送 | 時事、科技分開發；Podcast 語音合併發 |

## 運作方式

### 排程
- **時間**：每天 JST 07:00（UTC 22:00）
- **執行者**：OpenClaw cron → 讀取 `SKILL.md` 執行
- **模型**：Sonnet (low thinking)
- **超時**：30 分鐘

### 四階段流程

| Phase | 內容 | 詳情 |
|-------|------|------|
| 1 | 🔬 科技新聞 | RSS 39 feeds + GitHub 18 repos + Reddit 10 subs + Web Search → 品質評分 → 去重 |
| 2 | 🌍 時事新聞 | 9 大區域 + 多國視角（Format A/B）|
| 3 | 🎙️ Podcast | 合併兩份摘要，6000-10000 字 → TTS 語音 |
| 4 | 📤 Push | Git commit + push |

### 手動觸發

```bash
openclaw cron run 71c85d19-ff69-409f-b03d-9d7bed7c8268
```

## 檔案結構

```
daily-world-news/
├── SKILL.md               # 主流程定義（四階段）
├── README.md              # 本文件
│
├── # 時事新聞
├── FORMAT.md              # 時事格式規範（Format A 多元視角 / Format B 標準）
├── SOURCES.md             # 時事媒體清單（40+ 來源，按國家分類）
│
├── # 科技新聞
├── TECH_SOURCES.json      # 科技來源（39 RSS + 18 GitHub + 10 Reddit + Web Search）
├── TECH_TOPICS.json       # Topic 定義（LLM / AI Agent / Crypto / Frontier Tech）
├── TECH_FORMAT.md         # 科技格式規範（品質分數 + Topic 分類）
├── SCORING.md             # 品質評分公式 + 去重規則
│
├── # Podcast
├── PODCAST_PROMPT.md      # Podcast 風格指引（時事+科技合併版）
│
├── scripts/
│   └── generate-audio.py  # TTS 語音生成（edge-tts + ffmpeg）
│
└── summaries/             # 每日產出（auto-generated）
```

## 設計原則

### 品質評分（科技新聞）
- 優先來源 +3 / 多來源交叉 +5 / 時效 +2 / 已報導 -5
- 最低門檻 5 分，按分數降序排列
- 詳見 `SCORING.md`

### 多元視角（時事新聞）
- 重大事件按**國家**比較報導角度（不用東/西方分組）
- 3-5 則使用 Format A（多元視角），其餘用 Format B
- 每則必須附來源連結

### Podcast
- 不是念稿，是主持人在聊天
- 時事 + 科技自然串場
- 多元視角用敘事方式帶出

## 如何調整

| 想調整... | 編輯哪個檔案 |
|-----------|-------------|
| 時事來源 | `SOURCES.md` |
| 時事格式 | `FORMAT.md` |
| 科技來源（RSS/GitHub/Reddit）| `TECH_SOURCES.json` |
| 科技 Topic 定義 | `TECH_TOPICS.json` |
| 科技格式 | `TECH_FORMAT.md` |
| 評分規則 | `SCORING.md` |
| Podcast 風格/長度 | `PODCAST_PROMPT.md` |
| 語音設定 | `scripts/generate-audio.py` |
| 排程時間 | `openclaw cron edit <id> --cron "..." --tz "..."` |

## 依賴

```bash
pip install edge-tts
apt install ffmpeg
```
