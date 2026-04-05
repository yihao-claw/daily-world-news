# Environment Setup

## Date Convention
All dates/filenames use **JST (Asia/Tokyo)**:
```bash
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
```

## PATH (macOS)
Scheduled tasks may not have Homebrew in PATH:
```bash
export PATH="/opt/homebrew/bin:$PATH"
```

## Secrets (1Password)
Load via `scripts/load-secrets.sh`:
```bash
source "${SKILL_DIR}/scripts/load-secrets.sh"
```

**Flow:** `.env` (OP_SERVICE_ACCOUNT_TOKEN) -> `op` CLI -> 1Password vault `openclaw` / item `secrets` -> notesPlain (KEY=VALUE lines)

**Exported variables:**
| Variable | Source |
|----------|--------|
| TELEGRAM_BOT_TOKEN | 1Password (TG_BOT_DEFAULT) |
| TELEGRAM_CHAT_ID | Hardcoded: `-1003767828002` |
| BRIGHTDATA_API_TOKEN | 1Password |
| R2_API_TOKEN | 1Password |
| R2_ACCOUNT_ID | 1Password |
| R2_BUCKET | 1Password (default: `ai-podcast`) |

## Dependencies
```bash
pip3 install feedparser requests thefuzz yfinance edge-tts --break-system-packages -q
which ffmpeg || brew install ffmpeg
```

## Search Fallback
If `web_search` is unavailable:
```bash
python3 ~/.openclaw/workspace/skills/smart-search/scripts/smart_search.py \
  --query "your query" --type news --freshness day --limit 10 --json
```
Fallback chain: Brave API -> SearXNG (local) -> DuckDuckGo.

## Directories
- **Skill dir:** `${SKILL_DIR}` (this skill's root)
- **Summaries:** `${SKILL_DIR}/summaries/`
