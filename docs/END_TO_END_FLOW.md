# End-to-end chain: from Meet link to final Markdown

This document describes the full pipeline. It is the mental model to use when operating or debugging Sprut MeetingBot Pipeline.

## 1. Input: Google Meet URL

The input is a Meet link:

```text
https://meet.google.com/xxx-yyyy-zzz
```

The link can come from anywhere: a laptop, phone, calendar invite, chat message, or remote command. The important part is that the machine running this repository receives the link.

## 2. Dispatch

The start script creates a job:

```bash
./scripts/meetingbot_recording_start.sh '<meet-url>' 2h
```

It then:

1. loads `config/meetingbot.env`;
2. checks/starts the backend;
3. checks `/health`;
4. checks `/isbusy`;
5. sends `POST /google/join`;
6. starts the monitor in the background;
7. writes job metadata under `runtime/jobs/<jobId>/`.

`POST /google/join` returning `202` means the backend accepted the job. It does not prove that the bot has joined or that recording has started.

## 3. Google Meet join

The backend opens Playwright/Chromium in Docker and navigates to the Meet URL.

Typical states:

- pre-join screen;
- name input;
- ask-to-join / join-now click;
- lobby / waiting for host admission;
- joined call;
- ended/removed/left state.

The bot is a regular participant. It cannot bypass locked rooms.

## 4. Participant and tile name capture

The backend attempts to collect participant names from two sources:

- visible Meet tiles;
- People panel.

This matters because a visible tile may contain a display name that does not appear correctly in the People panel, or vice versa.

Example:

```text
ALEKSEI ULIANOV
Алексей Ульянов
MeetingBot
```

These names identify who was present. They do not automatically identify who spoke at a specific second.

## 5. Recording

The backend writes a local browser recording artifact, typically WebM, under:

```text
backend/dist/_tempvideo/
```

The external monitor watches for the new file and waits until it becomes stable/non-empty.

A recording is considered proven only when:

- the bot is not blocked in lobby;
- a fresh recording file exists;
- the file grows during the meeting;
- the file later stabilizes after the meeting.

## 6. Audio conversion and cleanup

The monitor copies the original recording into the job folder and converts it to WAV:

```text
recording webm -> recording wav
```

Then it creates ASR-friendly derived audio:

```text
recording cleaned wav
recording asr wav
```

Cleanup can include:

- high-pass filter;
- light denoise;
- loudness normalization;
- terminal silence trim.

Original recording is preserved. Whisper receives the cleaned/trimmed derived file.

## 7. Transcription and diarization

The pipeline runs:

- MLX Whisper for transcription;
- pyannote.audio for speaker diarization.

The diarization script produces JSON with:

- duration;
- speaker clusters;
- transcript segments;
- timestamps;
- best speaker label per segment.

## 8. Speaker/name mapping

The pipeline can combine:

- pyannote voice clusters;
- Meet participant/tile names;
- transcript context;
- explicit name mentions.

However, exact `voice -> real person` mapping is strict only when enough evidence exists.

For stronger mapping, capture active-speaker tile highlights over time:

```text
timestamp -> highlighted tile -> visible name
```

Then join that evidence with Whisper and pyannote segments.

## 9. Quality gates

The pipeline distinguishes:

- strict success: recording/transcription/diarization/mapping are plausible and validated;
- best-effort: useful transcript exists, but some mapping or diarization evidence is uncertain;
- failure: no usable transcript/recording after attempts.

The default diarization/transcription attempt count is 3.

## 10. Final Markdown

Final Markdown is written under:

```text
runtime/meetings/
```

It should include:

- metadata;
- quality note;
- summary;
- decisions;
- tasks;
- open questions;
- risks;
- next-step / AI recommendation;
- timestamped transcript at the end.

See `docs/OUTPUT_MARKDOWN.md`.

## 11. Optional delivery

By default this repository writes output locally. You can add your own notifier:

- Telegram bot;
- Hermes CLI;
- email;
- webhook;
- local dashboard;
- Obsidian/Notion exporter.

Keep delivery separate from core processing so private deployments can choose their own route.
