#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$project_root/config/meetingbot.env"
template="$project_root/config/meetingbot.env.example"

if [[ -f "$config" ]]; then
  echo "Config already exists: $config"
  read -r -p "Overwrite? [y/N] " overwrite
  if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
    exit 0
  fi
fi

cp "$template" "$config"
chmod 600 "$config"

read -r -p "Hugging Face token for pyannote (input hidden after paste is not guaranteed in all terminals): " hf_token
if [[ -n "$hf_token" ]]; then
  python3 - "$config" "$hf_token" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
token=sys.argv[2]
text=path.read_text()
text=text.replace('HF_TOKEN=hf_your_token_here', f'HF_TOKEN={token}')
path.write_text(text)
PY
fi

echo "Wrote local config: $config"
echo "Never commit this file. Run preflight next:"
echo "MEETINGBOT_CONFIG=config/meetingbot.env ~/.sprut-meetingbot/whisper-env/bin/python scripts/meetingbot_pyannote_preflight.py"
