#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("MEETINGBOT_PROJECT_ROOT", SCRIPT_DIR.parent)).resolve()
WORKSPACE = Path(os.environ.get("MEETINGBOT_WORKSPACE", PROJECT_ROOT / "runtime")).resolve()
BACKEND_REPO = Path(os.environ.get("MEETINGBOT_BACKEND_REPO", PROJECT_ROOT / "backend")).resolve()
JOBS_DIR = Path(os.environ.get("MEETINGBOT_JOBS_DIR", WORKSPACE / "jobs")).resolve()
MONITOR = SCRIPT_DIR / "meetingbot_recording_monitor.py"
MEET_RE = re.compile(r"^https://meet\.google\.com/[A-Za-z0-9-]+(?:[/?#].*)?$")
DEFAULT_BACKEND_URL = "http://127.0.0.1:3001"


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


def _meeting_id(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1].split("?")[0].split("#")[0]
    return re.sub(r"[^A-Za-z0-9_-]+", "-", tail)[:80] or "meet"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _http_json(method: str, url: str, payload: dict | None = None, timeout: int = 10) -> tuple[int, dict | str]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw or "{}")
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw or "{}")
        except json.JSONDecodeError:
            return exc.code, raw


def _health(backend_url: str) -> dict:
    try:
        code, body = _http_json("GET", f"{backend_url}/health", timeout=3)
        return {"ok": code == 200, "status": code, "body": body}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _start_backend(job_dir: Path, backend_url: str) -> dict:
    auto_start = os.environ.get("MEETINGBOT_BACKEND_AUTO_START", "1").strip().lower() not in ("0", "false", "no")
    if not auto_start:
        return {"ok": False, "reason": "backend_not_running_and_autostart_disabled"}

    log_path = job_dir / "backend-start.log"
    env = os.environ.copy()
    env["COMPOSE_PROJECT_NAME"] = os.environ.get("MEETINGBOT_COMPOSE_PROJECT", "meetingbot")
    with log_path.open("ab", buffering=0) as log_fh:
        proc = subprocess.Popen(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=str(BACKEND_REPO),
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            env=env,
        )
        rc = proc.wait(timeout=int(os.environ.get("MEETINGBOT_BACKEND_BUILD_TIMEOUT", "900")))
    if rc != 0:
        return {"ok": False, "reason": "docker_compose_failed", "returncode": rc, "log": str(log_path)}

    deadline = time.time() + int(os.environ.get("MEETINGBOT_BACKEND_READY_TIMEOUT", "120"))
    last = {}
    while time.time() < deadline:
        last = _health(backend_url)
        if last.get("ok"):
            return {"ok": True, "health": last, "log": str(log_path)}
        time.sleep(3)
    return {"ok": False, "reason": "backend_health_timeout", "lastHealth": last, "log": str(log_path)}


def _recording_files() -> list[str]:
    root = BACKEND_REPO / "dist" / "_tempvideo"
    if not root.is_dir():
        return []
    return sorted(
        str(path)
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".webm", ".wav", ".mp4", ".mkv"}
    )


def _is_busy(backend_url: str) -> dict:
    try:
        code, body = _http_json("GET", f"{backend_url}/isbusy", timeout=5)
        busy = False
        if isinstance(body, dict):
            busy = bool((body.get("data") or 0) == 1)
        return {"ok": code == 200, "busy": busy, "status": code, "body": body}
    except Exception as exc:
        return {"ok": False, "busy": False, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Start recording-first MeetingBot job.")
    parser.add_argument("url")
    parser.add_argument("duration", nargs="?", default="2h")
    parser.add_argument("--deliver-to", default=os.environ.get("MEETINGBOT_DELIVER_TO", "telegram"))
    parser.add_argument("--backend-url", default=os.environ.get("MEETINGBOT_BACKEND_URL", DEFAULT_BACKEND_URL))
    parser.add_argument("--title", default="")
    parser.add_argument("--foreground-monitor", action="store_true")
    args = parser.parse_args()

    url = args.url.strip()
    if not MEET_RE.match(url):
        print("refusing: expected https://meet.google.com/... URL", file=sys.stderr)
        return 2

    backend_url = args.backend_url.rstrip("/")
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    job_id = f"recording-{now}-{_meeting_id(url)}"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=False)

    baseline = _recording_files()
    _write_json(job_dir / "baseline-files.json", baseline)

    health = _health(backend_url)
    if not health.get("ok"):
        health = _start_backend(job_dir, backend_url)
    _write_json(job_dir / "backend-health.json", health)
    if not health.get("ok"):
        print(json.dumps({"ok": False, "jobId": job_id, "reason": "backend_unavailable", "backend": health}, ensure_ascii=False, indent=2))
        return 3

    busy = _is_busy(backend_url)
    _write_json(job_dir / "backend-busy.json", busy)
    if busy.get("busy"):
        print(json.dumps({"ok": False, "jobId": job_id, "reason": "backend_busy", "busy": busy}, ensure_ascii=False, indent=2))
        return 4

    payload = {
        "bearerToken": os.environ.get("MEETINGBOT_JOIN_TOKEN", "local-recording"),
        "url": url,
        "name": os.environ.get("MEETINGBOT_DISPLAY_NAME", "MeetingBot"),
        "teamId": os.environ.get("MEETINGBOT_TEAM_ID", "local-meetingbot"),
        "timezone": os.environ.get("HERMES_TIMEZONE", os.environ.get("TZ", "Asia/Tbilisi")),
        "userId": os.environ.get("MEETINGBOT_USER_ID", "local-user"),
        "eventId": job_id,
        "botId": job_id,
    }
    _write_json(job_dir / "join-payload-redacted.json", {**payload, "bearerToken": "<redacted>"})

    try:
        status, response = _http_json("POST", f"{backend_url}/google/join", payload=payload, timeout=20)
    except Exception as exc:
        response = {"error": f"{type(exc).__name__}: {exc}"}
        status = 0
    _write_json(job_dir / "join-response.json", {"status": status, "body": response})
    if status not in (200, 202):
        print(json.dumps({"ok": False, "jobId": job_id, "reason": "join_rejected", "status": status, "response": response}, ensure_ascii=False, indent=2))
        return 5

    meta = {
        "jobId": job_id,
        "mode": "recording-first",
        "url": url,
        "duration": args.duration,
        "durationSeconds": _duration_seconds(args.duration),
        "deliverTo": args.deliver_to,
        "title": args.title,
        "backendUrl": backend_url,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "jobDir": str(job_dir),
    }
    _write_json(job_dir / "job.json", meta)

    cmd = [
        sys.executable,
        str(MONITOR),
        "--job-dir",
        str(job_dir),
        "--url",
        url,
        "--duration",
        args.duration,
        "--deliver-to",
        args.deliver_to,
        "--backend-url",
        backend_url,
    ]
    if args.title:
        cmd.extend(["--title", args.title])

    if args.foreground_monitor:
        return subprocess.call(cmd)

    log_path = job_dir / "monitor.log"
    with log_path.open("ab", buffering=0) as log_fh:
        monitor_env = os.environ.copy()
        for key in (
            "HERMES_CRON_AUTO_DELIVER_PLATFORM",
            "HERMES_CRON_AUTO_DELIVER_CHAT_ID",
            "HERMES_CRON_AUTO_DELIVER_THREAD_ID",
        ):
            monitor_env.pop(key, None)
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
            env=monitor_env,
        )

    meta["monitorPid"] = proc.pid
    meta["monitorLog"] = str(log_path)
    _write_json(job_dir / "job.json", meta)
    print(
        json.dumps(
            {
                "ok": True,
                "jobId": job_id,
                "pid": proc.pid,
                "jobDir": str(job_dir),
                "backendUrl": backend_url,
                "deliverTo": args.deliver_to,
                "message": "Recording-first MeetingBot accepted the link. Final Markdown transcript will be written to runtime/meetings or sent through the configured notifier.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
