#!/usr/bin/env bash
# x-scrape.sh — Scrape X/Twitter profiles or search via Brightdata MCP
# Usage: x-scrape.sh <url> [timeout_seconds]
# Env: BRIGHTDATA_API_TOKEN (required)
#
# Outputs scraped markdown to stdout. Exits 0 on success, 1 on failure.

set -euo pipefail

URL="${1:?Usage: x-scrape.sh <url> [timeout]}"
TIMEOUT="${2:-90}"
TOKEN="${BRIGHTDATA_API_TOKEN:?BRIGHTDATA_API_TOKEN not set}"

# Build JSON-RPC messages for stdio MCP
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"x-tracker","version":"1.0"}}}'
NOTIFY='{"jsonrpc":"2.0","method":"notifications/initialized"}'
CALL=$(cat <<EOF
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"scrape_as_markdown","arguments":{"url":"$URL","wait_for_network_idle":true}}}
EOF
)

RESULT=$(printf '%s\n%s\n%s\n' "$INIT" "$NOTIFY" "$CALL" \
  | API_TOKEN="$TOKEN" timeout "$TIMEOUT" npx -y @brightdata/mcp 2>/dev/null \
  | tail -1)

# Extract text content from MCP response
echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    contents = data.get('result', {}).get('content', [])
    for c in contents:
        if c.get('type') == 'text':
            print(c['text'])
            break
    else:
        print('ERROR: No text content in response', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"
