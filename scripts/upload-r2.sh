#!/usr/bin/env bash
# Upload podcast MP3 to Cloudflare R2
# Usage: ./upload-r2.sh <file.mp3> [object-key]
# Example: ./upload-r2.sh summaries/2026-03-24.mp3 podcasts/2026-03-24.mp3

set -euo pipefail

R2_ACCOUNT_ID="${R2_ACCOUNT_ID:?R2_ACCOUNT_ID env var not set}"
R2_BUCKET="${R2_BUCKET:-ai-podcast}"
R2_API_TOKEN="${R2_API_TOKEN:?R2_API_TOKEN env var not set}"

FILE="$1"
OBJECT_KEY="${2:-podcasts/$(basename "$FILE")}"

if [ ! -f "$FILE" ]; then
  echo "ERROR: File not found: $FILE" >&2
  exit 1
fi

# Detect content type from extension
case "${FILE##*.}" in
  mp3)  CONTENT_TYPE="audio/mpeg" ;;
  xml)  CONTENT_TYPE="application/xml" ;;
  jpg|jpeg) CONTENT_TYPE="image/jpeg" ;;
  png)  CONTENT_TYPE="image/png" ;;
  *)    CONTENT_TYPE="application/octet-stream" ;;
esac

FILESIZE=$(stat -c%s "$FILE" 2>/dev/null || stat -f%z "$FILE")

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/${R2_ACCOUNT_ID}/r2/buckets/${R2_BUCKET}/objects/${OBJECT_KEY}" \
  -H "Authorization: Bearer ${R2_API_TOKEN}" \
  -H "Content-Type: ${CONTENT_TYPE}" \
  --data-binary @"$FILE")

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
  echo "✅ Uploaded: ${OBJECT_KEY} (${FILESIZE} bytes, ${CONTENT_TYPE}) → R2:${R2_BUCKET}"
else
  echo "❌ Upload failed: HTTP ${HTTP_CODE}" >&2
  exit 1
fi
