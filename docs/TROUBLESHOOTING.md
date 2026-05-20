# Troubleshooting

## `HTTP 202` returned, but no transcript appears

`202` means only that the backend accepted the job. Check the downstream chain:

```bash
curl -sS http://127.0.0.1:3001/isbusy
docker logs --tail 200 <backend-container>
find backend/dist/_tempvideo -type f -maxdepth 3
```

Look for:

- lobby/admission messages;
- browser launch errors;
- Playwright errors;
- recording file creation;
- file size growth.

## Bot is waiting in lobby

The meeting is restricted or the host has not admitted the bot. Admit `MeetingBot` or invite the dedicated bot Google account.

Do not say “recording started” until a recording file exists and grows.

## pyannote preflight fails

Run:

```bash
MEETINGBOT_CONFIG=config/meetingbot.env \
~/.sprut-meetingbot/whisper-env/bin/python scripts/meetingbot_pyannote_preflight.py
```

Common causes:

- `HF_TOKEN` is missing;
- Hugging Face account has not accepted `pyannote/speaker-diarization-3.1` terms;
- wrong Python env is used;
- `pyannote.audio` is not installed.

## Whisper repeats a phrase at the end

This is often ASR hallucination over terminal silence. Keep original audio, but send a trimmed ASR WAV to Whisper. This pipeline has `MEETINGBOT_TRIM_TRAILING_SILENCE=1` by default.

## Speaker names are wrong or missing

Participant names and speaker diarization are different things. The bot may know that `Aleksei` was present without knowing which voice cluster belongs to Aleksei.

For better mapping, implement active-speaker snapshots and controlled calibration phrases.

## Xvfb failed to start

Use `xvfb-run -a`, not a fixed display such as `:99`. This repository's `backend/start.sh` intentionally lets Xvfb choose a free display.

## PulseAudio monitor missing

Inside the backend container, check:

```bash
export XDG_RUNTIME_DIR=/run/user/0
export PULSE_SERVER=unix:/run/user/0/pulse/native
pactl info
pactl list sources short | grep virtual_output.monitor
```

The expected monitor source is `virtual_output.monitor`.
