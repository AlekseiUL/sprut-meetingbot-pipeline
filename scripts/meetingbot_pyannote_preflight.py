#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MODEL = "pyannote/speaker-diarization-3.1"
ENV_PATH = Path(os.environ.get("MEETINGBOT_CONFIG", Path(__file__).resolve().parent.parent / "config" / "meetingbot.env"))
TOKEN_KEYS = ("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN", "PYANNOTE_AUTH_TOKEN")


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def main() -> int:
    load_env_file(ENV_PATH)
    token_key = next((key for key in TOKEN_KEYS if os.environ.get(key)), "")
    result = {
        "model": MODEL,
        "envPath": str(ENV_PATH),
        "tokenPresent": bool(token_key),
        "tokenKey": token_key or None,
        "ok": False,
        "reason": "",
    }
    if not token_key:
        result["reason"] = "missing_hf_token"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    try:
        from pyannote.audio import Pipeline
        token = os.environ[token_key]
        pipeline = Pipeline.from_pretrained(MODEL, token=token)
        result["ok"] = pipeline is not None
        result["reason"] = "ok" if pipeline is not None else "pipeline_none"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if pipeline is not None else 3
    except Exception as exc:
        text = f"{type(exc).__name__}: {exc}"
        if "401" in text or "gated" in text.lower() or "restricted" in text.lower():
            result["reason"] = "hf_token_missing_access_or_terms_not_accepted"
        else:
            result["reason"] = "pipeline_load_failed"
        result["errorType"] = type(exc).__name__
        result["errorPreview"] = text[:500]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
