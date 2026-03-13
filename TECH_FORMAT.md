# 科技新聞格式規範

## 整體結構

```
# 🔬 每日科技新聞 — YYYY年M月D日（週X）

> 📡 資料來源：RSS {N} | GitHub {N} | Reddit {N} | Web Search {N}
> ⏰ 更新時間：JST HH:MM

---

## 🔥 科技頭條（Top 3）

[當日最重大的 3 則科技新聞，跨 Topic]

---

## 🧠 LLM / 大型模型
[按 quality_score 降序，3-8 則]

## 🤖 AI Agent
[按 quality_score 降序，3-6 則]

## 💰 加密貨幣
[按 quality_score 降序，3-6 則]

## 🔬 前沿科技
[按 quality_score 降序，3-8 則]

---

## 📦 GitHub Releases
[監控 repo 的新版本發布]

## 📝 Blog Picks
[3 篇來自獨立技術部落格的精選文章]

---

## 📊 市場快照（加密貨幣）
- BTC / ETH / SOL（價格、24h 漲跌幅）
- 總市值、24h 交易量
- 恐懼貪婪指數
```

## 每則新聞格式

### 標準格式
```
• 🔥{score} **[標題]** — [2-3 句摘要，包含背景與影響]
  📎 來源：[媒體名](URL)
```

### 多來源格式（score > 10 或重大事件）
```
• 🔥{score} **[標題]**
  [事件摘要 2-3 句]
  📎 來源：[來源A](URL) | [來源B](URL) | [來源C](URL)
```

### GitHub Release 格式
```
• **owner/repo** `vX.Y.Z` — release 重點摘要
  📎 <https://github.com/owner/repo/releases/tag/vX.Y.Z>
```

### Blog Pick 格式
```
• **文章標題** — 作者 | 2-3 句核心觀點摘要
  📎 <https://blog.example.com/post>
```

### Reddit 格式
```
• 🔥{score} **[標題]** — [摘要] *[Reddit r/xxx, {upvotes}↑]*
  📎 來源：[Reddit](URL)
```

## Telegram 注意事項
- ❌ 不使用 markdown 表格
- ✅ 使用 bullet points + bold
- ✅ 市場快照用純文字列表
