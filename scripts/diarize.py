#!/usr/bin/env python3
"""Run local transcription and diarization for a meeting audio file.

Output is JSON on stdout. Diagnostics go to stderr.
"""

from __future__ import annotations

import json
import contextlib
import os
import sys
from pathlib import Path
from typing import Any

import mlx_whisper
import soundfile as sf
import torch
from pyannote.audio import Pipeline


DEFAULT_MODEL = "mlx-community/whisper-small-mlx"
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"


def usage() -> None:
    print("Usage: diarize.py <audio_path> [language] [whisper_model]", file=sys.stderr)


def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def best_speaker(segment: dict[str, Any], diarization_segments: list[dict[str, Any]]) -> str:
    start = float(segment.get("start", 0.0))
    end = float(segment.get("end", start))
    scores: dict[str, float] = {}

    for item in diarization_segments:
      amount = overlap(start, end, item["start"], item["end"])
      if amount > 0:
          scores[item["speaker"]] = scores.get(item["speaker"], 0.0) + amount

    if not scores:
        return "UNKNOWN"
    return max(scores.items(), key=lambda item: item[1])[0]


def load_diarization(audio_path: Path) -> list[dict[str, Any]]:
    token = (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        or os.environ.get("PYANNOTE_AUTH_TOKEN")
    )
    kwargs = {"token": token} if token else {}
    pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, **kwargs)
    if torch.backends.mps.is_available():
        pipeline.to(torch.device("mps"))

    result = pipeline(str(audio_path))
    annotation = getattr(result, "speaker_diarization", result)
    segments: list[dict[str, Any]] = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append({
            "start": float(turn.start),
            "end": float(turn.end),
            "speaker": str(speaker),
        })
    return segments


def transcribe(audio_path: Path, language: str, model: str) -> dict[str, Any]:
    return mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo=model,
        language=language,
        word_timestamps=True,
    )


def main() -> int:
    if len(sys.argv) < 2:
        usage()
        return 2

    audio_path = Path(sys.argv[1]).expanduser().resolve()
    language = sys.argv[2] if len(sys.argv) > 2 else "ru"
    model = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODEL

    if not audio_path.exists():
        print(f"Audio file does not exist: {audio_path}", file=sys.stderr)
        return 2

    info = sf.info(str(audio_path))
    diarization_mode = "pyannote"
    diarization_error = ""

    try:
        with contextlib.redirect_stdout(sys.stderr):
            diarization_segments = load_diarization(audio_path)
    except Exception as exc:
        diarization_mode = "whisper_only"
        diarization_error = f"{type(exc).__name__}: {exc}"
        diarization_segments = []
        print(f"Diarization failed, falling back to whisper_only: {diarization_error}", file=sys.stderr)

    with contextlib.redirect_stdout(sys.stderr):
        whisper_result = transcribe(audio_path, language, model)
    output_segments: list[dict[str, Any]] = []

    for segment in whisper_result.get("segments", []):
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        speaker = best_speaker(segment, diarization_segments) if diarization_segments else "SPEAKER_00"
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        output_segments.append({
            "start": start,
            "end": end,
            "speaker": speaker,
            "text": text,
        })

    speakers = sorted({segment["speaker"] for segment in output_segments})
    payload = {
        "audio_file": str(audio_path),
        "language": language,
        "diarization_mode": diarization_mode,
        "diarization_error": diarization_error,
        "speakers": speakers,
        "speaker_count": len(speakers),
        "segments": output_segments,
        "duration_seconds": float(info.duration),
        "sample_rate": int(info.samplerate),
        "channels": int(info.channels),
        "whisper_model": model,
        "diarization_model": DIARIZATION_MODEL,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
