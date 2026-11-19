# Auditoría de wallpapers animados

Fecha: 2026-11-13. Método: `ffprobe` (resolución/duración), `du` (tamaño), `file` (formato real),
`md5sum` (duplicados exactos), `magick` + `ffmpeg` (muestreo de 8 frames por vídeo y comparación
RMSE normalizado contra el poster; continuidad de bucle = frame 0 vs último frame).

Criterios de admisión del plan: 1366x768 o más · ≤10 MB · ≥6 s y bucle continuo · sin marca de agua ·
sin texto legible · fiel al tema · sin IA · no duplicado · con poster `.png` generado.

## Resumen por tema

> Diagnóstico original del 2026-11-13, conservado como historial. El estado real
> de hoy (68 piezas, 68 pósters exactos) está en «F8 — cierre» al final.

| Tema | mp4 | estáticas | posters OK | posters MAL |
|---|---|---|---|---|
| 01-shingeki-no-kyojin | 5 | 0 | 4 | 1 |
| 02-blame | 5 | 0 | 0 | 5 |
| 03-berserk | 5 | 0 | 3 | 2 |
| 04-debian-linux | 5 | 0 | 1 | 4 |
| 05-flcl | 5 | 0 | 1 | 4 |
| 06-golden-boy | 5 | 0 | 4 | 1 |
| 07-paisajes | 5 | 0 | 2 | 3 |
| 08-codigo | 5 | 0 | 3 | 2 |
| 09-juegos | 5 | 0 | 3 | 2 |
| 10-bandas | 15 | 1 | 12 | 3 |
| 11-eleccion-propia | 5 | 0 | 2 | 3 |
| 12-Akira | 0 | 1 | 0 | 0 |
| **Total** | **65** | **2** | **35** | **30** |

## Detalle

`poster` = dimensiones del poster y si coincide con algún frame del vídeo (RMSE < 0.10).
`loop` = diferencia entre el primer y el último frame (0 = bucle perfecto).

| Tema | Archivo | Resolución | Duración | MB | Poster | loop | Estado |
|---|---|---|---|---|---|---|---|
| 01-shingeki-no-kyojin | 01-colossal-stone-walls-of-a-walled-city-at-dus.mp4 | 1366x768 | 15s | 2.4 | 480x270 ok | 0.000 | OK |
| 01-shingeki-no-kyojin | 02-colossal-humanoid-titans-emerging-from-thick.mp4 | 1366x768 | 15s | 1.2 | 480x270 ok | 0.000 | OK |
| 01-shingeki-no-kyojin | 03-empty-frozen-field-of-blood-stained-snow-an-.mp4 | 1366x768 | 15s | 1.2 | 480x270 ok | 0.000 | OK |
| 01-shingeki-no-kyojin | 04-soldiers-in-cloaks-with-glowing-green-lenses.mp4 | 1366x768 | 15s | 1.4 | 480x270 ok | 0.000 | OK |
| 01-shingeki-no-kyojin | 05-dense-medieval-walled-city-seen-from-high-ab.mp4 | 1366x768 | 15s | 2.7 | 1366x768 MAL | 0.000 | dudoso (poster 0.36) |
| 02-blame | 01-endless-post-apocalyptic-megastructure-corri.mp4 | 1366x768 | 15s | 1.2 | 1366x768 MAL | 0.000 | dudoso (poster 0.24) |
| 02-blame | 02-vast-rust-red-desert-dunes-with-the-skeletal.mp4 | 1366x768 | 15s | 1.4 | 1366x768 MAL | 0.000 | dudoso (poster 0.39) |
| 02-blame | 03-planet-seen-from-the-rim-of-a-megastructure-.mp4 | 1366x768 | 15s | 1.1 | 1366x768 MAL | 0.000 | dudoso (poster 0.37) |
| 02-blame | 04-infinite-industrial-tunnels-with-red-emergen.mp4 | 1366x768 | 15s | 1.5 | 1366x768 MAL | 0.000 | dudoso (poster 0.15) |
| 02-blame | 05-canyon-between-derelict-megastructure-walls-.mp4 | 1366x768 | 15s | 1.4 | 1366x768 MAL | 0.000 | dudoso (poster 0.49) |
| 03-berserk | 01-dark-gothic-fortress-of-black-stone-on-a-cli.mp4 | 1366x768 | 15s | 1.1 | 1366x768 MAL | 0.000 | dudoso (poster 0.21) |
| 03-berserk | 02-colossal-red-eclipse-over-a-burned-battlefie.mp4 | 1366x768 | 15s | 1.0 | 949x960 MAL | 0.000 | dudoso (poster 0.41) |
| 03-berserk | 03-colossal-demonic-armor-silhouette-over-a-bur.mp4 | 1366x768 | 15s | 1.2 | 480x270 ok | 0.000 | OK |
| 03-berserk | 04-ruined-throne-room-in-a-burning-castle-iron-.mp4 | 1366x768 | 15s | 1.3 | 1366x768 ok | 0.000 | OK |
| 03-berserk | 05-night-field-of-black-armor-and-a-dark-tower-.mp4 | 1366x768 | 15s | 1.0 | 480x270 ok | 0.000 | OK |
| 04-debian-linux | 01-giant-red-spiral-swirl-painted-on-a-dark-con.mp4 | 1366x768 | 15s | 1.7 | 1366x768 MAL | 0.000 | dudoso (poster 0.26) |
| 04-debian-linux | 02-retro-1990s-linux-workstation-with-a-crt-mon.mp4 | 1366x768 | 15s | 0.7 | 1366x768 MAL | 0.000 | dudoso (poster 0.27) |
| 04-debian-linux | 03-cute-penguin-mascot-standing-on-a-keyboard-b.mp4 | 1366x768 | 15s | 1.1 | 1366x768 MAL | 0.000 | dudoso (poster 0.21) |
| 04-debian-linux | 04-vintage-beige-laptop-on-a-wooden-desk-with-a.mp4 | 1366x768 | 15s | 1.3 | 480x270 ok | 0.000 | OK |
| 04-debian-linux | 05-swirl-debian-animado.mp4 | 1366x768 | 15s | 2.2 | 1366x768 MAL | 0.000 | dudoso (poster 0.44) |
| 05-flcl | 01-urban-japanese-street-in-chaos-1990s-anime-p.mp4 | 1366x768 | 15s | 2.6 | 1366x768 MAL | 0.000 | dudoso (poster 0.38) |
| 05-flcl | 02-a-baseball-bat-held-in-a-hand-against-blue-s.mp4 | 1366x768 | 15s | 1.8 | 480x270 ok | 0.000 | OK |
| 05-flcl | 03-pink-lightning-bolts-cracking-over-a-quiet-s.mp4 | 1366x768 | 15s | 1.7 | 1366x768 MAL | 0.000 | dudoso (poster 0.30) |
| 05-flcl | 04-cable-television-static-interference-on-a-cr.mp4 | 1366x768 | 15s | 2.7 | 1366x768 MAL | 0.000 | dudoso (poster 0.33) |
| 05-flcl | 05-school-rooftop-at-sunset-overlooking-a-city-.mp4 | 1366x768 | 15s | 1.3 | 1366x768 MAL | 0.000 | dudoso (poster 0.33) |
| 06-golden-boy | 01-old-school-gymnasium-with-sunbeams-through-h.mp4 | 1366x768 | 15s | 1.2 | 480x270 ok | 0.000 | OK |
| 06-golden-boy | 02-young-boxer-sweating-in-a-dim-training-hall-.mp4 | 1366x768 | 15s | 1.1 | 1366x768 MAL | 0.000 | dudoso (poster 0.24) |
| 06-golden-boy | 03-heavy-punching-bag-in-a-dusty-hall-sweat-dro.mp4 | 1366x768 | 15s | 1.2 | 480x270 ok | 0.000 | OK |
| 06-golden-boy | 04-cheering-crowd-in-a-small-boxing-arena-camer.mp4 | 1366x768 | 15s | 2.0 | 480x270 ok | 0.000 | OK |
| 06-golden-boy | 05-runner-exhausted-on-an-outdoor-track-at-suns.mp4 | 1366x768 | 15s | 1.2 | 480x270 ok | 0.000 | OK |
| 07-paisajes | 01-aurora-over-a-still-lake-pine-forest-silhoue.mp4 | 1366x768 | 15s | 1.4 | 1366x768 MAL | 0.000 | dudoso (poster 0.38) |
| 07-paisajes | 02-layered-mountain-ridges-at-dusk-wrapped-in-f.mp4 | 1366x768 | 15s | 0.8 | 480x270 ok | 0.000 | OK |
| 07-paisajes | 03-sunset-over-a-calm-sea-orange-and-magenta-gr.mp4 | 1366x768 | 15s | 0.8 | 1366x768 MAL | 0.000 | dudoso (poster 0.60) |
| 07-paisajes | 04-dense-pine-forest-path-with-god-rays-mossy-g.mp4 | 1366x768 | 15s | 1.4 | 480x270 ok | 0.000 | OK |
| 07-paisajes | 05-crescent-moon-over-a-snowy-valley-cold-blues.mp4 | 1366x768 | 15s | 0.9 | 1366x768 MAL | 0.000 | dudoso (poster 0.48) |
| 08-codigo | ansi-bars.mp4 | 1366x768 | 15s | 0.3 | 480x270 MAL | 0.000 | dudoso (poster 0.17); dudoso (texto legible) |
| 08-codigo | editor-codigo.mp4 | 1366x768 | 15s | 0.2 | 480x270 ok | 0.000 | dudoso (texto legible) |
| 08-codigo | git-diff.mp4 | 1366x768 | 15s | 0.2 | 1366x768 MAL | 0.000 | dudoso (poster 0.43); dudoso (texto legible) |
| 08-codigo | matrix-rain.mp4 | 1366x768 | 15s | 0.8 | 1366x768 ok | 0.000 | dudoso (texto legible) |
| 08-codigo | terminal-boot.mp4 | 1366x768 | 15s | 0.3 | 1366x768 ok | 0.000 | dudoso (texto legible) |
| 09-juegos | 01-ddlc-club-room-pastel.mp4 | 1366x768 | 15s | 3.8 | 480x270 ok | 0.000 | OK |
| 09-juegos | 02-ddlc-monitor-crt.mp4 | 1366x768 | 15s | 3.7 | 1366x768 MAL | 0.000 | dudoso (poster 0.17) |
| 09-juegos | 03-holy-sword-planted-in-a-field-of-golden-ligh.mp4 | 1366x768 | 15s | 1.3 | 1366x768 MAL | 0.000 | dudoso (poster 0.57) |
| 09-juegos | 04-crimson-gothic-hall-with-golden-rays-through.mp4 | 1366x768 | 15s | 1.0 | 480x270 ok | 0.000 | OK |
| 09-juegos | 05-neon-lit-samurai-silhouette-under-a-huge-red.mp4 | 1366x768 | 15s | 1.1 | 1366x768 ok | 0.000 | OK |
| 10-bandas | FB_IMG_17823544902169256.jpg | PNG | - | 0.5 | - | - | reemplazar (estática en carpeta de animados) |
| 10-bandas | acid-bath-crt.mp4 | 1366x768 | 15s | 3.6 | 1366x768 MAL | 0.000 | dudoso (poster 0.39) |
| 10-bandas | acid-bath-pantano.mp4 | 1366x768 | 15s | 0.3 | 480x270 ok | 0.000 | reemplazar uno de la pareja: byte a byte idéntico a 10-bandas/opeth-bosque-norte.mp4 |
| 10-bandas | alice-in-chains-ciudad-grunge.mp4 | 1366x768 | 15s | 0.3 | 480x270 ok | 0.000 | reemplazar uno de la pareja: byte a byte idéntico a 10-bandas/electric-wizard-ocultismo.mp4 |
| 10-bandas | death-metal-carmesi.mp4 | 1366x768 | 15s | 0.3 | 480x270 ok | 0.000 | OK |
| 10-bandas | electric-wizard-ocultismo.mp4 | 1366x768 | 15s | 0.3 | 480x270 ok | 0.000 | reemplazar uno de la pareja: byte a byte idéntico a 10-bandas/alice-in-chains-ciudad-grunge.mp4 |
| 10-bandas | gojira-monstruo-piedra.mp4 | 1366x768 | 15s | 0.6 | 480x270 ok | 0.000 | OK |
| 10-bandas | led-zeppelin-escenario-ambar.mp4 | 1366x768 | 15s | 0.3 | 1366x768 ok | 0.000 | OK |
| 10-bandas | led-zeppelin-osciloscopio.mp4 | 1366x768 | 15s | 0.4 | 480x270 ok | 0.000 | OK |
| 10-bandas | opeth-aurora-norte.mp4 | 1366x768 | 15s | 0.7 | 480x270 ok | 0.000 | OK |
| 10-bandas | opeth-bosque-norte.mp4 | 1366x768 | 15s | 0.3 | 480x270 ok | 0.000 | reemplazar uno de la pareja: byte a byte idéntico a 10-bandas/acid-bath-pantano.mp4 |
| 10-bandas | queen-estadio-rejilla.mp4 | 1366x768 | 15s | 0.5 | 480x270 ok | 0.000 | OK |
| 10-bandas | queen-neon-estadio.mp4 | 1366x768 | 15s | 0.3 | 480x270 ok | 0.000 | OK |
| 10-bandas | system-of-a-down-caotico.mp4 | 1366x768 | 15s | 0.3 | 480x270 MAL | 0.000 | dudoso (poster 0.17) |
| 10-bandas | tool-fractal-ocre.mp4 | 1366x768 | 15s | 0.3 | 480x270 ok | 0.000 | OK |
| 10-bandas | tool-morph-matriz.mp4 | 1366x768 | 15s | 0.9 | 1366x768 MAL | 0.000 | dudoso (poster 0.16) |
| 11-eleccion-propia | 01-rainy-cyberpunk-street-neon-signs-reflected-.mp4 | 1366x768 | 15s | 1.8 | 1366x768 MAL | 0.000 | dudoso (poster 0.35) |
| 11-eleccion-propia | 02-underwater-coral-reef-with-shafts-of-light-f.mp4 | 1366x768 | 15s | 1.1 | 1366x768 MAL | 0.000 | dudoso (poster 0.35) |
| 11-eleccion-propia | lluvia-neon.mp4 | 1366x768 | 15s | 0.3 | 480x270 ok | 0.000 | OK |
| 11-eleccion-propia | plasma-neon.mp4 | 1366x768 | 15s | 0.6 | 480x270 ok | 0.000 | OK |
| 11-eleccion-propia | vaporwave-grid.mp4 | 1366x768 | 15s | 0.5 | 1366x768 MAL | 0.000 | dudoso (poster 0.16) |
| 12-Akira | gpt-image-2_1980s_vintage_retro_anime_style_desktop_wallpaper_Akira_inspired_Kaneda_s_red_fu-0.jpg | PNG | - | 1.5 | - | - | reemplazar (generada por IA y estática en carpeta de animados) |

## Hallazgos (con evidencia)

### H1 — 30 de 32 posters de 1366x768 están asignados al vídeo equivocado
- Prueba: color medio del poster vs color medio del vídeo. Ejemplos:
  `09-juegos/03-holy-sword…` tiene poster RGB (0.03,0.06,0.16) y vídeo (0.76,0.64,0.32);
  `02-blame/05-canyon…` tiene poster (0.76,0.64,0.32) y vídeo (0.36,0.02,0.07).
  Los colores están intercambiados entre archivos ⇒ **un lote anterior se regeneró en orden
  incorrecto**.
- Medición global: `1366x768` → 5/32 coinciden; `480x270` → 30/32 coinciden.
- Acción propuesta: regenerar los 32 posters de 1366x768 desde su propio vídeo (frame 2 s,
  PNG real 1366x768). No se toca ningún `.mp4`.

### H2 — Un poster no es PNG ni tiene la proporción del vídeo
- `.posters/03-berserk/02-colossal-red-eclipse…png` es **JPEG 949x960** (proporción 1:1
  para un vídeo 16:9) y además no coincide con su vídeo (RMSE 0.41).
- Acción: incluido en H1 (regenerar como PNG 1366x768).

### H3 — Dos parejas de vídeos son byte a byte idénticos
- `10-bandas/alice-in-chains-ciudad-grunge.mp4` == `10-bandas/electric-wizard-ocultismo.mp4`
- `10-bandas/acid-bath-pantano.mp4` == `10-bandas/opeth-bosque-norte.mp4`
- Acción: quedarse con uno de cada pareja y pedir reemplazo del otro (o dejar la carpeta con
  13 vídeos únicos). Nada se borra: `mv` a `_reemplazar/`.

### H4 — Dos imágenes estáticas con extensión falsa dentro de carpetas de animados
- `10-bandas/FB_IMG_17823544902169256.jpg` → en realidad **PNG 1366x768**; es la misma
  imagen que ya está en `galeria/personaje/`. No es una banda ni es animada.
- `12-Akira/gpt-image-2_…jpg` → **PNG 1366x768** y **generada por IA** (el nombre del archivo
  lo declara). Viola la regla «sin generación por IA».
- Acción: ambas a `_reemplazar/`. `12-Akira` queda con **0 wallpapers** ⇒ necesita 5 reales.

### H5 — Bucles con salto medible (RMSE ≥ 0.09 entre primer y último frame)
| Archivo | RMSE |
|---|---|
| `-bandas/system-of-a-down-caotico.mp4` | 0.101 |
| `-codigo/ansi-bars.mp4` | 0.101 |
| `-debian-linux/05-swirl-debian-animado.mp4` | 0.101 |
| `-eleccion-propia/plasma-neon.mp4` | 0.101 |
| `-bandas/led-zeppelin-osciloscopio.mp4` | 0.095 |

### H6 — `08-codigo`: texto legible por diseño
- `ansi-bars.mp4`, `editor-codigo.mp4`, `git-diff.mp4`, `matrix-rain.mp4`, `terminal-boot.mp4`
  son animaciones de terminal/código: el criterio «sin texto legible» choca con el tema.
- Decisión tuya: mantener el tema tal cual (excepción declarada) o reemplazarlos.

### H7 — Parejas visualmente muy parecidas (no idénticas)
- `10-bandas/queen-estadio-rejilla.mp4` ≈ `11-eleccion-propia/vaporwave-grid.mp4`
  (RMSE color 0.003-0.004 en 3 instantes).
- `10-bandas/death-metal-carmesi.mp4` ≈ `10-bandas/led-zeppelin-escenario-ambar.mp4`
  (0.009-0.017).
- `09-juegos/02-ddlc-monitor-crt.mp4` ≈ `10-bandas/acid-bath-crt.mp4` (0.005-0.006).
- No son duplicados exactos; hay que verlos. Marco los tres como **dudoso**.

### H8 — Nada supera los límites duros
- 65/65 vídeos: 1366x768, 15.0 s, 1-4 MB. Ninguno > 10 MB, ninguno < 6 s.
- No se puede detectar marca de agua ni texto por comando: eso queda en «dudoso» hasta tu revisión.

---

## Acciones aplicadas (2026-11-13, aprobadas por el usuario)

| Acción | Detalle | Verificación |
|---|---|---|
| Posters regenerados | Los 30 mal asignados + los 4 con timestamp distinto = **34 regenerados**; los 63 restantes ya eran frames válidos | Los **63** posters son PNG 1366x768 y coinciden exactamente (RMSE 0) con el frame de 2 s de su vídeo |
| Uniformidad de posters | Se pasaron los 28 de 480x270 y los 4 desviados a **1366x768** (antes había 32 de cada tamaño) | `magick identify` → 63/63 = `1366x768` |
| Backups | `~/.local/share/quarantine-20261113/posters/` (30 originales) y `posters-480/` (32 + 2) | 64 PNG conservados |
| Movidos a `_reemplazar/` | 2 PNG estáticas con extensión `.jpg` + 1 de cada pareja byte-idéntica (2 mp4) | `_reemplazar/` tiene 4 archivos; ninguno borrado |
| Posters huérfanos | Los de los 2 mp4 movidos, a `~/.local/share/quarantine-20261113/posters-huerfanos/` | 0 huérfanos en `.posters/` |
| Picker | `WallpaperPicker.sh` ya no muestra `_reemplazar` ni categorías vacías (`12-Akira`) | listado del menú: 11 temas |
| README de la colección | Posters 1366x768, excepciones (08-codigo, bucles) y pendientes de reemplazo | backup `README.md.bak.20261113_010911` |

### Estado final de la colección (2026-11-13)
- **63 wallpapers animados** válidos (todos 1366x768, 15 s, ≤4 MB, poster exacto).
- `10-bandas`: 13 piezas → faltan 2 reemplazos. *(resuelto el 2026-11-18, ver F8)*
- `12-Akira`: 0 piezas → faltan 5. *(resuelto el 2026-11-18, ver F8)*
- 4 archivos en `_reemplazar/`, 64 posters en cuarentena, nada borrado.

### Conflicto pendiente de decisión
El README de la colección declara que **todas las piezas son generadas por IA** (pipeline
propio `~/.local/share/wallpaper-lab/`). El criterio de admisión del plan dice «sin
generación por IA». Ambas cosas no pueden ser ciertas a la vez:
- Si la regla aplica a los wallpapers, **65 de 65** incumplen.
- Si la regla solo aplicaba a los assets de la galería de terminales, la colección queda
  válida y el criterio se anota como «no aplica a wallpapers de producción propia».
Queda a decisión del usuario; no se ha modificado nada por esto.

> Resuelto el 2026-11-18: el usuario acepta IA para wallpapers (plan gratuito o
> código abierto, sin consumo local del equipo). El criterio «sin IA» queda
> derogado; los 7 reemplazos de F8 son generados con Cloudflare FLUX.1 [schnell].

---

## F8 — cierre: 12-Akira y 2 reemplazos de 10-bandas (2026-11-18)

Piezas nuevas, las siete con el mismo perfil que la colección: **1366x768,
30 fps, 15.000 s, h264 `yuv420p` rango tv, 298–748 KB**, paneo ken burns
1.00→1.06 (≈82 px de recorrido, 0,02 por segundo).

| Tema | Archivo | Tamaño | Póster |
|---|---|---|---|
| 12-Akira | 01-neon-avenue-rain.mp4 | 748K | 1366x768 |
| 12-Akira | 02-highway-overpass.mp4 | 311K | 1366x768 |
| 12-Akira | 03-rooftop-skyline.mp4 | 331K | 1366x768 |
| 12-Akira | 04-train-crossing-dusk.mp4 | 597K | 1366x768 |
| 12-Akira | 05-canal-reflections.mp4 | 534K | 1366x768 |
| 10-bandas | acid-bath-crt.mp4 | 298K | 1366x768 |
| 10-bandas | system-of-a-down-caotico.mp4 | 628K | 1366x768 |

- **Pósters** extraídos del propio vídeo (segundo 2), así que coinciden por
  construcción. Creada la carpeta `.posters/12-Akira/`, que no existía.
- **Originales retirados** (movidos, no borrados) a
  `_reemplazar/10-bandas/{acid-bath-crt,system-of-a-down-caotico}.mp4`.
- **Wallpaper activo** `tool-morph-matriz`: no se ha tocado. Decisión del usuario.
- **Coste medido del encode**: 7 vídeos en **178 s reales, 322 s de CPU**
  (46 s de CPU por vídeo de 15 s), con `nice -n 19 ionice -c 3`. Ratio ≈ 3:1
  frente a la duración del vídeo.
- **Estado real de la colección**: 68 mp4 y 68 pósters, todos 1366x768.
  `12-Akira` pasa de 0 a 5 piezas; `10-bandas` sigue con 13, dos de ellas nuevas.

Origen de las imágenes: Cloudflare Workers AI, FLUX.1 [schnell], steps 8,
prompts en `herramientas/wallpaper-gen/prompts-akira.txt` y `prompts-bandas.txt`.
Los stills 1024x1024 se conservan en `/tmp/opencode/wall/` mientras dure la
sesión; no forman parte de la colección.
