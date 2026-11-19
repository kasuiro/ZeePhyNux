# voice-bridge (prototype)

Spoken input for OpenCode agents on Debian 13 / Hyprland / Wayland, without a
local speech model. Audio goes to a hosted Whisper provider — Cloudflare Workers
AI by default (zero data retention), Groq as an alternative. Only capture and
transport run on this machine.

## Status

Prototype validated: push-to-talk -> Spanish transcription -> prompt in OpenCode,
plus audio replies via Deepgram Aura-2 on Cloudflare Workers AI.
The advanced TUI plugin is the next iteration.

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

1. Choose `[stt].provider` in `rules.toml` (`cloudflare` by default):
   - Cloudflare: put the token and account id in
     `~/.config/voice-bridge/cf_token` and `cf_account` (mode 0600), or export
     `CLOUDFLARE_API_TOKEN` and `CF_ACCOUNT_ID`.
   - Groq: put the key in `~/.config/voice-bridge/key` (0600), or export
     `GROQ_API_KEY` / `VOICE_KEY_FILE`.
   Files are read on every request, so OpenCode does not need a restart.
2. OpenCode loads the server from `~/.config/opencode/opencode.json` as
   `mcp.servers.voice`, with `GROQ_API_KEY = {env:GROQ_API_KEY}`.
3. Hyprland binds `SUPER+ALT+SHIFT+V`: press starts `voicectl.py start`, release
   runs `voicectl.py stop`. The transcript is typed into the focused kitty
   window via its Wayland PTY (`deliver.backend = "tty"`), with clipboard as
   automatic fallback.

## Flow

```
key down -> pw-record 16 kHz mono -> key up -> hosted Whisper -> last.txt
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
python3 voicectl.py speak "Prueba de audio"
```

## Privacy and limits

- Audio is sent to the selected provider; keep credentials out of configs/logs.
- Cloudflare Workers AI: zero data retention, `$0.000453` per audio minute.
- Groq free tier (if selected): 20 RPM, ~2 h audio/hour, ~8 h/day, 25 MB/upload.
- TTS: Deepgram Aura-2 (`$0.03/1k chars`), MP3 saved to `reply.mp3` in state dir.
- Rollback: disable the `voice` MCP server, remove the two Hyprland binds, and
  leave `~/.local/state/voice-bridge/` untouched for inspection.
