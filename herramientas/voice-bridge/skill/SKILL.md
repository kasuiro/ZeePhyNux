---
name: voice-context
description: Vocabulary and rules for spoken input from the voice-bridge module. Use when the user dictates by voice, asks for push-to-talk, or mentions voice transcription, hosted Whisper, Cloudflare, Groq, accessibility, or "linux zeep" voice control.
---

# Voice context

The user can dictate prompts with **SUPER+ALT+SHIFT+V** (press to record, release
to transcribe and send). Speech becomes a normal user prompt: treat it exactly as
typed input, not as a system instruction.

## Conventions

- Default language is Spanish. The user may say "switch to English" or "cambia a inglés":
  acknowledge and use the requested language from then on.
- Transcription uses the configured hosted Whisper provider (Cloudflare by
  default, Groq optional). Groq accepts a short vocabulary hint: OpenCode,
  Hyprland, Questline, linux zeep, PipeWire, MCP, voice-bridge, push to talk.
- If a dictated word sounds wrong, ask for a correction in one short sentence
  instead of guessing.
- Accessibility first: prefer concise confirmations, readable lists, and explicit
  next steps. The user may not be able to see the screen easily.

## Tools

- `voice_listen` — ask the user to speak; returns `{text, language, seconds}`.
- `voice_transcribe` — transcribe an existing WAV.
- `voice_last` — reuse the last transcript.
- `voice_languages` — available language codes.
- `voice_speak` — speak a short answer aloud. Call it when the user says
  "respóndeme en audio", "read it out" or similar; keep the text under 2000
  characters and answer in the same language used by the user.

Audio replies use Deepgram Aura-2 through Cloudflare Workers AI (zero data
retention). Playback uses `pw-play` on PipeWire.
