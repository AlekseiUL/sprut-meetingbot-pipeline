#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This helper targets macOS. For Linux, install Docker, ffmpeg, Node 20+, and Python 3.11 manually." >&2
  exit 2
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required: https://brew.sh" >&2
  exit 2
fi

brew install ffmpeg python@3.11 node git || true
brew install --cask docker google-chrome || true

python3.11 -m venv "$HOME/.sprut-meetingbot/whisper-env"
"$HOME/.sprut-meetingbot/whisper-env/bin/python" -m pip install --upgrade pip wheel setuptools
"$HOME/.sprut-meetingbot/whisper-env/bin/python" -m pip install -r requirements-whisper.txt

echo "Done. Now run: ./scripts/configure_local.sh"
