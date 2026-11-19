# Perfil energético de los 7 modos — helper root mínimo

Motivo: los scripts de gamemode no pueden tocar CPU ni iGPU porque ambos sysfs
son de root. Todo lo demás (pesos de cgroup, prioridades, cuotas) **sí** se hace
sin root y ya está resuelto por otras vías.

Este directorio contiene lo único que exige privilegios, con la documentación
oficial citada bloque por bloque.

---

## 1. Estado real de la máquina (medido, no supuesto)

| Dato | Valor | Comando |
|---|---|---|
| Driver cpufreq | `acpi-cpufreq` | `cpupower frequency-info` |
| Gobernadores disponibles | `performance schedutil` | idem |
| Rango | 1.10 – 1.90 GHz, pasos 1.90/1.80/1.50/1.20/1.10 | idem |
| Política actual | min = max = **1.90 GHz** (clavada arriba) | idem |
| iGPU | `power_dpm_force_performance_level = auto` | `cat /sys/class/drm/card0/device/power_dpm_force_performance_level` |
| `pp_dpm_sclk` | vacío (Kaveri no expone estados por reloj) | idem |
| power-profiles-daemon | activo, perfil `balanced`, pero `PlatformDriver: placeholder` | `powerprofilesctl list` |
| paquete `scx-scheds` | no existe en trixie | `apt-cache search sched-ext` |

Conclusión: **PPD no puede gestionar esta máquina** (sin `platform_profile`), y
el gobernador lleva clavado el máximo desde antes. Ese es el desperdicio real:
no hay margen de ahorro por gobernador, sí por techo de frecuencia.

---

## 2. Por qué NO se usan estas tres vías

| Vía | Por qué no |
|---|---|
| `amd-pstate` | Solo CPUs Zen2+ (Ryzen). El A10-7300 es Kaveri: el driver ni aparece. Doc F7. |
| `scx_lavd` / sched-ext | No hay paquete en Debian 13; compilarlo es un cambio de sistema y consume CPU. |
| `tuned` / `tuned-ppd` | Sustituye a PPD y reescribe gobernadores por su cuenta: dos dueños del mismo sysfs. |

Y una regla de diseño: **el helper no crea estado propio**. No escribe archivos,
no guarda perfiles, no arranca demonios. Aplica y sale.

---

## 3. Qué hace el helper (y qué no)

| Verbo | CPU | iGPU | Root |
|---|---|---|---|
| `status` | lee | lee | no |
| `perf` | `performance`, 1.90/1.90 | `high` | sí |
| `balanced` | `schedutil`, 1.10/1.90 | `auto` | sí |
| `eco` | `schedutil`, 1.10/1.50 | `low` | sí |

`restore` devuelve exactamente lo que había antes de la primera escritura
(lo guarda en `/var/lib/mode-power/prev.env`), así que no supone que el valor de
fábrica sea el correcto.

Mapeo ya enganchado a los modos (`gamemode_toggle.sh`):

| Modo | Perfil |
|---|---|
| Devmode, GameDevmode, 3Dmode | `perf` |
| AudioVisualmode, Planingmode | `balanced` |
| Readmode, Writemode | `eco` |

Al salir de cualquier modo se vuelve a `balanced`. Si el helper no está
instalado o no hay NOPASSWD, el modo funciona igual y lo deja anotado en
`/tmp/gamemode-modo.log`.

No toca: cgroups, `nice`, prioridades de I/O, scheduler de CPU, ni ningún
servicio. Nada que requiera reiniciar sesión.

---

## 4. Fuentes oficiales, una por bloque del script

| Bloque | Fuente | Sección exacta |
|---|---|---|
| [4] CPU | `https://docs.kernel.org/admin-guide/pm/cpufreq.html` | `#generic-scaling-governors`, `#performance`, `#schedutil` |
| [4] escritura | `man 1 cpupower-frequency-set` | opciones `-g`, `-d`, `-u` (paquete `linux-cpupower`, instalado) |
| [5] iGPU | `https://docs.kernel.org/gpu/amdgpu/thermal.html` | `#power-dpm-force-performance-level` (valores `auto/low/high/manual/profile_*`) |
| [2] privilegios | `man 5 sudoers` | `NOPASSWD`, comparación de argumentos |
| [7] no aplica | `https://docs.kernel.org/admin-guide/pm/amd-pstate.html` | requisito Zen2+ |
| sin root | `man 5 systemd.resource-control` | `CPUWeight`, `CPUQuota`, `AllowedCPUs`, `IOWeight` |

Las cinco primeras están verificadas contra el HTML/`man` instalado en esta
máquina, no citadas de memoria.

---

## 5. Instalación (la haces tú; el agente no ejecuta `sudo`)

```bash
cd ~/Documentos/Debian_Hyprland_Look_And_Feel/herramientas/power-modes
bash -n mode-power.sh                      # sintaxis
./mode-power.sh status                      # debe funcionar sin root
sudo install -m 0755 mode-power.sh /usr/local/bin/mode-power
sudo install -m 0440 -o root -g root 99-mode-power.sudoers /etc/sudoers.d/99-mode-power
sudo visudo -c                              # debe decir: parsed OK
```

## 6. Verificación

```bash
mode-power status                 # sin sudo: leer no necesita privilegios
sudo -n mode-power eco            # debe funcionar sin contraseña
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # schedutil
sudo -n mode-power balanced       # vuelve al estado normal
mode-power nope                   # debe salir 2 sin tocar nada
```

`sudo -n mode-power status` **sí** pide contraseña: `status` no está en el
sudoers a propósito, porque no necesita root.

Aviso medido en esta máquina: al escribir el nivel de la iGPU el driver
devuelve `EINVAL` (rc 234) y `pp_dpm_sclk` está vacío, así que **el nivel de la
iGPU no se aplica en este hardware**. El helper lo avisa y sigue; el perfil de
CPU se aplica igual.

## 7. Rollback (una línea)

```bash
sudo rm /etc/sudoers.d/99-mode-power /usr/local/bin/mode-power
```
Sin `rm -rf`, dos rutas exactas. El estado energético se queda como esté;
`mode-power balanced` antes de borrar deja todo en el valor por defecto.

---

## 8. Lo que NO necesita root (ya probado, no hace falta helper)

Delegación de cgroups v2 en la sesión de usuario: funciona y se verificó hoy.

```bash
systemctl --user show app.slice -p CPUWeight      # 100
systemctl --user set-property app.slice CPUWeight=150
systemd-run --user --scope -p CPUQuota=80% -p IOWeight=200 -p AllowedCPUs=0-1 -- true
```

Eso permite dar prioridad a un modo (o quitársela) sin privilegios. Si algún
modo necesita "reservar" CPU, este es el camino, no el helper root.
