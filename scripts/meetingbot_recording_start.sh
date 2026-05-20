#!/usr/bin/env bash
set -euo pipefail

url="${1:-}"
duration="${2:-2h}"

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config_file="${MEETINGBOT_CONFIG:-$project_root/config/meetingbot.env}"
workspace="${MEETINGBOT_WORKSPACE:-$project_root/runtime}"
python_bin="${MEETINGBOT_PYTHON:-python3}"
deliver_to="${MEETINGBOT_DELIVER_TO:-local}"

if [[ -f "$config_file" ]]; then
  # shellcheck source=/dev/null
  source "$config_file"
fi

if [[ -z "$url" ]]; then
  echo "Usage: $0 <https://meet.google.com/...> [duration]" >&2
  exit 2
fi

mkdir -p "$workspace/jobs" "$workspace/meetings"

export MEETINGBOT_PROJECT_ROOT="$project_root"
export MEETINGBOT_WORKSPACE="$workspace"
export MEETINGBOT_CONFIG="$config_file"

exec "$python_bin" \
  "$project_root/scripts/meetingbot_recording_dispatch.py" \
  "$url" "$duration" --deliver-to "$deliver_to"
