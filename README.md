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

### 五階段流程

| Phase | 內容 | 詳情 |
|-------|------|------|
| 0 | 🔐 Pre-flight | 載入 secrets（1Password）、安裝依賴、抓市場數據 |
| 1 | 🔬 科技新聞 | RSS 39 feeds + GitHub 18 repos + Reddit 10 subs + X + Web Search → 品質評分 → 去重 |
| 2 | 🌍 時事新聞 | 9 大區域 + 多國視角（Format A/B）|
| 3 | 🎙️ Podcast | 合併兩份摘要，6000-10000 字 → TTS 語音 |
| 4 | 📤 Validate & Push | 驗證 + Git commit + push |
| 5 | 🎧 Publish | R2 上傳 + RSS 更新（排程自動 / 手動觸發）|

### 手動觸發

```bash
openclaw cron run 71c85d19-ff69-409f-b03d-9d7bed7c8268
```

## 檔案結構

```
daily-world-news/
├── SKILL.md                  # 主流程定義（精簡版，引用子檔案）
├── README.md                 # 本文件
│
├── config/                   # 設定檔
│   ├── ENV.md                # 環境設定、secrets、依賴
│   ├── SOURCES.md            # 時事媒體清單（40+ 來源，按國家分類）
│   └── TECH_SOURCES.json     # 科技來源 + Topic 定義（RSS/GitHub/Reddit/Web Search）
│
├── guidelines/               # 品質與格式規範
│   ├── QUALITY.md            # 評分公式、去重規則、反面觀點、市場日期校正、事實核查
│   ├── FORMAT.md             # 時事格式（Format A 多元視角 / Format B 標準）
│   ├── TECH_FORMAT.md        # 科技格式（品質分數 + Topic 分類）
│   └── PODCAST.md            # Podcast 風格指引
│
├── scripts/
│   ├── load-secrets.sh       # 從 1Password 載入 secrets
│   ├── generate-audio.py     # TTS 語音生成（edge-tts + ffmpeg）
│   ├── generate-rss.py       # RSS feed 生成
│   ├── upload-r2.sh          # 上傳到 Cloudflare R2
│   ├── fetch_market.py       # 市場數據抓取
│   └── validate.py           # 產出驗證
│
├── gather_tech.py            # 科技新聞資料收集（RSS + GitHub + Reddit）
├── episode-counter.txt       # Podcast 集數計數器
│
└── summaries/                # 每日產出（auto-generated）
```

## 如何調整

| 想調整... | 編輯哪個檔案 |
|-----------|-------------|
| 環境 / secrets / 依賴 | `config/ENV.md` |
| 時事來源 | `config/SOURCES.md` |
| 科技來源（RSS/GitHub/Reddit）| `config/TECH_SOURCES.json` |
| 時事格式 | `guidelines/FORMAT.md` |
| 科技格式 | `guidelines/TECH_FORMAT.md` |
| 評分 / 去重 / 事實核查 | `guidelines/QUALITY.md` |
| Podcast 風格/長度 | `guidelines/PODCAST.md` |
| 語音設定 | `scripts/generate-audio.py` |
| 主流程 | `SKILL.md` |
| 排程時間 | `openclaw cron edit <id> --cron "..." --tz "..."` |

## 依賴

```bash
pip3 install feedparser requests thefuzz yfinance edge-tts --break-system-packages
brew install ffmpeg  # macOS
```
