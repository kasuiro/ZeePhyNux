#!/usr/bin/env bash
# Build the local Vosk STT images. Refuses to run if Docker is not rooted in /home.
set -euo pipefail

cd "$(dirname "$0")"

root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
case "$root" in
  /home/*) echo "Docker data-root OK: $root" ;;
  *)
    echo "ABORT: Docker data-root must be under /home (got: ${root:-unknown})." >&2
    echo "Ask the system administrator before changing Docker storage." >&2
    exit 1
    ;;
esac

build() {
  local image="$1" model="$2" url="$3"
  echo "==> $image ($model)"
  docker build \
    --build-arg "VOSK_MODEL=$model" \
    --build-arg "VOSK_MODEL_URL=$url" \
    --label "org.opencontainers.image.source=https://github.com/kasuiro/ZeePhyNux" \
    -t "$image" .
}

build voice-bridge-vosk-es:0.42 vosk-model-small-es-0.42 \
  https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
build voice-bridge-vosk-en:0.15 vosk-model-small-en-us-0.15 \
  https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

echo "Done. Verify with: docker images --format '{{.Repository}}:{{.Tag}}' | grep voice-bridge"
