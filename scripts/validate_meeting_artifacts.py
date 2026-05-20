#!/usr/bin/env python3
"""Validate MeetingBot JSON and final Markdown artifacts before publishing."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


RAW_LABEL_RE = re.compile(r"\b(?:SPEAKER_\d+|UNKNOWN)\b|\[Участник\s+\d+\]")


def participants_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def fail(message: str) -> None:
    raise ValueError(message)


def validate_json(path: Path, participants: list[str], strict: bool) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    segments = payload.get("segments") or []
    if not segments:
        fail(f"JSON has no segments: {path}")

    if strict and payload.get("diarization_mode") == "whisper_only":
        fail("Strict mode rejects whisper_only diarization")

    if strict and payload.get("diarization_error"):
        fail(f"Strict mode rejects diarization_error: {payload.get('diarization_error')}")

    speaker_count = int(payload.get("speaker_count") or len(payload.get("speakers") or []))
    if strict and len(participants) >= 2 and speaker_count < 2:
        fail(f"Expected at least 2 speakers for multi-participant meeting, got {speaker_count}")


def has_best_effort_evidence() -> bool:
    return (
        os.environ.get("MEETING_BEST_EFFORT_CONFIRMED") == "1"
        and os.environ.get("MEETING_MAPPING_ATTEMPTS") == "3"
        and os.environ.get("MEETING_CONTEXT_ROLE_MAPPING_ATTEMPTED") == "1"
    )


def validate_md(path: Path, participants: list[str], strict: bool) -> None:
    text = path.read_text(encoding="utf-8")
    raw_match = RAW_LABEL_RE.search(text)
    if raw_match:
        fail(f"Published MD contains raw diarization label: {raw_match.group(0)}")

    if "**Участники:**" not in text:
        fail("Published MD must contain **Участники:** metadata")

    has_unknown_placeholder = "Спикер без точного имени" in text
    if strict and has_unknown_placeholder:
        fail("Strict mode rejects `Спикер без точного имени`")

    if has_unknown_placeholder and not has_best_effort_evidence():
        fail("Best-effort placeholder requires evidence env triple")

    if participants and strict:
        transcript_speakers = set()
        for line in text.splitlines():
            match = re.match(r"^\*\*\[[0-9:]+\]\s+(.+?):\*\*", line)
            if match:
                transcript_speakers.add(match.group(1).strip())
        allowed = set(participants)
        unexpected = sorted(name for name in transcript_speakers if name not in allowed)
        if unexpected:
            fail(f"Transcript speakers are not in participants: {', '.join(unexpected)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path")
    parser.add_argument("--md", dest="md_path")
    parser.add_argument("--participants", default="")
    args = parser.parse_args()

    strict = os.environ.get("MEETING_STRICT_MD", "1") != "0"
    participants = participants_list(args.participants)

    try:
        if args.json_path:
            validate_json(Path(args.json_path), participants, strict)
        if args.md_path:
            validate_md(Path(args.md_path), participants, strict)
    except Exception as exc:
        print(f"VALIDATION_FAILED: {exc}", file=sys.stderr)
        return 1

    print("VALIDATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
