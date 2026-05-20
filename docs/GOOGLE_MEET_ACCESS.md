# Google Meet access and authorization

The bot needs normal Google Meet access. It is a participant, not an exploit.

## Why authorization may be needed

Google Meet rooms can be configured in different ways:

- open to anyone with the link;
- open to guests after host admission;
- restricted to organization accounts;
- restricted to invited calendar guests;
- blocked unless signed into a specific Google account.

If the room is restricted, a headless bot with only a link may stop at the lobby.

## Recommended access setups

### Option A: guest/open meetings

Use this for simple tests.

Requirements:

- Meet link accepts guests;
- host admits `MeetingBot` if prompted.

Pros:

- easiest setup;
- no Google cookies/account state.

Cons:

- someone may need to admit the bot;
- some organizations disable guest access.

### Option B: dedicated bot Google account

Use a separate Google account for the bot.

Requirements:

- create a dedicated account, not a personal account;
- invite it to meetings or allow it in your organization policy;
- authorize the browser profile locally on the Mac mini;
- keep auth state outside git.

Pros:

- more reliable for recurring meetings;
- cleaner security boundary;
- avoids using a personal account in automation.

Cons:

- first login may require manual setup;
- Google may ask for additional verification.

### Option C: manual host admission

Keep the bot as guest and admit it when it knocks.

Pros:

- no bot account setup.

Cons:

- recording does not start until admitted;
- unattended automation is weaker.

## What not to do

Do not commit:

- `auth.json`;
- cookies;
- browser profiles;
- screenshots with account information;
- `.env` files with tokens.

Do not use your personal Google browser profile unless you understand the risk.

## What the pipeline can prove

`/google/join` accepted means the backend accepted the job.

It does not prove access.

The bot is really inside only when backend/browser evidence shows Meet UI and the recording file starts growing.

## Practical test plan

1. Create a short test Meet.
2. Send the link to the Mac mini dispatcher.
3. Watch backend logs.
4. Confirm the bot appears as `MeetingBot`.
5. Admit it if needed.
6. Speak a few calibration lines:
   - “This is Aleksei speaking.”
   - “Now another speaker is speaking.”
7. End the meeting.
8. Check final Markdown quality.

Calibration lines are useful for evaluating diarization and name mapping, especially before active-speaker snapshots are implemented.
