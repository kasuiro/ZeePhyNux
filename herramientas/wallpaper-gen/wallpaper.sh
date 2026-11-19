#!/usr/bin/env bash
# Convierte un still en el tipo de video que usa el picker: 1366x768, 30 fps,
# 15 s, h264 yuv420p. El paneo es un zoom lento del 6 % (ken burns).
#
# Uso:
#   wallpaper.sh animar <imagen> <salida.mp4> [segundos=15]
#   wallpaper.sh poster <video.mp4> <salida.png> [segundo=2]
#
# El encode va con prioridad minima (nice 19 + ionice clase 3): es la unica
# parte de este flujo que consume CPU.
set -euo pipefail

PROG=${0##*/}

uso() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
}

[ $# -ge 3 ] || uso
accion=$1; entrada=$2; salida=$3; extra=${4:-}
[ -f "$entrada" ] || { echo "$PROG: no existe $entrada" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "$PROG: falta ffmpeg" >&2; exit 1; }

baja_prioridad() {
  if command -v ionice >/dev/null; then
    nice -n 19 ionice -c 3 "$@"
  else
    nice -n 19 "$@"
  fi
}

case $accion in
  animar)
    dur=${extra:-15}
    fps=30
    frames=$((dur * fps))
    # La copia 2x con 'neighbor' mantiene los bordes duros del pixel art; el
    # zoompan luego recorta una ventana 16:9 y la escala a 1366x768.
    baja_prioridad ffmpeg -hide_banner -loglevel error -y \
      -loop 1 -i "$entrada" -t "$dur" -r "$fps" \
      -vf "scale=2048:2048:flags=neighbor,zoompan=z='1+0.06*on/$frames':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1366x768:fps=$fps,format=yuv420p" \
      -c:v libx264 -preset veryfast -crf 28 -maxrate 900k -bufsize 1800k \
      -pix_fmt yuv420p -color_range tv -movflags +faststart "$salida"
    echo "listo: $salida ($(du -h "$salida" | cut -f1))"
    ;;
  poster)
    seg=${extra:-2}
    baja_prioridad ffmpeg -hide_banner -loglevel error -y \
      -ss "$seg" -i "$entrada" -frames:v 1 \
      -vf "scale=1366:768:flags=lanczos" "$salida"
    echo "listo: $salida"
    ;;
  *)
    uso
    ;;
esac
