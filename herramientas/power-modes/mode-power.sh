#!/usr/bin/env bash
# ============================================================================
# mode-power — perfil energético mínimo para los 7 modos de gamemode
# Máquina: AMD A10-7300 (4C, acpi-cpufreq 1.10–1.90 GHz) + amdgpu (Kaveri)
# Sistema: Debian 13 trixie, kernel 6.12, systemd 257
#
# ÍNDICE DE BLOQUES
#   [0] Contrato de uso y códigos de salida
#   [1] Rutas y valores permitidos ................ cpufreq + amdgpu sysfs
#   [2] Guard de privilegios (solo escrituras) .... sudoers(5)
#   [3] Validación de argumentos (allowlist)
#   [4] CPU: governor + límites de frecuencia ..... docs.kernel.org cpufreq
#   [5] iGPU: DPM force level ..................... docs.kernel.org amdgpu
#   [6] Tabla de perfiles
#   [6b] Estado previo: guardar y restaurar (sin perfiles inventados)
#   [7] Lectura de estado (no requiere root)
#   [8] main
#
# FUENTES OFICIALES (verificadas una a una, no de memoria)
#   F1 https://docs.kernel.org/admin-guide/pm/cpufreq.html#generic-scaling-governors
#   F2 https://docs.kernel.org/admin-guide/pm/cpufreq.html#performance
#   F3 https://docs.kernel.org/admin-guide/pm/cpufreq.html#schedutil
#   F4 https://docs.kernel.org/gpu/amdgpu/thermal.html#power-dpm-force-performance-level
#   F5 man 1 cpupower-frequency-set   (paquete linux-cpupower, instalado)
#   F6 man 5 sudoers                  (sintaxis NOPASSWD)
#   F7 https://docs.kernel.org/admin-guide/pm/amd-pstate.html  (NO aplica: ver README)
# ============================================================================

set -euo pipefail
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

# ---------------------------------------------------------------------------
# [0] CONTRATO
#   mode-power status          lectura, sin root
#   mode-power perf            escritura, requiere root
#   mode-power balanced        escritura, requiere root
#   mode-power eco             escritura, requiere root
#   mode-power restore         vuelve al estado previo a la primera escritura
#   Salidas: 0 ok | 1 error de entorno | 2 uso incorrecto | 3 falta root
#   No acepta ningún otro argumento. No interpreta rutas del usuario.
# ---------------------------------------------------------------------------
readonly PROG=${0##*/}

# ---------------------------------------------------------------------------
# [1] RUTAS Y VALORES PERMITIDOS
# F5: cpupower opera sobre /sys/devices/system/cpu/cpufreq/policy*
# F4: el nivel DPM se escribe como texto en un único sysfs del device DRM
# ---------------------------------------------------------------------------
readonly CPU_BASE=/sys/devices/system/cpu
readonly DPM_FILE=/sys/class/drm/card0/device/power_dpm_force_performance_level
readonly GOV_FILE=${CPU_BASE}/cpu0/cpufreq/scaling_governor

# F4 acepta: auto low high manual profile_standard profile_min_sclk
#            profile_min_mclk profile_peak. Solo usamos los tres primeros.
readonly DPM_OK=(auto low high)
# F1/F3: esta máquina expone exactamente estos dos gobernadores.
readonly GOV_OK=(performance schedutil)
# F5: pasos reales de esta CPU (cpupower frequency-info).
readonly FREQ_MIN=1.10GHz
readonly FREQ_MAX=1.90GHz
# Estado previo a la primera escritura, para poder deshacer sin adivinar.
readonly STATE_DIR=/var/lib/mode-power
readonly STATE_FILE=${STATE_DIR}/prev.env

# ---------------------------------------------------------------------------
# [2] GUARD DE PRIVILEGIOS
#   Leer (status) no necesita privilegios. Escribir sí: el dueño de
#   scaling_governor y del sysfs DPM es root y no es delegable por sysfs.
# F6: la regla NOPASSWD concede ejecución como root de ESTA ruta y nada más.
# ---------------------------------------------------------------------------
necesita_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "$PROG: '$1' requiere root (usa: sudo $PROG $1)" >&2
    exit 3
  fi
}

# ---------------------------------------------------------------------------
# [3] VALIDACIÓN DE ARGUMENTOS
#   Allowlist cerrada: cualquier otra cosa sale con código 2 y no toca nada.
# ---------------------------------------------------------------------------
validar_arg() {
  case "${1:-}" in
    status|perf|balanced|eco|restore) return 0 ;;
    "")
      echo "uso: $PROG {status|perf|balanced|eco|restore}" >&2
      exit 2 ;;
    *)
      echo "$PROG: argumento no permitido: '$1'" >&2
      echo "uso: $PROG {status|perf|balanced|eco|restore}" >&2
      exit 2 ;;
  esac
}

# ---------------------------------------------------------------------------
# [4] CPU: GOBERNADOR + LÍMITES DE FRECUENCIA
# F2: 'performance' fija el límite superior dentro del rango de la policy.
# F3: 'schedutil' usa los datos del scheduler; permite bajar de 1.90 GHz.
# F5: cpupower frequency-set -g <gov> -d <min> -u <max>
#   Se comprueba antes que el gobernador exista en la lista del kernel para
#   no dejar la policy en un estado inventado.
# ---------------------------------------------------------------------------
cpu_set() {
  local gov=$1 fmin=$2 fmax=$3 disponible g

  disponible=$(cat "${CPU_BASE}/cpu0/cpufreq/scaling_available_governors")
  for g in "${GOV_OK[@]}"; do
    if [ "$g" = "$gov" ]; then
      case " $disponible " in
        *" $gov "*) ;;
        *) echo "$PROG: el kernel no ofrece el gobernador '$gov' (ofrece: $disponible)" >&2; return 1 ;;
      esac
    fi
  done

  # Idempotencia: si ya está así, no se escribe.
  if [ "$(cat "$GOV_FILE")" = "$gov" ]; then
    :
  else
    cpupower frequency-set -g "$gov" >/dev/null
  fi
  cpupower frequency-set -d "$fmin" -u "$fmax" >/dev/null
}

# ---------------------------------------------------------------------------
# [5] iGPU: power_dpm_force_performance_level
# F4: 'high' fuerza el estado de mayor consumo, 'low' el menor, 'auto' deja
#     que el driver decida. 'manual' se evita a propósito: exige máscaras en
#     pp_dpm_* y aquí pp_dpm_sclk viene vacío (Kaveri), así que no aporta.
# ---------------------------------------------------------------------------
igpu_set() {
  local nivel=$1 v ok=0
  [ -w "$DPM_FILE" ] || { echo "$PROG: no escribible: $DPM_FILE" >&2; return 0; }
  for v in "${DPM_OK[@]}"; do [ "$v" = "$nivel" ] && ok=1; done
  [ "$ok" -eq 1 ] || { echo "$PROG: nivel DPM no permitido: '$nivel'" >&2; return 0; }
  if [ "$(cat "$DPM_FILE")" = "$nivel" ]; then
    return 0
  fi
  # En este ASIC (Kaveri) el driver puede rechazar el cambio con EINVAL y
  # pp_dpm_sclk viene vacío. Se avisa y se sigue: el perfil de CPU vale igual.
  if ! printf '%s\n' "$nivel" > "$DPM_FILE" 2>/dev/null; then
    echo "$PROG: la iGPU no acepta el nivel '$nivel' (sin soporte en este hardware); se ignora" >&2
  fi
  return 0
}

# ---------------------------------------------------------------------------
# [6] TABLA DE PERFILES
#   perf      : máxima frecuencia sostenida + iGPU a tope   (Devmode, GameDev, 3D)
#   balanced  : schedutil con techo completo, iGPU auto     (AudioVisual, Planing)
#   eco       : schedutil con techo 1.50 GHz, iGPU low      (Readmode, Writemode)
#   Ningún perfil toca: cgroups, prioridades de proceso ni el scheduler.
# ---------------------------------------------------------------------------
aplicar() {
  guardar_prev
  case "$1" in
    perf)     cpu_set performance "$FREQ_MAX" "$FREQ_MAX"; igpu_set high ;;
    balanced) cpu_set schedutil   "$FREQ_MIN" "$FREQ_MAX"; igpu_set auto ;;
    eco)      cpu_set schedutil   "$FREQ_MIN" "1.50GHz";   igpu_set low  ;;
  esac
  estado
}

# ---------------------------------------------------------------------------
# [6b] ESTADO PREVIO
#   Se guarda UNA vez, antes de la primera escritura. Así 'restore' devuelve
#   exactamente lo que había, sin suponer que el valor de fábrica es el correcto.
#   El fichero vive en /var/lib (root) y no contiene nada sensible.
# ---------------------------------------------------------------------------
guardar_prev() {
  [ -f "$STATE_FILE" ] && return 0
  mkdir -p "$STATE_DIR"
  chmod 0755 "$STATE_DIR"
  {
    printf 'gov=%s\n' "$(cat "$GOV_FILE")"
    printf 'min=%s\n' "$(cat "${CPU_BASE}/cpu0/cpufreq/scaling_min_freq")"
    printf 'max=%s\n' "$(cat "${CPU_BASE}/cpu0/cpufreq/scaling_max_freq")"
    printf 'dpm=%s\n' "$(cat "$DPM_FILE")"
  } > "$STATE_FILE"
  chmod 0644 "$STATE_FILE"
}

restaurar() {
  if [ ! -f "$STATE_FILE" ]; then
    echo "no hay estado previo guardado (nada que restaurar)"
    estado
    return 0
  fi
  local gov min max dpm v ok
  # shellcheck disable=SC1090
  . "$STATE_FILE"
  ok=0; for v in "${GOV_OK[@]}"; do [ "$v" = "${gov:-}" ] && ok=1; done
  [ "$ok" -eq 1 ] || { echo "estado previo inválido (gov='${gov:-}')" >&2; return 1; }
  ok=0; for v in "${DPM_OK[@]}"; do [ "$v" = "${dpm:-}" ] && ok=1; done
  [ "$ok" -eq 1 ] || dpm=auto
  cpupower frequency-set -g "$gov" >/dev/null
  cpupower frequency-set -d "$((min / 1000))MHz" -u "$((max / 1000))MHz" >/dev/null
  printf '%s\n' "$dpm" > "$DPM_FILE"
  rm -f "$STATE_FILE"
  estado
}

# ---------------------------------------------------------------------------
# [7] ESTADO (lectura pura; funciona como usuario)
# ---------------------------------------------------------------------------
estado() {
  local gov dpm fmin fmax
  gov=$(cat "$GOV_FILE" 2>/dev/null || echo "?")
  dpm=$(cat "$DPM_FILE" 2>/dev/null || echo "?")
  fmin=$(cat "${CPU_BASE}/cpu0/cpufreq/scaling_min_freq" 2>/dev/null || echo 0)
  fmax=$(cat "${CPU_BASE}/cpu0/cpufreq/scaling_max_freq" 2>/dev/null || echo 0)
  printf 'governor=%s  min=%sMHz  max=%sMHz  igpu_dpm=%s\n' \
    "$gov" "$((fmin / 1000))" "$((fmax / 1000))" "$dpm"
}

# ---------------------------------------------------------------------------
# [8] MAIN
# ---------------------------------------------------------------------------
main() {
  validar_arg "${1:-}"
  case "$1" in
    status) estado ;;
    restore) necesita_root "$1"; restaurar ;;
    *) necesita_root "$1"; aplicar "$1" ;;
  esac
}

main "$@"
