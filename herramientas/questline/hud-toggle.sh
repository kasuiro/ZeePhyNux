#!/usr/bin/env bash
# Show / hide the Questline HUD. Starts it if it is not running.
# Bidirectional control is a SIGUSR1 to the pid in $XDG_RUNTIME_DIR; no daemon
# and no polling: the HUD is already a resident card by design.
set -uo pipefail

HUD="${QL_HUD_BIN:-$HOME/.local/bin/ql-hud}"
RUNTIME="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
PID_FILE="$RUNTIME/questline-hud.pid"

if [ -r "$PID_FILE" ]; then
  read -r pid < "$PID_FILE" || pid=""
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    kill -USR1 "$pid" && exit 0
  fi
fi

# Not running (or a stale pid): start it detached from this shell.
if [ -x "$HUD" ]; then
  setsid "$HUD" >/dev/null 2>&1 &
fi
