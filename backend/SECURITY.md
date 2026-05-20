# Backend Security Notes

This backend is bundled inside Sprut MeetingBot Pipeline. Use the repository root `SECURITY.md` as the source of truth.

Do not commit or bake into Docker images:

- `.env` files with tokens;
- Google auth/cookies/browser profiles;
- meeting recordings;
- transcripts;
- debug videos/screenshots from private meetings.

The backend runs as a local recorder component. It cannot bypass Google Meet access controls; invite/admit the bot account or allow guest access for the meeting.
