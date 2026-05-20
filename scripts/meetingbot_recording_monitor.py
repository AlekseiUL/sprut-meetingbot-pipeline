#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("MEETINGBOT_PROJECT_ROOT", SCRIPT_DIR.parent)).resolve()
WORKSPACE = Path(os.environ.get("MEETINGBOT_WORKSPACE", PROJECT_ROOT / "runtime")).resolve()
BACKEND_REPO = Path(os.environ.get("MEETINGBOT_BACKEND_REPO", PROJECT_ROOT / "backend")).resolve()
TEMPVIDEO = BACKEND_REPO / "dist" / "_tempvideo"
DEBUG_VIDEOS = BACKEND_REPO / "debug-videos"
MEETINGS_DIR = Path(os.environ.get("MEETINGBOT_MEETINGS_DIR", WORKSPACE / "meetings")).resolve()
SCRIPTS = SCRIPT_DIR
HERMES = Path(os.environ.get("HERMES_BIN", shutil.which("hermes") or "hermes"))
ANALYSIS_PROFILE = os.environ.get("MEETINGBOT_ANALYSIS_PROFILE", "default")
WHISPER_PYTHON = Path(os.environ.get("MEETINGBOT_WHISPER_PYTHON", str(Path.home() / ".sprut-meetingbot" / "whisper-env" / "bin" / "python3")))


def _duration_seconds(value: str) -> int:
    match = re.match(r"^\s*(\d+)\s*([smhSMH]?)\s*$", value or "")
    if not match:
        return 2 * 60 * 60
    amount = int(match.group(1))
    unit = (match.group(2) or "m").lower()
    if unit == "s":
        return amount
    if unit == "h":
        return amount * 60 * 60
    return amount * 60


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run(cmd: list[str], *, timeout: int = 120, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=timeout, env=env)


def _send(deliver_to: str, subject: str, body: str) -> dict[str, Any]:
    """Send a notification if Hermes CLI is configured; otherwise keep the result local."""
    hermes_available = HERMES.is_file() or shutil.which(str(HERMES)) is not None
    if deliver_to in {"", "local", "none"} or not hermes_available:
        return {"success": True, "mode": "local", "subject": subject, "message": body}
    env = os.environ.copy()
    for key in (
        "HERMES_CRON_AUTO_DELIVER_PLATFORM",
        "HERMES_CRON_AUTO_DELIVER_CHAT_ID",
        "HERMES_CRON_AUTO_DELIVER_THREAD_ID",
    ):
        env.pop(key, None)
    proc = _run([str(HERMES), "send", "--to", deliver_to, "--subject", subject, "--json", body], timeout=180, env=env)
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"error": "send returned non-JSON", "stdout": proc.stdout, "stderr": proc.stderr}


def _backend_busy(backend_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{backend_url.rstrip('/')}/isbusy", timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
            return bool((payload.get("data") or 0) == 1)
    except Exception:
        return False


def _recording_files() -> list[Path]:
    if not TEMPVIDEO.is_dir():
        return []
    return sorted(
        (
            path
            for path in TEMPVIDEO.rglob("*")
            if path.is_file() and path.suffix.lower() in {".webm", ".wav", ".mp4", ".mkv"}
        ),
        key=lambda item: item.stat().st_mtime,
    )


def _wait_for_stable_recording(job_dir: Path, duration: str, backend_url: str, started_at: float) -> Path | None:
    baseline_path = job_dir / "baseline-files.json"
    try:
        baseline = set(json.loads(baseline_path.read_text(encoding="utf-8")))
    except Exception:
        baseline = set()

    poll_seconds = int(os.environ.get("MEETINGBOT_RECORDING_POLL_SECONDS", "15"))
    stable_seconds = int(os.environ.get("MEETINGBOT_RECORDING_STABLE_SECONDS", "90"))
    max_wait = _duration_seconds(duration) + int(os.environ.get("MEETINGBOT_RECORDING_GRACE_SECONDS", "1800"))
    deadline = time.time() + max_wait
    candidate: Path | None = None
    last_size = -1
    stable_since: float | None = None
    saw_backend_busy = False
    idle_without_file_since: float | None = None

    while time.time() < deadline:
        backend_busy = _backend_busy(backend_url)
        if backend_busy:
            saw_backend_busy = True
            idle_without_file_since = None
        files = [
            path
            for path in _recording_files()
            if str(path) not in baseline and path.stat().st_mtime >= started_at - 60 and path.stat().st_size > 0
        ]
        if files:
            newest = max(files, key=lambda item: item.stat().st_mtime)
            size = newest.stat().st_size
            if candidate != newest or size != last_size:
                candidate = newest
                last_size = size
                stable_since = time.time()
            required_stable = 10 if not backend_busy else stable_seconds
            _write_json(
                job_dir / "monitor-state.json",
                {
                    "state": "recording_detected",
                    "candidate": str(candidate),
                    "bytes": size,
                    "backendBusy": backend_busy,
                    "stableForSeconds": int(time.time() - (stable_since or time.time())),
                    "requiredStableSeconds": required_stable,
                    "ts": datetime.now().isoformat(timespec="seconds"),
                },
            )
            if stable_since and (time.time() - stable_since) >= required_stable:
                return candidate
        else:
            if not backend_busy:
                if saw_backend_busy and idle_without_file_since is None:
                    idle_without_file_since = time.time()
                if saw_backend_busy and idle_without_file_since and (time.time() - idle_without_file_since) > 60:
                    return None
                if not saw_backend_busy and (time.time() - started_at) > int(os.environ.get("MEETINGBOT_NO_BUSY_GRACE_SECONDS", "300")):
                    return None
            _write_json(
                job_dir / "monitor-state.json",
                {
                    "state": "waiting_for_recording",
                    "backendBusy": backend_busy,
                    "sawBackendBusy": saw_backend_busy,
                    "tempVideoDir": str(TEMPVIDEO),
                    "ts": datetime.now().isoformat(timespec="seconds"),
                },
            )
        time.sleep(poll_seconds)
    return None


def _convert_to_wav(recording: Path, wav_path: Path) -> bool:
    proc = _run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(recording),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ],
        timeout=1800,
    )
    wav_path.with_suffix(".ffmpeg.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    return proc.returncode == 0 and wav_path.is_file() and wav_path.stat().st_size > 0


def _enhance_wav_for_asr(wav_path: Path, enhanced_path: Path) -> bool:
    """Create a conservative ASR-friendly copy: remove rumble, denoise lightly, normalize speech."""
    if os.environ.get("MEETINGBOT_AUDIO_CLEANUP", "1") in {"0", "false", "False", "no"}:
        return False
    proc = _run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-af",
            "highpass=f=80,afftdn=nf=-25,loudnorm=I=-18:TP=-2:LRA=11",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(enhanced_path),
        ],
        timeout=1800,
    )
    enhanced_path.with_suffix(".ffmpeg.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    return proc.returncode == 0 and enhanced_path.is_file() and enhanced_path.stat().st_size > 0


def _ffprobe_duration_seconds(wav_path: Path) -> float | None:
    proc = _run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(wav_path)],
        timeout=60,
    )
    if proc.returncode != 0:
        return None
    try:
        return float((proc.stdout or "").strip())
    except ValueError:
        return None


def _trim_trailing_silence_for_asr(wav_path: Path, trimmed_path: Path, job_dir: Path) -> Path:
    """Trim long terminal silence so Whisper does not hallucinate repeated phrases over an empty tail."""
    if os.environ.get("MEETINGBOT_TRIM_TRAILING_SILENCE", "1") in {"0", "false", "False", "no"}:
        return wav_path
    min_tail = float(os.environ.get("MEETINGBOT_TRAILING_SILENCE_SECONDS", "12"))
    noise = os.environ.get("MEETINGBOT_SILENCE_NOISE", "-35dB")
    duration = _ffprobe_duration_seconds(wav_path)
    if not duration:
        return wav_path
    proc = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(wav_path),
            "-af",
            f"silencedetect=noise={noise}:d=0.7",
            "-f",
            "null",
            "-",
        ],
        timeout=1800,
    )
    log = (proc.stdout or "") + (proc.stderr or "")
    (job_dir / "silencedetect-asr.txt").write_text(log, encoding="utf-8")
    silence_start: float | None = None
    for match in re.finditer(r"silence_start:\s*([0-9.]+)", log):
        value = float(match.group(1))
        if duration - value >= min_tail:
            silence_start = value
    if silence_start is None or silence_start < 5:
        return wav_path
    proc = _run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-t",
            f"{silence_start:.3f}",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(trimmed_path),
        ],
        timeout=1800,
    )
    trimmed_path.with_suffix(".ffmpeg.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    if proc.returncode == 0 and trimmed_path.is_file() and trimmed_path.stat().st_size > 0:
        _write_json(
            job_dir / "audio-trim.json",
            {"source": str(wav_path), "trimmed": str(trimmed_path), "duration": duration, "cutAt": silence_start, "tailSilence": duration - silence_start},
        )
        return trimmed_path
    return wav_path


def _clean_participant_name(raw: str) -> str:
    name = re.sub(r"\s+", " ", (raw or "").strip())
    if not name:
        return ""
    # Google Meet DOM snapshots can duplicate text as "NAME NAME" or "NAMENAME".
    half = len(name) // 2
    if len(name) % 2 == 0 and name[:half].strip().lower() == name[half:].strip().lower():
        name = name[:half].strip()
    words = name.split()
    if len(words) % 2 == 0:
        left = " ".join(words[: len(words) // 2])
        right = " ".join(words[len(words) // 2 :])
        if left.lower() == right.lower():
            name = left
    return name


def _participants(started_at: float) -> list[str]:
    names: list[str] = []
    if DEBUG_VIDEOS.is_dir():
        for path in sorted(DEBUG_VIDEOS.glob("participants-*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            if path.stat().st_mtime < started_at - 120:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            fields = ["participants", "visibleTileParticipants", "panelParticipants"]
            for field in fields:
                for raw_name in payload.get(field) or []:
                    if not isinstance(raw_name, str):
                        continue
                    name = _clean_participant_name(raw_name)
                    if name and name.lower() != "meetingbot" and name not in names:
                        names.append(name)
    return names


def _diarize(job_dir: Path, wav_path: Path, participants: list[str]) -> tuple[Path | None, dict[str, Any]]:
    python = WHISPER_PYTHON if WHISPER_PYTHON.is_file() else Path(sys.executable)
    best_json: Path | None = None
    best_payload: dict[str, Any] = {}
    attempts = int(os.environ.get("MEETINGBOT_DIARIZATION_ATTEMPTS", "3"))
    language = os.environ.get("MEETINGBOT_TRANSCRIBE_LANGUAGE", "ru")
    whisper_model = os.environ.get("MEETINGBOT_WHISPER_MODEL", "mlx-community/whisper-small-mlx")

    for attempt in range(1, attempts + 1):
        out_path = job_dir / f"meeting-attempt{attempt}.json"
        proc = _run(
            [str(python), str(SCRIPTS / "diarize.py"), str(wav_path), language, whisper_model],
            timeout=int(os.environ.get("MEETINGBOT_DIARIZATION_TIMEOUT", "7200")),
        )
        (job_dir / f"diarize-attempt{attempt}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
        (job_dir / f"diarize-attempt{attempt}.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
        if proc.returncode != 0 or not proc.stdout.strip():
            continue
        try:
            payload = _parse_json_stdout(proc.stdout)
        except json.JSONDecodeError:
            continue
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        best_json = out_path
        best_payload = payload

        validate = _run(
            [
                str(python),
                str(SCRIPTS / "validate_meeting_artifacts.py"),
                "--json",
                str(out_path),
                "--participants",
                ",".join(participants),
            ],
            timeout=120,
            env={**os.environ, "MEETING_STRICT_MD": "1"},
        )
        (job_dir / f"validate-json-attempt{attempt}.txt").write_text(
            (validate.stdout or "") + (validate.stderr or ""),
            encoding="utf-8",
        )
        speaker_count = int(payload.get("speaker_count") or len(payload.get("speakers") or []))
        participant_count = len([name for name in participants if name.strip()])
        speaker_mapping_plausible = participant_count == 0 or speaker_count == participant_count
        if validate.returncode == 0 and speaker_mapping_plausible:
            final_json = job_dir / "meeting.json"
            final_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return final_json, {"strict": True, "attempts": attempt, "payload": payload}
        if validate.returncode == 0 and not speaker_mapping_plausible:
            (job_dir / f"validate-json-attempt{attempt}.txt").write_text(
                (validate.stdout or "")
                + (validate.stderr or "")
                + f"\nSTRICT_DOWNGRADED: speaker_count={speaker_count}, participant_count={participant_count}\n",
                encoding="utf-8",
            )

    if best_json:
        final_json = job_dir / "meeting.json"
        final_json.write_text(best_json.read_text(encoding="utf-8"), encoding="utf-8")
        return final_json, {"strict": False, "attempts": attempts, "payload": best_payload}
    return None, {"strict": False, "attempts": attempts, "payload": {}, "error": "diarization_failed"}


def _parse_json_stdout(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise json.JSONDecodeError("empty output", raw or "", 0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        return json.loads(text[start:end + 1])


def _fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _speaker_aliases(payload: dict[str, Any], participants: list[str] | None = None) -> dict[str, str]:
    aliases: dict[str, str] = {}
    raw_speakers: list[str] = []
    for segment in payload.get("segments") or []:
        raw = str(segment.get("speaker") or "UNKNOWN").strip() or "UNKNOWN"
        if raw not in raw_speakers:
            raw_speakers.append(raw)

    clean_participants = []
    for name in participants or []:
        clean = _clean_participant_name(str(name))
        if clean and clean.lower() != "meetingbot" and clean not in clean_participants:
            clean_participants.append(clean)

    if len(raw_speakers) == 1 and len(clean_participants) == 1:
        aliases[raw_speakers[0]] = f"Вероятно {clean_participants[0]} (не подтверждено diarization)"
        return aliases
    if len(raw_speakers) == 1 and len(clean_participants) > 1:
        aliases[raw_speakers[0]] = "Голосовой кластер 1 (имя не подтверждено: " + " / ".join(clean_participants) + ")"
        return aliases

    for raw in raw_speakers:
        aliases[raw] = f"Спикер {len(aliases) + 1}"
    return aliases


def _build_transcript(payload: dict[str, Any], aliases: dict[str, str]) -> str:
    lines: list[str] = []
    for segment in payload.get("segments") or []:
        start = float(segment.get("start") or 0.0)
        raw = str(segment.get("speaker") or "UNKNOWN").strip() or "UNKNOWN"
        speaker = aliases.get(raw, "Спикер без точного имени")
        text = str(segment.get("text") or "").strip() or "[неразборчиво]"
        lines.append(f"**[{_fmt_time(start)}] {speaker}:** {text}")
    return "\n".join(lines).strip()


def _extractive_fallback_analysis(transcript: str, quality: str) -> str:
    chunks = [line.strip() for line in transcript.splitlines() if line.strip()]
    sample = [re.sub(r"^\*\*\[[^]]+\]\s*[^:]+:\*\*\s*", "", line)[:220] for line in chunks[:8]]
    bullets = [f"- {line}" for line in sample[:5]] or ["- не указано"]
    return "\n".join(
        [
            "## Коротко",
            "",
            "- Автоаналитика LLM не сработала; сохранена best-effort выжимка и полная транскрибация.",
            *bullets,
            "",
            "## Решения",
            "",
            "- не указано",
            "",
            "## Задачи",
            "",
            "- не указано",
            "",
            "## Открытые вопросы",
            "",
            "- не указано",
            "",
            "## Подсказка нейросети / следующий шаг",
            "",
            "- Проверьте полный transcript ниже и вручную подтвердите решения/задачи, если качество распознавания низкое.",
            "- Если нужна нормальная диаризация, нужен рабочий HF token с доступом к gated pyannote model или другой локальный diarization backend.",
            "",
            "## Подводные камни",
            "",
            "- Имена из Google Meet показывают список участников, но сами по себе не дают привязку аудио-сегментов к голосам.",
            "- При whisper-only режиме все фразы могут попасть в один голосовой кластер.",
            "",
            "## Риски и качество",
            "",
            f"- {quality}",
        ]
    )


def _llm_analysis(job_dir: Path, transcript: str, participants: list[str], url: str, title: str, quality: str) -> str:
    prompt = f"""
Ты MeetingBot. На основе транскрипта встречи сделай аналитическую часть протокола на русском.

Правила:
- не выдумывай решения, задачи, сроки и участников;
- если данных нет, пиши "не указано";
- не используй raw labels вроде SPEAKER_00 или UNKNOWN;
- если имена участников нельзя уверенно связать со спикерами, так и напиши;
- обязательно добавь практическую подсказку: что в этой ситуации стоит сделать дальше;
- обязательно подсвети подводные камни/риски;
- задачи пиши чеклистом с владельцем/сроком только если они явно есть, иначе "не указано".

Ссылка: {url}
Название: {title or "не указано"}
Участники из Meet: {", ".join(participants) if participants else "не определены"}
Качество: {quality}

Транскрипт:
{transcript[:80000]}

Верни только Markdown без code fence и строго с разделами:
## Коротко
## Решения
## Задачи
## Открытые вопросы
## Подсказка нейросети / следующий шаг
## Подводные камни
## Риски и качество
""".strip()
    if not HERMES.is_file() and shutil.which(str(HERMES)) is None:
        return _extractive_fallback_analysis(transcript, quality)
    proc = _run([str(HERMES), "-p", ANALYSIS_PROFILE, "-z", prompt], timeout=900)
    (job_dir / "llm-analysis.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (job_dir / "llm-analysis.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    (job_dir / "llm-analysis.result.json").write_text(
        json.dumps({"returncode": proc.returncode, "profile": ANALYSIS_PROFILE}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if proc.returncode == 0 and proc.stdout.strip():
        text = proc.stdout.strip()
        text = re.sub(r"^```(?:markdown|md)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()
    return _extractive_fallback_analysis(transcript, quality)


def _write_markdown(
    path: Path,
    *,
    payload: dict[str, Any],
    participants: list[str],
    aliases: dict[str, str],
    transcript: str,
    analysis: str,
    url: str,
    title: str,
    quality: str,
    recording: Path,
    wav_path: Path,
) -> None:
    duration = float(payload.get("duration_seconds") or 0.0)
    speaker_rows = [f"- {alias}: отдельный голосовой кластер {idx}" for idx, alias in enumerate(aliases.values(), start=1)]
    if not speaker_rows:
        speaker_rows = ["- Спикер без точного имени: речь не распознана"]
    md = [
        "# Протокол встречи",
        "",
        f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Ссылка:** {url}",
        f"**Название:** {title or 'не указано'}",
        f"**Участники:** {', '.join(participants) if participants else 'не определены автоматически'}",
        f"**Длительность аудио:** {round(duration / 60)} минут" if duration else "**Длительность аудио:** не определена",
        f"**Качество:** {quality}",
        f"**Запись:** {recording}",
        f"**WAV:** {wav_path}",
        "",
        "## Спикеры",
        "",
        *speaker_rows,
        "",
        analysis.strip(),
        "",
        "## Полная транскрибация",
        "",
        transcript or "_Транскрипт пустой._",
        "",
    ]
    path.write_text("\n".join(md), encoding="utf-8")


def _validate_md(job_dir: Path, json_path: Path, md_path: Path, participants: list[str], strict: bool) -> bool:
    env = os.environ.copy()
    if not strict:
        env["MEETING_STRICT_MD"] = "0"
        env["MEETING_BEST_EFFORT_CONFIRMED"] = "1"
        env["MEETING_MAPPING_ATTEMPTS"] = "3"
        env["MEETING_CONTEXT_ROLE_MAPPING_ATTEMPTED"] = "1"
    proc = _run(
        [
            str(WHISPER_PYTHON if WHISPER_PYTHON.is_file() else Path(sys.executable)),
            str(SCRIPTS / "validate_meeting_artifacts.py"),
            "--json",
            str(json_path),
            "--md",
            str(md_path),
            "--participants",
            ",".join(participants),
        ],
        timeout=120,
        env=env,
    )
    (job_dir / "validate-md.txt").write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor recording backend and produce Markdown transcript.")
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--duration", default="2h")
    parser.add_argument("--deliver-to", default="telegram")
    parser.add_argument("--backend-url", default="http://127.0.0.1:3001")
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    job_dir = Path(args.job_dir)
    started_at = time.time()
    _write_json(job_dir / "monitor-state.json", {"state": "starting", "ts": datetime.now().isoformat(timespec="seconds")})

    recording = _wait_for_stable_recording(job_dir, args.duration, args.backend_url, started_at)
    if not recording:
        _write_json(job_dir / "monitor-state.json", {"state": "recording_timeout", "ts": datetime.now().isoformat(timespec="seconds")})
        send_result = _send(
            args.deliver_to,
            "MeetingBot: запись не найдена",
            (
                "MeetingBot backend принял задачу, но новый файл записи не появился или не стабилизировался.\n\n"
                f"Ссылка: {args.url}\n"
                f"Job: {job_dir}\n"
                f"Temp dir: {TEMPVIDEO}"
            ),
        )
        _write_json(job_dir / "send-error-result.json", send_result)
        return 2

    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
    safe_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    recording_copy = job_dir / f"recording{recording.suffix.lower()}"
    if recording.resolve() != recording_copy.resolve():
        recording_copy.write_bytes(recording.read_bytes())
    wav_path = job_dir / "recording.wav"
    enhanced_wav_path = job_dir / "recording.cleaned.wav"
    trimmed_wav_path = job_dir / "recording.asr.wav"
    _write_json(job_dir / "recording.json", {"source": str(recording), "copy": str(recording_copy), "bytes": recording.stat().st_size})

    if not _convert_to_wav(recording_copy, wav_path):
        _write_json(job_dir / "monitor-state.json", {"state": "ffmpeg_failed", "recording": str(recording_copy), "ts": datetime.now().isoformat(timespec="seconds")})
        _send(args.deliver_to, "MeetingBot: ошибка обработки записи", f"FFmpeg не смог конвертировать запись.\n\nJob: {job_dir}\nФайл: {recording_copy}")
        return 3

    cleanup_wav_path = enhanced_wav_path if _enhance_wav_for_asr(wav_path, enhanced_wav_path) else wav_path
    transcribe_wav_path = _trim_trailing_silence_for_asr(cleanup_wav_path, trimmed_wav_path, job_dir)
    _write_json(
        job_dir / "recording.json",
        {
            "source": str(recording),
            "copy": str(recording_copy),
            "wav": str(wav_path),
            "cleanupWav": str(cleanup_wav_path),
            "transcribeWav": str(transcribe_wav_path),
            "audioCleanup": cleanup_wav_path == enhanced_wav_path,
            "tailTrimmed": transcribe_wav_path == trimmed_wav_path,
            "bytes": recording.stat().st_size,
        },
    )

    participants = _participants(started_at)
    _write_json(job_dir / "participants.json", {"participants": participants})
    json_path, diarization_info = _diarize(job_dir, transcribe_wav_path, participants)
    if not json_path:
        _write_json(job_dir / "monitor-state.json", {"state": "diarization_failed", "info": diarization_info, "ts": datetime.now().isoformat(timespec="seconds")})
        _send(args.deliver_to, "MeetingBot: транскрибация не удалась", f"Не удалось получить JSON транскрипта.\n\nJob: {job_dir}")
        return 4

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    strict = bool(diarization_info.get("strict"))
    attempts_used = int(diarization_info.get("attempts") or 1)
    diarization_mode = str(payload.get("diarization_mode") or "unknown")
    diarization_error = str(payload.get("diarization_error") or "").strip()
    if strict:
        quality = f"normal-success: Whisper + diarization прошли strict validation за {attempts_used} попытк(и)"
    elif diarization_mode == "whisper_only" and ("gated repo" in diarization_error.lower() or "401" in diarization_error):
        quality = (
            f"best-effort после {attempts_used} попыток: pyannote diarization недоступна без HF-доступа, "
            "сохранена Whisper-транскрибация одним голосовым кластером"
        )
    else:
        quality = (
            f"best-effort после {attempts_used} попыток: транскрипт готов, "
            "но diarization/маппинг спикеров требует ручной проверки"
        )
    aliases = _speaker_aliases(payload, participants)
    transcript = _build_transcript(payload, aliases)
    (job_dir / "transcript.md").write_text(transcript + "\n", encoding="utf-8")
    analysis = _llm_analysis(job_dir, transcript, participants, args.url, args.title, quality)

    md_path = job_dir / "meeting-transcript.md"
    _write_markdown(
        md_path,
        payload=payload,
        participants=participants,
        aliases=aliases,
        transcript=transcript,
        analysis=analysis,
        url=args.url,
        title=args.title,
        quality=quality,
        recording=recording_copy,
        wav_path=transcribe_wav_path,
    )
    md_ok = _validate_md(job_dir, json_path, md_path, participants, strict)
    final_path = MEETINGS_DIR / f"meeting_{safe_stamp}.md"
    final_path.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    result = {
        "summaryPath": str(final_path),
        "jobSummaryPath": str(md_path),
        "jsonPath": str(json_path),
        "transcriptPath": str(job_dir / "transcript.md"),
        "recordingPath": str(recording_copy),
        "wavPath": str(transcribe_wav_path),
        "originalWavPath": str(wav_path),
        "participants": participants,
        "strict": strict,
        "mdValidationOk": md_ok,
        "finishedAt": datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(job_dir / "result.json", result)
    _write_json(job_dir / "monitor-state.json", {"state": "done", "result": result, "ts": datetime.now().isoformat(timespec="seconds")})

    note = (
        "Готов текстовый файл с транскрибацией встречи.\n\n"
        f"Ссылка: {args.url}\n"
        f"Качество: {quality}\n"
        f"Job: {job_dir}\n\n"
        f"[[as_document]]\nMEDIA:{final_path}"
    )
    send_result = _send(args.deliver_to, "MeetingBot: транскрибация готова", note)
    _write_json(job_dir / "send-result.json", send_result)
    return 0 if not send_result.get("error") else 5


if __name__ == "__main__":
    raise SystemExit(main())
