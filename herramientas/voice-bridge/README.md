# voice-bridge (prototype)

Spoken input for OpenCode agents on Debian 13 / Hyprland / Wayland, without a
local speech model. Audio goes to Groq Whisper; only capture and transport run
on this machine.

## Status

Prototype, phase 1: push-to-talk -> Spanish transcription -> prompt in OpenCode.
Audio replies (TTS) are deferred to the validation iteration.

## Layout

```
rules.toml            defaults; never stores the API key
voicectl.py           capture / transcribe / deliver CLI
mcp.py                stdio MCP server: listen, transcribe, last, languages
skill/SKILL.md        voice vocabulary and rules for the agent
commands/voice.md     /voice fallback command
tests/smoke.py        offline tests (no network, no microphone)
```

## Setup

1. Export the key in your own shell configuration (never in `rules.toml`):
   `set -gx GROQ_API_KEY <your-key>` (fish) or point `VOICE_KEY_FILE` at a 0600 file.
2. OpenCode loads the server from `~/.config/opencode/opencode.json` as
   `mcp.servers.voice`, with `GROQ_API_KEY = {env:GROQ_API_KEY}`.
3. Hyprland binds `SUPER+ALT+SHIFT+V`: press starts `voicectl.py start`, release
   runs `voicectl.py stop`. The transcript is typed into the focused kitty
   window via its Wayland PTY (`deliver.backend = "tty"`), with clipboard as
   automatic fallback.

## Flow

```
key down -> pw-record 16 kHz mono -> key up -> Groq Whisper -> last.txt
        -> PTY master / clipboard -> OpenCode composer -> Enter
```

The agent can also initiate a conversation turn with `voice_listen(seconds: 8)`.

## Languages

Spanish is the default (`language = "es"`). Change `language` via `rules.toml`,
a tool argument, or say "switch to English" (the skill applies it). Whisper is
multilingual; `voice_languages` lists the codes used here.

## Verification

```sh
python3 tests/smoke.py
python3 voicectl.py status
python3 voicectl.py listen --seconds 5
```

## Privacy and limits

- Audio is sent to Groq; keep the key out of configs and logs.
- Free tier: 20 requests/min, ~2 h audio/hour, ~8 h/day, 25 MB per upload.
- Rollback: disable the `voice` MCP server, remove the two Hyprland binds, and
  leave `~/.local/state/voice-bridge/` untouched for inspection.
