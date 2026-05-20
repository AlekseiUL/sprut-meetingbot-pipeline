# Quality gates

The pipeline must prefer correctness over a beautiful-looking protocol.

## Three-attempt rule

Transcription/diarization is attempted up to `MEETINGBOT_DIARIZATION_ATTEMPTS` times, default `3`.

After three failed strict attempts, a best-effort Markdown may still be produced, but it must clearly say what failed.

## Strict success

Strict success means:

- recording is non-empty;
- Whisper produced transcript segments;
- pyannote ran without a diarization error;
- participants/tile labels were extracted;
- speaker cluster count is plausible for the meeting;
- final Markdown has metadata, summary, decisions, tasks, questions, risks, next step, and transcript;
- raw labels such as `SPEAKER_00`, `UNKNOWN`, and `Спикер без точного имени` are not presented as normal success.

## Best-effort success

Best-effort is acceptable only when strict mapping cannot be proven after attempts. It must say clearly:

- diarization ran or failed;
- speaker-to-person mapping is uncertain;
- which evidence exists;
- which parts need manual review.

## Participant names are not diarization

Google Meet names identify who was present. They do not prove who spoke at a given timestamp.

Reliable `voice -> person` mapping needs more evidence:

- active speaker UI/tile snapshots over time;
- participant/tile label captures;
- pyannote speaker clusters;
- speech context such as “Алексей, что скажешь?” and reply order;
- manual or controlled calibration phrases in tests.

## ASR tail hallucination guard

Whisper can hallucinate repeated phrases over long silence. The monitor trims terminal silence before ASR when a long silent tail reaches the end of the WAV.

Original recordings are preserved; ASR receives a cleaned/trimmed derived WAV.

## Do not invent

If a task, owner, deadline, decision, or participant name is not supported by the transcript/evidence, write `не указано`, `требует уточнения`, or mark the mapping as uncertain.
