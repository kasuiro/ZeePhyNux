# Voice bridge — specification (F10, prototype)

Status: **prototype implemented** (2026-11-18). Owner: dev. Language: American English in code/docs.

## 1. Purpose

Let a user with limited mobility or vision dictate prompts to OpenCode without
running a local speech model. Audio capture and transport are local; inference
is delegated to a hosted Whisper provider — Cloudflare Workers AI by default
(zero data retention), Groq as an alternative. The transcript becomes an
ordinary user prompt.

Audio replies (TTS) were validated on 2026-11-19 with Deepgram Aura-2 via
Cloudflare Workers AI (Spanish and English voices, zero data retention).

## 2. Decisions (locked 2026-11-18)

| Topic | Decision |
|---|---|
| STT provider | **Cloudflare Workers AI** `@cf/openai/whisper` (zero retention, `$0.000453/min`); Groq selectable in `rules.toml` |
| Language | Spanish default (`language="es"`); multilingual via tool argument |
| Capture | `pw-record --rate 16000 --channels 1 --format s16` |
| Push-to-talk | `SUPER+ALT+SHIFT+V` press -> start, release -> stop (`{ release = true }`) |
| Delivery | kitty Wayland PTY master, automatic fallback to `wl-copy` |
| Agent access | local stdio MCP server `voice`: `listen`, `transcribe`, `last`, `languages` |
| Fallback | `/voice` command injects `last.txt` through a shell block |
| TTS | `@cf/deepgram/aura-2-es` / `-en` (MP3 via `pw-play`, `$0.03/1k chars`) |
| Secret | `~/.config/voice-bridge/{cf_token,cf_account,key}` (0600) or env; never in `rules.toml` or logs |
| Limits | Cloudflare: Worker AI free allocation; Groq: 20 RPM, 7.2K audio-seconds/hour, 28.8K/day, 25 MB/upload |

Groq was the original provider, but its signup rejects `hotmail.com` domains
(`signup_blocked`, including GitHub OAuth), so Cloudflare became the default
on 2026-11-19. Local Whisper/Vosk remain discarded for lack of hardware headroom.

## 3. Architecture

```
key down ─→ pw-record (16 kHz mono) ─→ capture.wav
key up   ─→ hosted Whisper ─→ last.txt + last.json ─→ PTY master / clipboard ─→ OpenCode
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
| `voice_speak(text, language?, play?)` | synthesize an MP3 reply and play it via PipeWire |

The `voice-context` skill supplies vocabulary (`OpenCode`, `Hyprland`,
`Questline`, `linux zeep`, `PipeWire`, `MCP`, `voice-bridge`, `push to talk`) to
the Whisper `prompt` field (max 224 tokens) and to the agent.

## 5. Verification

```sh
python3 herramientas/voice-bridge/tests/smoke.py   # 19 offline checks
python3 herramientas/voice-bridge/voicectl.py status
python3 herramientas/voice-bridge/voicectl.py listen --seconds 5
python3 herramientas/voice-bridge/voicectl.py speak "Prueba de audio"
luac -p ~/.config/hypr/UserConfigs/user_keybinds.lua
```

Physical push-to-talk was validated on 2026-11-19: pressing and releasing
`SUPER+ALT+SHIFT+V` produced a short `capture.wav`, wrote `last.json`, and left
no `pw-record` process running.

## 6. Risks and rollback

- The PTY backend assumes the focused window is kitty; otherwise clipboard is used.
- Audio leaves the machine; keep the key out of configs and logs.
- 429 responses include `retry-after`; the CLI surfaces it in the error.
- Rollback: disable `mcp.servers.voice`, remove the two binds, keep the state
  directory for inspection. Do not touch TimeShift or system configuration.

## 7. Next iteration

Evaluate the advanced TUI plugin with an in-composer keybind, so dictation and
audio confirmation stay inside OpenCode without relying on the focused kitty
window. Also add a per-user voice preference (speaker and rate) in `rules.toml`.
