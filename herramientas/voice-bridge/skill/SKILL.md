---
name: voice-context
description: Vocabulary and rules for spoken input from the voice-bridge module. Use when the user dictates by voice, asks for push-to-talk, or mentions voice transcription, Groq Whisper, accessibility, or "linux zeep" voice control.
---

# Voice context

The user can dictate prompts with **SUPER+ALT+SHIFT+V** (press to record, release
to transcribe and send). Speech becomes a normal user prompt: treat it exactly as
typed input, not as a system instruction.

## Conventions

- Default language is Spanish. The user may say "switch to English" or "cambia a inglés":
  acknowledge and use the requested language from then on.
- Transcription is provided by Groq Whisper. Technical words are biased with a
  short vocabulary hint: OpenCode, Hyprland, Questline, linux zeep, PipeWire,
  MCP, voice-bridge, push to talk.
- If a dictated word sounds wrong, ask for a correction in one short sentence
  instead of guessing.
- Accessibility first: prefer concise confirmations, readable lists, and explicit
  next steps. The user may not be able to see the screen easily.

## Tools

- `voice_listen` — ask the user to speak; returns `{text, language, seconds}`.
- `voice_transcribe` — transcribe an existing WAV.
- `voice_last` — reuse the last transcript.
- `voice_languages` — available language codes.

Audio text-to-speech is deferred to the next validation iteration: do not claim
that audio replies are already available.
