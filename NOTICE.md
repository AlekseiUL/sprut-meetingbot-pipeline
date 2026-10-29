# NOTICE

Sprut MeetingBot Pipeline is maintained by Aleksei Ulianov / Sprut_AI.

Canonical source:
https://github.com/AlekseiUL/sprut-meetingbot-pipeline

This repository packages a local recording-first MeetingBot pipeline for Google Meet:

- local Docker/Playwright meeting recorder;
- WebM/WAV recording artifacts;
- FFmpeg cleanup and terminal-silence trim;
- local Whisper transcription through MLX Whisper;
- speaker diarization through pyannote.audio;
- strict/best-effort Markdown generation and validation.

## Upstream attribution

The browser automation backend component includes code derived from the MIT-licensed ScreenApp meeting-bot project:

- Upstream repository: https://github.com/screenappai/meeting-bot
- Upstream copyright: Copyright (c) 2025 ScreenApp.io
- License: MIT

Sprut_AI modifications include local remote-dispatch workflow, recording-first pipeline hardening, Google Meet participant/tile label capture improvements, Docker/Xvfb startup fixes, local ASR/diarization monitor scripts, quality gates, and documentation for local Apple Silicon / Mac mini deployment.

## Vendored dependency

`backend/vendor/deepmerge-hardened` derives from deepmerge 4.3.1, copyright
(c) 2012 James Halliday, Josh Duff, and other contributors, under the MIT
license. Its original license is included alongside the source. Sprut_AI's
local change filters prototype-control keys on both merge paths to address
GHSA-gcqx-w48m-w2h4. See the vendored README for exact provenance, compatibility,
verification and maintenance boundaries. This is not an upstream release.

## Attribution

Where permitted by the applicable license, if you reuse, fork, modify, package, or publish this work, keep the original copyright and license notice and link back to the canonical repository.
