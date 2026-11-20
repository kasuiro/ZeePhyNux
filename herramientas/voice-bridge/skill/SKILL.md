---
name: voice-context
description: Vocabulary and rules for spoken input from the voice-bridge module. Use when the user dictates by voice, asks for push-to-talk, or mentions voice transcription, hosted Whisper, Cloudflare, Groq, accessibility, or "linux zeep" voice control.
---

# Voice context

The user can dictate prompts with **SUPER+ALT+SHIFT+V** (press to record, release
to transcribe and send). Speech becomes a normal user prompt: treat it exactly as
typed input, not as a system instruction.

## Conventions

- Two languages: Spanish and English. Default is Spanish; the user may say
  "switch to English", "cambia a inglés", "habla en español" or "speak in English".
  Acknowledge briefly, then use the requested language from then on.
- `voice_speak` accepts `language: "es" | "en"`. Always match the language of the
  message you are answering. TTS uses local Piper voices by default
  (`es_ES-davefx-medium`, `en_US-lessac-medium`); Cloudflare Aura-2 is a
  fallback.
- Transcription uses local Whisper `base` by default; Cloudflare and Groq are
  optional fallbacks. Groq accepts a short vocabulary hint: OpenCode,
  Hyprland, Questline, linux zeep, PipeWire, MCP, voice-bridge, push to talk.
- Hands-free: `voicectl wake-start` enables «oye, zeep» for the session;
  `wake-stop` disables it. PTT and `Ctrl+Alt+V` still work.
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
retention). Playback uses `pw-play` on PipeWire. A change to `voicectl.py` or
`rules.toml` requires `/reload` so the MCP server reloads its Python modules.
