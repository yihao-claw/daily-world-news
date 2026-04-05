# Claude Code 設定指南

## 前提

- 已安裝 Claude Code CLI (`claude`)
- 已安裝 1Password CLI (`op`)
- 已在 1Password vault `openclaw` 中建立 item `secrets`，包含以下 fields：
  - `telegram-bot-token`
  - `telegram-chat-id`
  - `brightdata-api-token`
  - `r2-api-token`
  - `r2-account-id`
- 已建立 1Password Service Account 並取得 token

## Step 1 — 註冊 Skill

在專案目錄的 `.claude/settings.json` 中加入 skill 路徑：

```bash
cd ~/.openclaw/skills/daily-world-news
mkdir -p .claude
cat > .claude/settings.json << 'EOF'
{
  "skills": [
    "."
  ]
}
EOF
```

或在全域設定 `~/.claude/settings.json` 中加入：

```json
{
  "skills": [
    "~/.openclaw/skills/daily-world-news"
  ]
}
```

## Step 2 — 建立排程任務

```bash
claude schedule create \
  --name "daily-world-news" \
  --cron "0 4 * * *" \
  --tz "Asia/Tokyo" \
  --env "OP_SERVICE_ACCOUNT_TOKEN=<your-service-account-token>" \
  --project "~/.openclaw/skills/daily-world-news" \
  --prompt "執行每日新聞完整流程（Phase 0 → 4）。讀取 SKILL.md 按照指示逐步執行。"
```

## Step 3 — 驗證

```bash
# 確認排程已建立
claude schedule list

# 手動觸發一次測試
claude schedule run daily-world-news
```

## 手動執行（部分流程）

```bash
# 只跑科技新聞
claude --project ~/.openclaw/skills/daily-world-news \
  -e "OP_SERVICE_ACCOUNT_TOKEN=<token>" \
  "只跑科技新聞（Phase 0 + Phase 1）"

# 只跑時事
claude --project ~/.openclaw/skills/daily-world-news \
  -e "OP_SERVICE_ACCOUNT_TOKEN=<token>" \
  "只跑時事新聞（Phase 0 + Phase 2）"

# 發布 podcast（需要先審核通過）
claude --project ~/.openclaw/skills/daily-world-news \
  -e "OP_SERVICE_ACCOUNT_TOKEN=<token>" \
  "發布 podcast 到 R2 和 RSS（Phase 5）"
```
