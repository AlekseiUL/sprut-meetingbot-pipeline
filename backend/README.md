# Backend component

This directory contains the local browser automation backend used by Sprut MeetingBot Pipeline.

For normal installation and operation, start from the repository root:

- `../README.md`
- `../docs/LOCAL_MAC_SETUP.md`
- `../docs/REMOTE_DISPATCH.md`
- `../docs/GOOGLE_MEET_ACCESS.md`
- `../docs/QUALITY_GATES.md`

## What this backend does

- Exposes local HTTP endpoints, including `/health`, `/isbusy`, and `/google/join`.
- Starts a Playwright/Chromium browser inside Docker.
- Joins Google Meet as a regular participant when access is allowed.
- Writes local recording artifacts for the outer pipeline to process.
- Leaves transcription, diarization, quality gates, and final Markdown assembly to the root `scripts/` pipeline.

Default local port in this package: `3001`.

## Quick local smoke

```bash
npm ci
npm run build

# Docker Compose v2:
docker compose up -d --build

# If your machine has the standalone binary instead:
# docker-compose up -d --build

curl -sS http://127.0.0.1:3001/health
curl -sS http://127.0.0.1:3001/isbusy
```

Stop it with:

```bash
npm run stop
```

## Docker Compose compatibility

`package.json` supports both Docker Compose forms:

- `docker compose` — Docker Compose v2 plugin;
- `docker-compose` — standalone binary.

The docs show v2 first because that is the current Docker default, but the standalone binary is supported for older/local setups.

## Access boundary

This backend does not bypass Google Meet access controls.

The Meet must allow the bot to enter through one of the normal paths:

- guest access is allowed;
- the host admits the bot from lobby;
- a dedicated bot Google account is invited;
- a dedicated bot browser profile is authorized locally.

`/google/join` returning accepted only means the backend accepted the job. Real recording starts only after the bot has actually joined and the recording file begins to grow.

## Attribution

The browser automation backend component includes code derived from the MIT-licensed ScreenApp meeting-bot project:

- upstream repository: https://github.com/screenappai/meeting-bot
- upstream copyright: Copyright (c) 2025 ScreenApp.io
- license: MIT

Sprut_AI additions live mostly around the backend: remote dispatch, recording-first monitor scripts, FFmpeg cleanup, MLX Whisper transcription, pyannote diarization, strict/best-effort validation, and Mac mini / home-server documentation.

See root `NOTICE.md` for the full attribution note.

## Security notes

Do not commit or bake into Docker images:

- `.env` files with real tokens;
- Google auth state, cookies, or browser profiles;
- meeting recordings;
- transcripts from private meetings;
- debug videos/screenshots.

Use `../config/meetingbot.env.example` as the public configuration template.
