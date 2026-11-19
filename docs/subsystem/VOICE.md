# Voice bridge — specification (F10, prototype)

Status: **prototype implemented** (2026-11-18). Owner: dev. Language: American English in code/docs.

## 1. Purpose

Let a user with limited mobility or vision dictate prompts to OpenCode without
running a local speech model. Audio capture and transport are local; inference
is delegated to Groq Whisper (open-weight model behind an OpenAI-compatible
endpoint). The transcript becomes an ordinary user prompt.

Audio replies (TTS) are deliberately deferred to the validation iteration.

## 2. Decisions (locked 2026-11-18)

| Topic | Decision |
|---|---|
| STT provider | **Groq** free tier; `whisper-large-v3-turbo` (`$0.04/audio hour`) |
| Language | Spanish default (`language="es"`); multilingual via tool argument |
| Capture | `pw-record --rate 16000 --channels 1 --format s16` |
| Push-to-talk | `SUPER+ALT+SHIFT+V` press -> start, release -> stop (`{ release = true }`) |
| Delivery | kitty Wayland PTY master, automatic fallback to `wl-copy` |
| Agent access | local stdio MCP server `voice`: `listen`, `transcribe`, `last`, `languages` |
| Fallback | `/voice` command injects `last.txt` through a shell block |
| Secret | `GROQ_API_KEY` env / `VOICE_KEY_FILE`; never in `rules.toml` or logs |
| Limits | 20 RPM, 7.2K audio-seconds/hour, 28.8K/day, 25 MB per upload |

Cloudflare Workers AI Whisper was considered (zero data retention) but not
chosen; local Whisper/Vosk were discarded for lack of hardware headroom.

## 3. Architecture

```
key down ─→ pw-record (16 kHz mono) ─→ capture.wav
key up   ─→ Groq Whisper ─→ last.txt + last.json ─→ PTY master / clipboard ─→ OpenCode
                                  └─→ MCP voice_last / voice_listen ─→ agent context
```

`~/.local/state/voice-bridge/` holds the WAV, recorder pid, log and last result.
`rules.toml` holds non-secret defaults. No daemon, no socket, no port.

## 4. Tools

| Tool | Returns |
|---|---|
| `voice_listen(seconds?, language?)` | `{text, language, model, seconds}` after recording |
| `voice_transcribe(path, language?, hint?)` | transcript of an existing WAV |
| `voice_last()` | last transcript, no recording |
| `voice_languages()` | supported ISO-639-1 codes |

The `voice-context` skill supplies vocabulary (`OpenCode`, `Hyprland`,
`Questline`, `linux zeep`, `PipeWire`, `MCP`, `voice-bridge`, `push to talk`) to
the Whisper `prompt` field (max 224 tokens) and to the agent.

## 5. Verification

```sh
python3 herramientas/voice-bridge/tests/smoke.py   # 12 offline checks
python3 herramientas/voice-bridge/voicectl.py status
python3 herramientas/voice-bridge/voicectl.py listen --seconds 5
luac -p ~/.config/hypr/UserConfigs/user_keybinds.lua
```

## 6. Risks and rollback

- The PTY backend assumes the focused window is kitty; otherwise clipboard is used.
- Audio leaves the machine; keep the key out of configs and logs.
- 429 responses include `retry-after`; the CLI surfaces it in the error.
- Rollback: disable `mcp.servers.voice`, remove the two binds, keep the state
  directory for inspection. Do not touch TimeShift or system configuration.

## 7. Next iteration

Add `voice_speak` (Groq TTS) and test the full loop: dictate -> answer in audio.
Then evaluate the advanced TUI plugin with an in-composer keybind.
