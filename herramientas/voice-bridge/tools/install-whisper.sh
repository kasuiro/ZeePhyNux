#!/usr/bin/env bash
# Install the local Whisper STT runtime outside the repo, under ~/.local/state.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
state="${VOICE_BRIDGE_WHISPER_DIR:-$HOME/.local/state/voice-bridge/whisper}"
venv="$state/venv"
python_bin="${1:-python3}"

if [ ! -x "$venv/bin/python" ]; then
    mkdir -p "$state"
    "$python_bin" -m venv "$venv"
fi
"$venv/bin/python" -m pip install --disable-pip-version-check \
    "faster-whisper==1.2.1" "av==14.4.0"

# Keep the cache where rules.toml expects it; models download on first use.
mkdir -p "$state/hf"
printf 'Whisper venv ready: %s\n' "$venv"
printf 'Repo unchanged: %s\n' "$root"
