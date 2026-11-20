# Voice bridge — specification (F10, prototype)

Status: **prototype implemented** (2026-11-18). Owner: dev. Language: American English in code/docs.

## 1. Purpose

Let a user with limited mobility or vision dictate prompts to OpenCode.
Audio capture, inference and transport are local by default: `faster-whisper`
(model `base`, int8) runs in a dedicated venv under `~/.local/state/voice-bridge/`.
Vosk in Docker, Cloudflare Workers AI and Groq remain explicit alternatives.
The transcript becomes an ordinary user prompt.

Audio replies (TTS) are local by default since 2026-11-20: Piper 1.8.0 with the
official `es_ES-davefx-medium` and `en_US-lessac-medium` voices, synthesised in
a dedicated venv and played with `pw-play`. Deepgram Aura-2 via Cloudflare was
validated earlier and remains an explicit fallback.

## 2. Decisions (locked 2026-11-18)

| Topic | Decision |
|---|---|
| STT provider | **Whisper local (`base`, int8)** como default, sin credenciales; Vosk en Docker y Cloudflare/Groq como opciones explícitas en `rules.toml` |
| Language | Spanish default (`language="es"`); multilingual via tool argument |
| Capture | `pw-record --rate 16000 --channels 1 --format s16` |
| Push-to-talk | `SUPER+ALT+SHIFT+V` press -> start, release -> stop (`{ release = true }`) |
| Delivery | kitty Wayland PTY master, automatic fallback to `wl-copy` |
| Agent access | local stdio MCP server `voice`: `listen`, `transcribe`, `last`, `languages`, `speak` |
| Fallback | `/voice` command injects `last.txt` through a shell block |
| TTS | **Piper local `1.8.0`** (WAV via `pw-play`, sin cupo) como default; `@cf/deepgram/aura-2-es` / `-en` (MP3, `$0.03/1k chars`) como fallback |
| Secret | `~/.config/voice-bridge/{cf_token,cf_account,key}` (0600) or env; never in `rules.toml` or logs |
| Limits | Whisper `base`: ~438 MB RAM medidos, sin cupo; Vosk: modelo pequeño ~50 MB, ~300 MB RAM por llamada; Cloudflare: Worker AI free allocation; Groq: 20 RPM, 7.2K audio-seconds/hour, 28.8K/day, 25 MB/upload |

Groq was the original provider, but its signup rejects `hotmail.com` domains
(`signup_blocked`, including GitHub OAuth), so Cloudflare became the default
on 2026-11-19. Cloudflare's quota was later exhausted by repeated STT/TTS calls
(`429 Too Many Requests`), so on 2026-11-19 the default changed to a **local
Vosk container**: ~39 MB model, ~300 MB RAM, one-shot execution, no egress.
Accuracy on real speech was poor; after the evaluation in section 10.1 the
default changed on 2026-11-20 to **local Whisper `base`** (section 11).

## 3. Architecture

```
key down ─→ pw-record (16 kHz mono) ─→ capture.wav
key up   ─→ Whisper venv (local) ─→ last.txt + last.json ─→ PTY / clipboard ─→ OpenCode
                                  └─→ MCP voice_last / voice_listen ─→ agent context
```

`~/.local/state/voice-bridge/` holds the WAV, recorder pid, log and last result.
`rules.toml` holds non-secret defaults. No daemon, no socket, no port, except
the one session-scoped wake listener approved in RULES.md 8: `voicectl
wake-start` / `wake-stop` run `wake_listener.py` for the current session only.
It reads `pw-record - -a` raw PCM, groups utterances by energy, detects with the
same local Whisper worker using `initial_prompt`/`hotwords`, then calls
`voicectl wake-dictate`: local Piper confirmation, recording until silence with
a 30 s hard cap, Whisper transcription and the normal PTY/clipboard delivery.
No socket, no network, no PID file outside the state directory. PTT and
`Ctrl+Alt+V` are unchanged.

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

Physical push-to-talk was validated on 2026-11-19: a 19,05 s dictation produced
a full transcript, wrote `last.json`, and left no `pw-record` running. Release
`V` before the modifiers: Hyprland only fires the `{ release = true }` bind when
the modifier state is unchanged on key-up.

## 6. Risks and rollback

- The PTY backend assumes the focused window is kitty; otherwise clipboard is used.
- Audio leaves the machine; keep the key out of configs and logs.
- 429 responses include `retry-after`; the CLI surfaces it in the error.
- Rollback: disable `mcp.servers.voice`, remove the two binds, keep the state
  directory for inspection. Do not touch TimeShift or system configuration.

## 7. TUI plugin iteration (2026-11-19)

`plugin/tui.js` is a local CLI-only plugin registered in `cli.json`. `Ctrl+Alt+V`
toggles dictation: first press calls `voicectl.py start`, second press calls
`stop`, copies the transcript with `wl-copy`, dispatches `prompt.paste` and
speaks "Entendido" through the configured TTS. It forces
`VOICE_DELIVER_BACKEND=none` so the Python CLI does not type into the kitty PTY.

The keystroke no longer depends on the Hyprland composer bind or on which window
has focus. The Hyprland `SUPER+ALT+SHIFT+V` path stays available as fallback.

Per-user playback preferences live in `[voice]` of `rules.toml`: `speaker`
(Deepgram Aura-2 voice) and `rate` (0.5–2.0, applied with `ffmpeg atempo`).
`VOICE_DELIVER_BACKEND` overrides the configured delivery backend for callers
that own the composer path.

Validation: 22/22 offline tests, `node --check` on the plugin. The toggle was
exercised end-to-end inside an isolated TUI via a pseudo-terminal: the plugin
reported `setup`, the first `Ctrl+Alt+V` created `recording.pid`, the second
stopped it and produced a real Cloudflare Whisper transcript, `wl-copy` received
that transcript and `reply.mp3` was regenerated by the TTS step. Setup writes
`~/.local/state/voice-bridge/plugin-load.json` as a load marker and each toggle
step is appended to `plugin-debug.log` in the same state directory. The
currently open TUI must run `/reload` (or be reopened) to pick up the plugin
registration.

Final validation (2026-11-19): the `wl-copy` handoff was changed from `close` to
`exit`, with a watchdog that clears `busy` after 120 s. A three-press PTY run
confirmed `setup -> start -> stop -> copy -> paste(true) -> finally -> start`
with no stuck state, transcript and clipboard matching, and 22/22 offline tests
still passing. Spoken replies use the same Deepgram Aura-2 path through the
`voice_speak` tool; the `aquila` speaker is Spanish-only (English returns HTTP
400), so spoken replies are Spanish by default.

After pasting, the plugin dispatches `input.submit` (the composer's Return
binding) so a user who cannot see the keyboard does not have to press Enter.
`prompt.submit` exists in the keymap but is a no-op for the active composer, so
`input.submit` is preferred. Verified against the API: the transcript appears
as a real `user` message in the session. The confirmation spoken afterwards is
"Entendido, mensaje enviado"; on failure the bridge says the text is in the
clipboard instead. `AUTO_SUBMIT` in `plugin/tui.js` can disable this behavior.

## 8. Bilingual operation (es / en)

`[stt].language = "auto"` lets local Whisper detect the spoken language;
Cloudflare/Groq are only used when explicitly configured.
`[voice].language` follows the same rule: `auto` detects from the reply text, or
it can be forced to `es`/`en`. TTS selects the voice per language:

| Language | Piper voice (default) | Cloudflare fallback | Speaker |
| --- | --- | --- | --- |
| `es` | `es_ES-davefx-medium` | `@cf/deepgram/aura-2-es` | `aquila` |
| `en` | `en_US-lessac-medium` | `@cf/deepgram/aura-2-en` | `asteria` |

The `voice_speak` MCP tool accepts `language: "es" | "en"`; callers should pass
the language of the message being answered. English with the Spanish-only
`aquila` voice returns HTTP 400, so per-language speakers are required.
Values are in `rules.toml` under `[tts]` and `[voice]`. Python module or rule
changes need `/reload` so the MCP server re-imports `voicectl.py`.

## 9. Rate-limit resilience (2026-11-19)

Cloudflare Workers AI can answer `429 Too Many Requests` under burst usage.
`http_post()` in `voicectl.py` now retries STT and TTS requests on `429`,
transient `5xx` and network errors with exponential backoff, honouring the
provider's `Retry-After` header (capped). Configure it in `rules.toml`:

```toml
[api]
retry_attempts = 3        # retries after the first attempt
retry_base_seconds = 2    # 2s, 4s, 8s...
retry_max_seconds = 8     # cap per wait, also caps Retry-After
```

If all retries fail, the plugin shows a plain-Spanish toast ("Cloudflare está
saturado; espera unos segundos y pulsa de nuevo") instead of the raw HTTP
error. The WAV remains in `~/.local/state/voice-bridge/capture.wav`, so a failed
transcription can be retried with `voicectl.py transcribe <file>` once the
quota window resets, or with a local provider (Whisper section 11, Vosk section
10), which has no quota at all. Offline coverage: 3 new tests in `tests/smoke.py`
(27 at that point; 35 after section 10, 42 after section 11 and 47 after
section 12).

## 10. Local Vosk STT (2026-11-19)

Decision: replace the quota-limited cloud path with a one-shot local container.

| Aspect | Value |
|---|---|
| Contract | `capture.wav` mounted `:ro` → `docker run --rm --network none` → JSON on stdout |
| Host dependency | Docker only; zero third-party Python packages on the host |
| Image | `python:3.12-slim` + pinned `vosk==0.3.45` + Spanish/English small model |
| Models | `vosk-model-small-es-0.42` (39 MB), `vosk-model-small-en-us-0.15` (40 MB) |
| RAM | ~300 MB while the container runs; nothing resident afterwards |
| Latency | end of speech + ~1–2 s container start + decode |
| Languages | `auto` captures with the Spanish image and reports es/en heuristically; `es`/`en` selectable |
| Data-root | `/home/dev/ia_local/docker_data_root` (verified); `docker/build.sh` refuses any root outside `/home` |
| Credentials | none |

Source: <https://alphacephei.com/vosk/> and <https://alphacephei.com/vosk/models>
(consulted 2026-11-19). The exact publication date of model `0.42` is **not
verified**; `0.42` is a version, not a date. The Python binding is pinned to
`vosk==0.3.45`, the newest wheel available for Python 3.12 on PyPI
(verified with `pip index versions vosk` on 2026-11-19).

`rules.toml`:

```toml
[stt]
provider = "vosk"

[stt.providers.vosk]
image = "voice-bridge-vosk-es:0.42"
image_en = "voice-bridge-vosk-en:0.15"
network = "none"
```

`build.sh` builds both images with `--build-arg`; no secret or real audio is
baked into them. Eight new offline tests cover the contract, both images,
language detection, missing Docker, container failure, invalid JSON and timeout
(35 total). GHCR publication is planned but not executed.

### 10.1 Accuracy limits and the rejected lgraph upgrade (2026-11-19)

Official WER figures from <https://alphacephei.com/vosk/models> (consulted
2026-11-19):

| Model | Size | WER |
|---|---|---|
| `vosk-model-small-es-0.42` | 39 MB | 16.02 % (cv), 16.72 % (mtedx), 11.21 % (mls) |
| `vosk-model-es-0.42` | 1.4 GB | 7.50 % (cv), 10.05 % (mtedx), 5.84 % (mls) |
| `vosk-model-small-en-us-0.15` | 40 MB | 9.85 % (librispeech), 10.38 % (tedlium) |
| `vosk-model-en-us-0.22-lgraph` | 128 MB | 7.82 % (librispeech), 8.20 % (tedlium) |

Both shipped models stay small. `vosk-model-en-us-0.22-lgraph` was built and
measured on the real 24 s WAV: **3 m 54.8 s** of decode (≈9.8× real time) on
this AMD A10-7300. The 60 s timeout was exceeded, so the WER gain from 9.85 %
to 7.82 % is not usable for dictation here and the change was reverted. The
1.4 GB Spanish model was also built and measured on 2026-11-20: **4.24 GB peak
RSS** and **118 s** of decode for the same 24 s WAV (≈4.9× real time, 2 m 15 s
wall clock) on this 6.7 GiB box. Alpha Cephei warns big models may need up to
16 GB. It was rejected and the 4.17 GB test image was removed. Both shipped
images remain the small ones.

Custom phrases are **not** a safe fix for the small Spanish model. Measured on
2026-11-19 with `vosk==0.3.45` and the real 24 s `capture.wav`:

- `Model.vosk_model_find_word()` returns `-1` for `OpenCode`, `Hyprland`,
  `Waydroid`, `PipeWire`, `Questline`, `Vosk` → those tokens are absent from the
  model vocabulary and `SetGrammar` ignores them with a warning.
- Passing a short grammar restricts decoding to that list: the same WAV
  degraded from full dictation to `peticiones peticiones`.

The small model ships no `words.txt`, so a full-vocabulary grammar cannot be
reconstructed locally. No grammar is passed by default; phrase boosting would
need either the big model or offline LM adaptation with Kaldi/OpenGRM, which
is not installed and is outside the approved scope.

Source for the API behaviour: official
[`test_words.py`](https://github.com/alphacep/vosk-api/blob/master/python/example/test_words.py)
and <https://alphacephei.com/vosk/adaptation> (consulted 2026-11-19).

## 11. Local Whisper STT — new default (2026-11-20)

After section 10.1 showed that Vosk small misrecognised ordinary dictation and
both larger Vosk models were unusable on this 6.7 GiB AMD A10-7300 box, the user
approved evaluating local `faster-whisper`, then chose the **`base`** model for
integration. Vosk remains available with `[stt].provider = "vosk"`.

| Aspect | Value |
|---|---|
| Runtime | `faster-whisper==1.2.1` + `av==14.4.0` in `~/.local/state/voice-bridge/whisper/venv` |
| Model | `base`, CPU `int8`, 4 threads, beam 5, VAD on |
| Host dependency | None beyond Python 3.13; the worker is a subprocess in its own venv |
| RAM | ~438 MB measured in this box |
| Latency | ~24 s decode for the 24.23 s real WAV; first load ~68 s including download, warm load ~4.6 s |
| Cache | `~/.local/state/voice-bridge/whisper/hf`; first run downloads, later runs need no network |
| Credentials | none |
| Tests | 7 new offline tests → 42 total |

Sources: official
[`faster-whisper` README](https://github.com/SYSTRAN/faster-whisper/blob/master/README.md)
and [`requirements.txt`](https://github.com/SYSTRAN/faster-whisper/blob/master/requirements.txt),
plus the model config returning HTTP 200 at
<https://huggingface.co/Systran/faster-whisper-small/resolve/main/config.json>
(consulted 2026-11-20). `av==19.0.2` failed here with
`TypeError: open() got an unexpected keyword argument 'metadata_errors'`;
`av==14.4.0` was verified working and is pinned by `tools/install-whisper.sh`.

Measured on the same real 24.23 s Spanish WAV (16 kHz, mono s16):

- Vosk small: `esta más profundo sistema que simplemente aquí con open comunicarse mediante vos y los con los nuevo la nueva tecnología...`
- Whisper `base`: `estamos probando en los sistemas que es implementando aquí con OpenCode para comunicarse mediante voz y en la nueva tecnología que estamos probando...`
- Whisper `small`: slightly better wording (`un nuevo sistema`, `limitaciones`)
  but ~46 s decode and ~653 MB RAM, so it was not chosen.
- Beam 1 with `base` took ~28 s but degraded the text, so beam 5 was kept.
- On a second real 13.95 s dictation, `base` produced `ahora estamos probando
  otra vez OpenCop por medio de voz, comando de voz de whisper debido a los
  fallos con voz.` The user confirmed the result was better than Vosk and
  accepted `base` despite residual errors such as `OpenCop` for `OpenCode`.

`rules.toml` now sets `[stt].provider = "whisper"` and
`[stt.providers.whisper]` with `model = "base"`, `compute_type = "int8"`,
`cpu_threads = 4`, `beam_size = 5`, `vad_filter = true`, `python` and `hf_home`
paths. `whisper_transcribe.py` prints only a JSON object on stdout;
`voicectl._transcribe_whisper()` builds the env, enforces the timeout and keeps
the host dependency-free. Nothing from the venv or the HF cache lives in the
repo. GHCR publication is still planned, not executed. The user validated the
dictation on 2026-11-20 and accepted `base`; no commit or push has been made yet.

## 12. Local Piper TTS — new default (2026-11-20)

Cloudflare's quota made spoken replies unreliable, so the user chose Piper as
the local TTS path before any commit/push.

| Aspect | Value |
|---|---|
| Runtime | `piper-tts==1.8.0` in `~/.local/state/voice-bridge/piper/venv` |
| Voices | `es_ES-davefx-medium` and `en_US-lessac-medium`, 63 MB each, under `.../piper/models` |
| Contract | `python -m piper --data-dir DIR -m VOICE -f reply.wav -- TEXT`, then `pw-play` |
| Host dependency | None; espeak-ng is embedded in Piper, so no `apt` install is needed |
| Credentials | none |
| Fallback | `[tts].provider = "cloudflare"` keeps Aura-2 MP3 via `pw-play` |
| Tests | 5 new offline tests → 47 total |

Sources consulted 2026-11-20: official
[`piper1-gpl` README](https://github.com/OHF-Voice/piper1-gpl),
[CLI docs](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md),
[voices docs](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md),
the [PyPI JSON metadata](https://pypi.org/pypi/piper-tts/json) (version 1.8.0,
`onnxruntime<2`, Python ≥3.9), the official
[`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices) tree and
the `v1.0.0` model/config URLs for both voices (HTTP 200, 63.2 MB each). Voice
model cards were checked: `davefx` uses a CC0 dataset; `lessac` links to its
Blizzard Challenge license. `rhasspy/piper` is archived; this setup uses the
maintained `OHF-Voice/piper1-gpl` package.

`rules.toml` now sets `[tts].provider = "piper"` with
`[tts.providers.piper]` holding the venv path, voice directory and voice names.
`speak()` dispatches to `_speak_piper()` or `_speak_cloudflare()`; both share
`_speak_finish()` for the optional `ffmpeg atempo` rate change and playback.
`status()` reports `tts_provider` and `tts_model`.

Real verification on this box: Spanish synthesis of
`Hola, esta es la respuesta hablada con Piper local.` produced a 131 KB WAV in
~10.5 s; `python3 voicectl.py speak 'Listo, Piper local funciona.'` returned
`"played": true` through `pw-play`. No audio or model files entered the repo.
GHCR publication remains planned, not executed. No commit or push has been made.
