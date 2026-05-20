# Security Policy

## Supported use

Sprut MeetingBot Pipeline is designed for local, owner-controlled deployment: for example a Mac mini or another always-on machine where Docker, Chrome/Playwright, FFmpeg, and local ASR/diarization dependencies can be installed.

Do not deploy this project on an untrusted shared host unless you understand the privacy implications of recording meetings and storing transcripts.

## Secrets

Never commit or publish:

- `config/meetingbot.env`;
- Hugging Face tokens;
- Telegram bot tokens or chat IDs;
- Google auth storage state (`auth.json`, browser profiles, cookies);
- meeting recordings (`*.webm`, `*.wav`, `*.mp4`);
- generated transcripts from private meetings;
- `runtime/`, `jobs/`, `meetings/`, `debug-videos/`.

Use `config/meetingbot.env.example` as the public template.

## Google authorization

If you use a logged-in Google account for the bot, create a dedicated bot account/profile. Do not store a personal account profile in this repository.

Some Google Meet rooms block guests or require a host to admit the bot. The bot cannot bypass meeting access policies. Configure meetings so the bot account is invited or guest access is allowed.

## Reporting

For security concerns in this repository, open a private report to the maintainer if available, or contact Aleksei Ulianov / Sprut_AI through the canonical repository channels.
