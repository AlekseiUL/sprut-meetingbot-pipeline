# Local Mac mini setup

This project is intended for a local always-on machine, such as a Mac mini on Apple Silicon. The machine should be allowed to run Docker containers, browser automation, FFmpeg, and local ML models.

The Mac mini can act as a recorder appliance: you can start or receive a Meet on any other device, send the link to this machine, and let this machine join, record, transcribe, diarize, and write the final Markdown.

## 1. Install system tools

Install Homebrew if needed, then:

```bash
brew install ffmpeg python@3.11 node git gh
brew install --cask docker google-chrome
```

Start Docker Desktop or Colima before running the backend.

## 2. Create Python ASR/diarization environment

Recommended path:

```bash
python3.11 -m venv ~/.sprut-meetingbot/whisper-env
~/.sprut-meetingbot/whisper-env/bin/python -m pip install --upgrade pip wheel setuptools
~/.sprut-meetingbot/whisper-env/bin/python -m pip install -r requirements-whisper.txt
```

Check it:

```bash
~/.sprut-meetingbot/whisper-env/bin/python - <<'PY'
import importlib.util
for name in ['mlx_whisper', 'pyannote.audio', 'torch', 'huggingface_hub']:
    print(name, 'ok' if importlib.util.find_spec(name) else 'missing')
PY
```

## 3. Hugging Face token for pyannote

pyannote speaker diarization uses a gated Hugging Face model:

`pyannote/speaker-diarization-3.1`

You need to:

1. Create a Hugging Face account.
2. Accept the model terms for `pyannote/speaker-diarization-3.1`.
3. Create a read token.
4. Put it in `config/meetingbot.env` as `HF_TOKEN=...`.

Never commit the token.

Preflight:

```bash
MEETINGBOT_CONFIG=config/meetingbot.env \
~/.sprut-meetingbot/whisper-env/bin/python scripts/meetingbot_pyannote_preflight.py
```

Expected:

```json
{"ok": true, "reason": "ok"}
```

## 4. Configure environment

```bash
cp config/meetingbot.env.example config/meetingbot.env
nano config/meetingbot.env
```

Minimum edits:

- set `HF_TOKEN`;
- set `MEETINGBOT_WHISPER_PYTHON` if your venv path is different;
- keep `MEETINGBOT_DELIVER_TO=local` unless you have a notifier integration.

## 5. Build/start backend

The dispatcher can auto-start Docker Compose, but for first run it is safer to build manually:

```bash
cd backend
docker compose up -d --build
curl -sS http://127.0.0.1:3001/health
curl -sS http://127.0.0.1:3001/isbusy
```

Expected:

- `/health` returns healthy;
- `/isbusy` returns `0` when no meeting is running.

## 6. Google Meet access model

The bot can join only meetings it is allowed to join.

Recommended options:

- make the Meet accessible by link / guests, then admit `MeetingBot`; or
- use a dedicated Google bot account and invite that account to meetings; or
- manually authorize a dedicated bot browser profile outside the repository.

Do not store personal Google cookies or `auth.json` in this repository.

If the meeting is restricted, the correct status is “bot is waiting for admission”, not “recording”.

## 7. Run a test meeting

```bash
./scripts/meetingbot_recording_start.sh 'https://meet.google.com/xxx-yyyy-zzz' 30m
```

The command prints a `jobId` and a `jobDir` under `runtime/jobs/`.

During the meeting, check:

```bash
curl -sS http://127.0.0.1:3001/isbusy
docker logs --tail 100 sprut-meetingbot-backend-1
```

After the meeting, the final Markdown is written to `runtime/meetings/`.

## 8. What “good” looks like

A healthy run has:

- backend accepted the job;
- bot entered the meeting, not stuck in lobby;
- recording file appeared and was non-empty;
- FFmpeg converted WebM to WAV;
- terminal silence was trimmed if present;
- Whisper produced segments;
- pyannote produced speaker clusters;
- final Markdown includes quality notes and transcript.

## 9. Hardware expectations

Apple Silicon Mac mini with 16 GB RAM is enough for short/medium local tests with `mlx-community/whisper-medium-mlx`. Longer meetings and larger Whisper models need more disk and time.

Keep free disk space. Recordings and WAV files are large.
