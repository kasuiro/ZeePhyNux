# AGENTS.md — Debian_Hyprland_Look_And_Feel

Desktop-work repository, not an application: four independent tools plus specs and
generated deliverables. There is no root README, manifest, build/lint/CI or
`opencode.json`; the subsystem READMEs and `docs/subsystem/` are the sources of
truth. Machine-wide rules live in `~/.config/opencode/AGENTS.md` — do not copy
them here.

## Map

- `herramientas/questline/` — `ql`, stdlib-only CLI; event log is the only truth.
  Spec `docs/subsystem/SPEC.md`, invariants `RULES.md`, backlog `BACKLOG.md`.
- `herramientas/voice-bridge/` — local Whisper STT + Piper TTS, stdio MCP, kitty
  TUI plugin. Details in `docs/subsystem/VOICE.md`.
- `herramientas/power-modes/` — root helper for CPU/iGPU, installed into
  `/usr/local/bin` and `/etc/sudoers.d`.
- `herramientas/gallery-gen/` — remote Cloudflare FLUX image generation; no
  local model.
- `.opencode/skills/document-workflow/` — DOCX/PDF/CSV/XLSX skill; `entregables/`
  holds outputs plus `.provenance.json`.
- `~/Documentos/Vault/` (checklist, notes) and `.obsidian/` are outside git.

## Verification

```sh
cd herramientas/questline && python3 tests/smoke.py      # isolated temp vault/state
cd herramientas/voice-bridge && python3 tests/smoke.py   # offline: no mic, no network
cd herramientas/voice-bridge && python3 voicectl.py status
node --check --input-type=module < herramientas/voice-bridge/plugin/tui.js
cd herramientas/power-modes && bash -n mode-power.sh && visudo -c -f 99-mode-power.sudoers
```

- Questline tests override `QL_VAULT`, `QL_HOME`, `QL_NOTIFY_LOG`, `QL_NO_SPLASH`
  and `QL_EMBLEM_OUT`; never point them at the real vault.
- Test counts in prose drift (voice README says 47 in one place and 62 in
  another; `VOICE.md` says 19; the runner currently has 62). Trust the runner.
- No scoring rule without a test; every point rule is covered by the smoke suite.

## Questline

- `Vault/Questline/events/<device>.tsv` is append-only; `state.json` is a
  disposable cache (`ql rebuild`). Corrections are new events, never edits.
- `ql scan` and `ql tasks` do not write. Only `ql scan --write-ids` appends a
  `^ql-…` block id once, after copying the note to `id-backups/`. The first
  `ql sync` is a baseline and awards nothing.
- No daemon or network in the core: no penalties, 40 FRG/day/mode and 4 h/session
  caps, roles differ only by affinity (`rules.toml`).
- The HUD is a GTK3 layer surface: hide/show the inner `Gtk.Box`, never
  `win.hide()`/`show_all()` — hiding the toplevel destroys the layer while the
  process stays alive. `ql-hud` chooses its monitor once at startup.
- Stamps are pure functions of the log; `ql claim <id>` is the only renderer and
  is idempotent. Generated cards live in `Vault/Questline/gallery/`.

## Voice-bridge

- Defaults are local: `[stt].provider = whisper` (`base`, int8, 4 threads) and
  `[tts].provider = piper` (`1.8.0`). Vosk, Cloudflare and Groq are opt-ins.
- venvs, models and state live under `~/.local/state/voice-bridge/`, never in
  the repo. `faster-whisper==1.2.1` needs `av==14.4.0` (`av 19` fails here).
- Credentials only via env or 0600 files in `~/.config/voice-bridge/`; never in
  `rules.toml`, logs or the repo.
- `wake-start`/`wake-stop` own the single session listener approved in
  `RULES.md` 8; `wake-dictate` ends on silence with a 30 s hard cap. Detection
  uses `NoiseAwareSplitter` (`noise_factor = 2.0`): a fixed 300 RMS threshold
  fails against this room's ~480 RMS noise floor.

## System and external services

- The agent never runs `sudo`, installs packages or edits `/etc`, systemd or
  the kernel: give the user exact commands from `power-modes/README.md`.
- `sudo -n mode-power status` intentionally asks for a password (`status` is
  excluded from sudoers). iGPU writes return EINVAL on this A10-7300 — expected;
  the CPU profile still applies.
- `GalleryGen.py --check` validates the token without spending neurons. FLUX
  returns fixed 1024×1024 and rejects `width`/`height`. Tokens are fish
  universal vars; from bash use `fish -c './GalleryGen.py --check'`. Prompts
  describe the subject, never named copyrighted characters.

## Deliverables

- Use `.opencode/skills/document-workflow`: Markdown source immutable (verify
  SHA-256), output under `<project>/entregables/` with `.provenance.json`, no
  overwrite without confirmation, no LibreOffice or system packages.

## Git

- Stage explicit paths only; unrelated user work may be in the working tree.
  Run `git diff --check` before committing.
