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

## 🧠 LLM / 大型模型 (max 6)
## 🤖 AI Agent (max 5)
## 💰 加密貨幣 (max 5)
## 🔬 前沿科技 (max 6)
## 🚀 Space & Science (max 3)
## 📱 Consumer Tech & Hardware (max 3)
## 🛡️ Cybersecurity (max 3)
## 🧬 Biotech & Health Tech (max 2)

---

## 📦 GitHub Releases
## 📝 Blog Picks (3 篇精選)

---

## 📊 市場快照（加密貨幣）
```

**Diversity rule:** 最終輸出必須涵蓋至少 4 個不同 topic。單一 topic 不得超過總篇數 40%。

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

### GitHub Release / Blog Pick / Reddit 格式
```
• **owner/repo** `vX.Y.Z` — release 重點摘要
  📎 <https://github.com/owner/repo/releases/tag/vX.Y.Z>

• **文章標題** — 作者 | 2-3 句核心觀點摘要
  📎 <https://blog.example.com/post>

• 🔥{score} **[標題]** — [摘要] *[Reddit r/xxx, {upvotes}↑]*
  📎 來源：[Reddit](URL)
```

## Telegram 注意事項
- 不使用 markdown 表格
- 使用 bullet points + bold
- 市場快照用純文字列表
