#!/usr/bin/env bash
# Install local Piper TTS outside the repo, under ~/.local/state/voice-bridge.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
state="${VOICE_BRIDGE_PIPER_DIR:-$HOME/.local/state/voice-bridge/piper}"
venv="$state/venv"
python_bin="${1:-python3}"

if [ ! -x "$venv/bin/python" ]; then
    mkdir -p "$state"
    "$python_bin" -m venv "$venv"
fi
"$venv/bin/python" -m pip install --disable-pip-version-check \
    "piper-tts==1.8.0"
"$venv/bin/python" -m piper.download_voices --data-dir "$state/models" \
    es_ES-davefx-medium en_US-lessac-medium

printf 'Piper venv ready: %s\n' "$venv"
printf 'Voices ready: %s\n' "$state/models"
printf 'Repo unchanged: %s\n' "$root"
