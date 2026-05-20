# Remote dispatch: send the Meet link from anywhere, record on your home Mac mini

The core product idea is simple:

> Start or receive a Google Meet on any computer, phone, or work laptop. Send the Meet link to your own bot/controller. The recording and transcription happen on your always-on home server, for example a Mac mini.

This separates the meeting device from the recording machine.

## Why this matters

Most meeting recorders assume the recorder runs on the same machine where the user is working, or they require a hosted SaaS bot/account.

This pipeline is different:

- the meeting can be started on a laptop, office machine, phone, or another person's calendar;
- the link is enough to dispatch the bot;
- the bot joins from a controlled local Mac mini / home server;
- recordings, intermediate WAV files, transcripts, diarization JSON, and final Markdown stay on that local machine by default;
- the user does not need to keep the original computer open for transcription.

## Example flow

```text
1. You start a Google Meet on a work laptop.
2. You copy the Meet URL.
3. You send the URL to your automation channel or run the start script remotely.
4. The home Mac mini receives the URL.
5. The Mac mini starts the backend if needed.
6. The bot joins the Meet as MeetingBot.
7. The Mac mini records and processes the meeting locally.
8. Final Markdown appears under runtime/meetings/ or is sent through your optional notifier.
```

## Minimal remote command

If you can SSH into the Mac mini:

```bash
ssh mac-mini.local \
  'cd ~/sprut-meetingbot-pipeline && ./scripts/meetingbot_recording_start.sh "https://meet.google.com/xxx-yyyy-zzz" 2h'
```

If you use a Telegram/Hermes/Home Assistant/custom webhook controller, that controller should call the same script on the Mac mini.

## Safety model

The dispatcher should implement:

- allowlist: only trusted users can launch the bot;
- Meet URL validation: only real `https://meet.google.com/...` links;
- placeholder filtering: example links such as `xxx-yyyy-zzz` should not launch a real join;
- debounce: avoid launching the same Meet twice within a short window;
- backend health check before join;
- `/isbusy` check before join;
- no duplicate bot joins while a meeting is active.

This repository ships the local command pipeline. The exact external trigger can be Telegram, CLI over SSH, a webhook, or another private automation system.

## Important boundary

Remote dispatch is not Google Meet access bypass.

The bot still needs permission to enter the meeting:

- guest access enabled; or
- host admits `MeetingBot`; or
- dedicated bot Google account is invited; or
- dedicated bot browser profile is already authorized.

If the bot is in lobby, it is not recording yet.
