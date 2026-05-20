# Final Markdown output format

The final Markdown file is the product artifact. It is designed to be readable by a human and usable by later automation.

## Recommended structure

```markdown
# Протокол встречи

**Дата:** 2026-05-20 19:44
**Ссылка:** https://meet.google.com/...
**Название:** не указано
**Участники:** Алексей Ульянов, MeetingBot
**Длительность аудио:** 45 минут
**Качество:** strict / best-effort with reason

## Коротко
- ...

## Решения
- ...

## Задачи
- [ ] Задача — Owner: ..., deadline: ...

## Открытые вопросы
- ...

## Подсказка нейросети / следующий шаг
- ...

## Подводные камни
- ...

## Риски и качество
- ...

## Транскрипт по времени
**[00:15] Алексей:** ...
**[00:42] Мария:** ...
```

## Metadata

Metadata should say what is known, not what would look nice:

- date/time;
- meeting URL, if safe to keep locally;
- title, or `не указано`;
- participants extracted from Meet;
- audio duration;
- quality status.

## Summary

The summary is a factual compressed view of the meeting:

- what was discussed;
- what changed;
- what was agreed;
- what remains unclear.

Do not invent decisions to make the summary look useful.

## Decisions

A decision is only something that was explicitly agreed or clearly concluded.

Good:

```markdown
- Recording pipeline: keep local-first recording and process audio on the Mac mini.
```

Bad:

```markdown
- We should probably use Notion later.
```

## Tasks

Tasks should include owner/deadline only when evidence exists.

If unclear:

```markdown
- [ ] Improve active-speaker capture — Owner: requires clarification; deadline: —
```

## Open questions

Use this for unresolved items:

- missing access;
- unclear owner;
- unconfirmed technical decision;
- diarization or mapping uncertainty.

## AI recommendation

This section is allowed to add value beyond the transcript, but it must be labeled as AI recommendation, not meeting fact.

Good recommendations:

- next debugging step;
- missing quality gate;
- risk in current process;
- suggested agenda for the next meeting.

## Risks and quality

Always state quality honestly.

Examples:

```markdown
**Качество:** strict — pyannote ran, transcript segments exist, speaker mapping is supported.
```

```markdown
**Качество:** best-effort — pyannote found two voice clusters, but only one non-bot participant was captured; speaker-to-person mapping needs manual review.
```

## Transcript

Transcript goes at the bottom so the top of the document remains useful.

Rules:

- keep timestamps;
- use real names only when supported;
- do not leave raw `SPEAKER_00` labels in normal-success output;
- use `[неразборчиво]` for unclear fragments;
- do not rewrite meaning for style.

## How transcription is produced

The transcript comes from:

1. original recording file;
2. FFmpeg WAV conversion;
3. audio cleanup;
4. terminal silence trim;
5. MLX Whisper segments;
6. pyannote speaker clusters;
7. overlap-based segment-to-speaker assignment;
8. optional name/context mapping;
9. Markdown assembly and validation.

The final text is not just a raw Whisper dump. It should be a quality-gated protocol with transcript evidence at the end.
