#!/usr/bin/env bash
# Set Higgsfield (and optional VIDEO_PROVIDER) env vars on Render via Render API.
# Usage: RENDER_API_KEY=rnd_xxx RENDER_SERVICE_ID=srv-xxx bash scripts/set_render_env.sh
#
# Reads HIGGSFIELD_API_KEY from ../.secrets.env (venture-agt) if not already in shell env.
set -euo pipefail

: "${RENDER_API_KEY:?Need RENDER_API_KEY}"
: "${RENDER_SERVICE_ID:?Need RENDER_SERVICE_ID}"

# Load HIGGSFIELD_API_KEY from .secrets.env if not set
if [[ -z "${HIGGSFIELD_API_KEY:-}" ]]; then
  SECRETS_FILE="$(dirname "$0")/../../venture-agt/.secrets.env"
  if [[ -f "$SECRETS_FILE" ]]; then
    HIGGSFIELD_API_KEY=$(grep '^HIGGSFIELD_API_KEY=' "$SECRETS_FILE" | cut -d= -f2-)
  fi
fi
: "${HIGGSFIELD_API_KEY:?HIGGSFIELD_API_KEY not found in env or .secrets.env}"

VIDEO_PROVIDER="${VIDEO_PROVIDER:-higgsfield}"

echo "Setting env vars on Render service $RENDER_SERVICE_ID ..."

curl -sf -X PUT "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/env-vars" \
  -H "Authorization: Bearer ${RENDER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg hf_key "$HIGGSFIELD_API_KEY" \
    --arg vp "$VIDEO_PROVIDER" \
    '[
      {"key": "HIGGSFIELD_API_KEY", "value": $hf_key},
      {"key": "VIDEO_PROVIDER",     "value": $vp}
    ]')" | jq .

echo "Done. Trigger a deploy or wait for next push."
