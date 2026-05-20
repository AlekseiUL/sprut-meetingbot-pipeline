#!/usr/bin/env python3
"""Build a deterministic transcript markdown section from diarization JSON."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def usage() -> None:
    print("Usage: json_to_transcript.py <meeting.json> [participants]", file=sys.stderr)


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def main() -> int:
    if len(sys.argv) < 2:
        usage()
        return 2

    path = Path(sys.argv[1]).expanduser().resolve()
    participants = sys.argv[2] if len(sys.argv) > 2 else ""
    payload = json.loads(path.read_text(encoding="utf-8"))
    segments = payload.get("segments") or []

    for segment in segments:
        start = float(segment.get("start", 0.0))
        speaker = (segment.get("speaker") or "UNKNOWN").strip()
        text = (segment.get("text") or "").strip() or "[неразборчиво]"
        print(f"**[{fmt_time(start)}] {speaker}:** {text}")

    duration_seconds = float(payload.get("duration_seconds") or 0)
    meta = {
        "date": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        "duration": f"{round(duration_seconds / 60)} минут" if duration_seconds else "[требует уточнения]",
        "speakers": int(payload.get("speaker_count") or len(payload.get("speakers") or [])),
        "participants": participants,
        "segment_count": len(segments),
        "diarization_mode": payload.get("diarization_mode", ""),
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
