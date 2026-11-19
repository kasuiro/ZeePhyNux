# Bitácora - Debian_Hyprland_Look_And_Feel

## 2026-10-22
- Modo agente activado. Keyword: "Remember to smile :)"
- F0: vault auditado, checklist/bitacora creados.
- F1: user_decorations.lua -> blur off, opacidad 0.85 (backup creado). Verificado con hyprctl.
- F2: Fuentes instaladas en ~/.local/share/fonts (JetBrainsMono NF, FantasqueSansM NF, Inter, Noto). fc-cache OK. Kitty apuntando a JetBrainsMono Nerd Font.
- F3: Galería creada en ~/Imágenes/wallpapers/galeria/{anime,manga,series,personaje,meme,stickers,gifts}/
- F3.1: Revisado personaje/gifts. Añadidos: personaje/openclipart-01.png, gifts/openclipart-gift-01.png (OpenClipart Public Domain). Tracker actualizado.
- F3.2: TerminalGallery.sh + fish hook creados. Listo para poblar anime/manga.

## 2026-10-22 - F3.5: Stack solicitado (Shingeki, Berserk, Blame!, Fate/Type-Moon)
- Objetivo: poblar con assets acordes al stack del .md
- Restricción estricta: solo CC0 / Public Domain / licencia explícita permisiva. No fanart sin licencia clara.
- Formatos: PNG/GIF/APNG, tamaño apto para kitten icat
- Estructura: dividir por categoria (prioritario: personaje + anime/manga/series)

## 2026-10-22 - F3.7: Resto del stack (Cyberpunk Edgerunners, Ergo Proxy, Serial Experiments Lain, Evangelion, etc)
- Enfoque: símbolos minimalistas (circuitos, neón, cables, proxy, red, ojos, estructura)
- Fuente: OpenClipart (Public Domain)
- Restricción: evitar retratos reconocibles con copyright

## 2026-10-22 - F3.9: Mapeo completo del stack
- Extraído listado completo de personajes/series/manga/anime del .md
- Creado personajes_mapeo.json (149 entradas) mapeadas a categorias
- Galería estructurada acorde al stack solicitado
- Pool actual: 26 assets (Public Domain) + tracker actualizado
- TerminalGallery.sh responsive y sin _quarantine

## 2026-10-23
- F4 completado: waybar restaurado a [BOT] Simple + [Black & White] Monochrome, waybar restarted OK.
- TerminalGallery.sh re-aplicado (fastfetch fix persistió).
- Checklist.md restaurado desde truncamiento.

## 2026-10-23 - F5: Gamemode (Devmode + Planingmode)
- Creado ~/.config/gamemode/gamemode.ini con configuración AMD iGPU
- Scripts: devmode_start/end.sh, planingmode_start/end.sh
- Wrappers: gamemode_devmode.sh, gamemode_planingmode.sh, gamemode_status.sh
- Keybindings: SUPER+G (Devmode), SUPER+SHIFT+G (Planingmode), SUPER+CTRL+G (Status)
- Validado: luac -p OK

## 2026-11-12 - F5.1: Fix conflicto real de teclas (duplicados de bind)
- Causa raíz (verificada con `hyprctl binds -j`): mi `bind()` no hacía `unbind()` previo.
  Había 2 binds por combo y Hyprland ejecuta ambos:
  · SUPER+G → `toggle group` (vendor) + Toggle Devmode
  · SUPER+SHIFT+G → `GameMode.sh` del vendor ("gamemode") + Toggle Planingmode  ← lo que el usuario veía
  · SUPER+CTRL+G → Ghostty themes + Gamemode status
- `exact = true` no existe en el helper: se ignoraba.
- Fix: binds movidos a SUPER+ALT+G / SUPER+ALT+SHIFT+G / SUPER+ALT+CTRL+G (libres, verificado).
  Vendor restaurado intacto: togglegroup, GameMode.sh, Ghostty themes.
- Aplicado en caliente con `hyprctl eval` (Lua config no acepta `keyword`), sin recargar compositor.
- Wrappers reescritos como toggle sin `read` (desde keybind no hay TTY y se auto-desactivaban).
  Exclusión mutua por markers /tmp/gamemode-<modo>.active. Probado en sandbox y en real (start/end OK).
- Backup: user_keybinds.lua.bak.20261112_222849

## 2026-11-12 - F3.10: Galería de terminales — causa raíz encontrada y corregida
- Bugs reales (no era el diseño, eran 3 errores concretos):
  1. `MAPFILE -t IMGS` → el builtin es `mapfile` (minúsculas). El script salía siempre
     con `IMGS` vacío ⇒ nunca dibujó nada. **Esta era la causa principal.**
  2. `read -r COLS LINES < <(stty size)` → `stty size` devuelve "filas columnas"; estaban
     invertidas, así que la geometría salía absurda (2x18) y el script abortaba.
  3. `timeout 5 kitty +kitten icat` → `timeout` cambia de grupo de proceso y `icat`
     moría por SIGTTIN (rc=137). Ahora `timeout --foreground`.
- Además: imagen movida al costado DERECHO (X = COLS-W-2) para que el prompt no la tape;
  lista global de usadas (`/tmp/termgal-used-$HYPRLAND_INSTANCE_SIGNATURE`) para que cada
  ventana estrene imagen; clamp de geometría a la ventana; hook fish con `disown`.
- Verificado: 3 ventanas kitty → 3 imágenes distintas, `icat` rc=0, geom 16x8@56x1.
- Log opcional: `TERMGAL_DEBUG=1` escribe en `/tmp/termgal-debug.log`.

## 2026-11-12 - F5.2 / F-A: Integridad de posters + wallust seguro para vídeo
- `WallustSwww.sh` corrompía el still: `cp -f "$wallpaper_path" .wallpaper_current` con un
  vídeo escribe los bytes del MP4 encima del PNG (el symlink apuntaba al poster).
  Hallazgo: `.posters/09-juegos/05-neon-...png` era un MP4 de 3,8 MB disfrazado.
- Parche: guard de vídeo → usa `.posters/<tema>/<base>.png` o extrae frame con ffmpeg a
  `~/.cache/wallust/`; `cp --remove-destination`; `WALLUST_NO_HYPR_RELOAD=1` para probar
  sin recargar el compositor.
- Poster regenerado con ffmpeg (PNG 1366x768 real). Corrupto en `/tmp/quarantine-poster/`.
- Quitado `pkill -SIGUSR2 waybar` de los 4 scripts de gamemode (disparaba la cadena de color).
- Verificado: `WallustSwww.sh <mp4>` → exit 0, poster intacto, `.wallpaper_current` PNG real.

## 2026-11-12 - F3.11: galería reescrita como banner de la shell fish
- Síntoma del usuario: «la imagen aparece debajo de la línea de comandos, sin estructura
  que separe imagen y texto, aspecto incorrecto».
- Causa raíz (documentada en `icat --help`, no hipótesis): `--place` deja el cursor en el
  vértice superior izquierdo de la imagen. El script no lo restauraba y además dibujaba en
  background, así que el prompt de fish nacía encima del dibujo.
- Segundo defecto real: `--place` cuenta celdas, no píxeles. Celda medida ≈ 11x25 px.
- Diseño nuevo (`~/.config/hypr/UserScripts/TerminalGallery.sh`):
  * `H = clamp(LINES/3, NINFO+2, 16)`, `W` derivado de la proporción real de la imagen
    (`kitty +kitten icat --print-window-size` + `magick identify`).
  * imagen arriba-derecha (`X = COLS-W-1`), `\r` para volver a la columna 0,
    bloque de texto a la izquierda con **exactamente H líneas**, separador `─`, y el
    prompt nace en la fila H+1.
  * hook: `~/.config/fish/conf.d/terminal_gallery.fish` (síncrono, sin background).
    `fish_greeting` NO se dispara en fish 4.0.2 → se usa la carga de `conf.d`.
  * marcador `/tmp/termgal-greeted-$KITTY_WINDOW_ID` para dibujar una sola vez por ventana.
  * `tr ' ' '─'` rompía el UTF-8 (0xE2 suelto) → sustituido por `printf '─%.0s'`.
- Verificado: 3 ventanas kitty → 3 imágenes distintas, `geom=40x13@44x1` en 85x40,
  `block_rows=13`, rc=0. Log con `TERMGAL_DEBUG=1` en `/tmp/termgal-debug.log`.
- Pendiente: **validación visual del usuario** (el agente no puede ver imágenes).

## 2026-11-13 - F3.12: por qué no se veía la imagen (causas verificadas)
- Causa 1 — **marcadores obsoletos**: el hook usaba `/tmp/termgal-greeted-$KITTY_WINDOW_ID`.
  kitty reutiliza ids (todas las pruebas dieron wid=1) y el fichero quedaba vivo → toda
  ventana nueva con ese id salía sin banner. Reproducido: con el marcador presente, cero
  salida (ni dibujo ni log). **Eliminado el mecanismo de marcadores.**
- Causa 2 — **umbral de ancho**: el script exigía `COLS >= 60` para dibujar. Las ventanas
  en mosaico (dwindle) de este equipo abren a ~41 columnas → no se dibujaba imagen.
  Añadida disposición **apilada** para `COLS < 60`: imagen arriba a lo ancho, texto debajo.
- Gate nuevo del hook: `TERMGAL_WID` exportado con el id de ventana; si un fish anidado
  hereda el mismo id, no repite el banner. Sin ficheros de estado.
- Diagnóstico permanente: cada ejecución escribe una línea en `/tmp/termgal-last.log`
  (modo, geometría, px, rc de icat). No requiere `TERMGAL_DEBUG`.
- Medido: script completo = 27 ms (objetivo < 150 ms).
- Ojo operativo: con muchas ventanas kitty abiertas, dwindle reparte el espacio y las
  ventanas nuevas nacen de 19-41 columnas; en ese estado la imagen sólo cabe apilada.

## 2026-11-13 - F3.13: la imagen ahora se adapta a la forma de cada ventana
- Síntoma del usuario: «la imagen no se adapta a la relación de aspecto que toma cada
  terminal al abrir varias» (estructura y una imagen por terminal ya correctas).
- Causa: la caja de la imagen se calculaba **sólo con la altura** (`ROWS = LINES/3`,
  tope 16) y el ancho se derivaba de ahí. Resultado: en ventanas anchas/bajas la imagen
  quedaba pequeña y con espacio muerto; en ventanas altas tampoco crecía.
- Diseño nuevo: `fit_box MAXW MAXH CELLW CELLH IMGW IMGH`
  * `MAXW` = 55% del ancho (con 24 columnas reservadas al texto), `MAXH` = 60% del alto
    con tope 22 filas.
  * `rel = (cell_h/cell_w) * (img_w/img_h)`; si `MAXH*rel > MAXW` limita el ancho,
    si no limita el alto. La imagen llena la caja sin deformarse.
  * `cell_w = px_w/COLS`, `cell_h = px_h/LINES` medidos con
    `kitty +kitten icat --print-window-size` (aquí 11x25 px).
- Texto: se centra verticalmente contra la imagen (aire arriba calculado), separador `─`
  y relleno hasta exactamente `ROWS` líneas → el prompt sigue naciendo debajo.
- Modo `stack` para `COLS < 60`: imagen arriba al ancho completo (tope 22 filas), texto
  debajo, recortado a las filas que queden.
- Verificado con shims de `stty`/`kitty` sobre 11 formas de ventana (30x8 … 172x40) y 4
  proporciones de imagen (1:1, 16:9, 9:16, 4:3) = 44 combinaciones: **ninguna desborda**,
  todas dibujan. Ventanas reales: `box=46x22 place=46x21@38x1` en 85x40, 3 ventanas →
  3 imágenes distintas, rc=0, 16 ms.

## 2026-11-13 - F3.14: respuesta al redimensionado (Ctrl+L recompone el banner)
- Aclaración del usuario: el problema no era el ajuste inicial, sino que el banner **no es
  responsive** al cambiar el tamaño de la ventana.
- Por qué no puede serlo solo: `icat --place WxH@XxY` fija la imagen en **celdas
  absolutas**; kitty no reajusta esa colocación al redimensionar (la imagen conserva
  píxeles y posición, se recorta o deja hueco).
- Solución elegida por el usuario: **Ctrl+L recompone el banner**.
  * `~/.config/fish/functions/__termgal_redraw.fish`: borra imágenes de kitty
    (`ESC _ G a=d,d=A ESC \`), limpia la pantalla (`ESC[H ESC[2J`, conserva scrollback),
    vuelve a ejecutar el script al tamaño actual y repinta el prompt
    (`commandline -f repaint`).
  * `~/.config/fish/functions/fish_user_key_bindings.fish`: `bind \cl __termgal_redraw`
    (fish 4.0.2 no traía Ctrl+L asignado, no se pisa nada).
  * `TerminalGallery.sh` acepta la imagen como `$1` (repintado con la MISMA imagen) y
    escribe la elegida en `$TERMGAL_IMG_OUT`; el hook la guarda en `TERMGAL_IMG`.
  * Fuera de kitty el atajo hace un clear normal.
- Verificado con un pty real (fish -i, 85x40): Ctrl+L ⇒ 2ª línea de log con la misma
  imagen; `TIOCSWINSZ` a 120x30 + Ctrl+L ⇒ `cols=120 lines=30` (geometría recalculada).
- Verificado en kitty real: `mode=side rc=0 px=935x1000 place=39x22@45x1` reutilizando la
  imagen forzada.
- Pendiente: validación visual del usuario (posición del prompt tras Ctrl+L).
- **F3 cerrada por el usuario (2026-11-13)**: «ahora funciona como es debido». Estructura,
  una imagen por terminal y Ctrl+L tras redimensionar, validados en vivo.

## 2026-11-13 - Fase B: auditoría de los 65 wallpapers (entrega: AUDITORIA_WALLPAPERS.md)
- Método objetivo, sin ver imágenes: `ffprobe` (res/duración), `file` (formato real), `md5sum`
  (duplicados exactos), `magick` + muestreo de 8 frames por vídeo (RMSE poster↔vídeo y
  continuidad de bucle frame 0 vs último).
- Resultado: 65 mp4 (todos 1366x768, 15 s, 1-4 MB) + 2 estáticas con extensión .jpg falsa.
  28 archivos OK, 33 dudosos, 6 a reemplazar.
- **Hallazgo importante**: 30 de los 32 posters de 1366x768 están asignados al vídeo
  equivocado (los colores están intercambiados entre archivos). Los 480x270 sí coinciden
  (30/32). Un lote anterior se regeneró en orden incorrecto ⇒ wallust tomaba colores de
  otra imagen.
- Otros: 1 poster es JPEG 949x960 con nombre .png; 2 parejas de mp4 byte a byte idénticas
  (10-bandas); 2 PNG estáticas con extensión .jpg (una de ellas generada por IA, en 12-Akira,
  que se queda con 0 wallpapers); 5 bucles con salto medible ≥0.09; 5 wallpapers de
  08-codigo con texto legible por diseño.
- Nada se movió ni se borró todavía: las acciones esperan decisión del usuario.

### Fase B — acciones aplicadas (con OK del usuario)
- **34 posters regenerados** (30 mal asignados + 4 con timestamp distinto) y **28 más
  pasados de 480x270 a 1366x768**: los 63 posters son ahora PNG 1366x768 y coinciden
  exactamente (RMSE 0) con el frame de 2 s de su vídeo.
  Motivo del 1366x768: `hyprlock` usa `.wallpaper_current`, que es una copia del poster;
  a 480x270 el bloqueo salía pixelado.
- Backups: `~/.local/share/quarantine-20261113/posters/` (30) y `posters-480/` (34).
- **4 archivos movidos a `~/Imágenes/wallpapers/_reemplazar/`**: las 2 PNG estáticas con
  extensión `.jpg` (una era la de la galería, la otra generada por IA en 12-Akira) y un
  mp4 de cada pareja byte-idéntica (`opeth-bosque-norte`, `electric-wizard-ocultismo`).
  Sus posters a `quarantine-20261113/posters-huerfanos/`.
- Resultado: 63 wallpapers válidos; `10-bandas` 13 piezas (faltan 2), `12-Akira` 0 (faltan 5).
- `WallpaperPicker.sh` parcheado: excluye `_reemplazar` y categorías vacías
  (backup `.bak.20261113_010623`). Verificado: el menú lista 11 temas.
- `WallustSwww.sh` sobre un vídeo con poster regenerado → exit 0 y `.wallpaper_current`
  PNG 1366x768.
- Conflicto detectado y **sin resolver a propósito**: el README de la colección declara
  que las 65 piezas son generadas por IA (pipeline propio), mientras el criterio de
  admisión del plan dice «sin generación por IA». Decisión del usuario pendiente.

## 2026-11-13/15 - Fase D: buzón de assets de la galería
- Creado `~/Imágenes/wallpapers/galeria/_inbox/` con `dudas/` y `LEEME.md` (instrucciones
  en español: cómo nombrar, formatos aceptados, qué hace el clasificador).
- Nuevo `~/.config/hypr/UserScripts/GalleryIntake.py`:
  * identifica personaje/serie por el nombre del archivo contra `personajes_mapeo.json`
    (normaliza acentos y mayúsculas), p. ej. `Killy_de_BLAME.png` → `manga/blame--killy--01.png`;
  * normaliza a PNG de 512 px de ancho máximo (`magick -resize 512x>`), conserva GIF/APNG;
  * numera sin pisar (`serie--personaje--NN`), registra la fila en `ASSETS_TRACKER.md`
    con origen «aportado por el usuario»;
  * el original se mueve a `_inbox/procesados/`; lo no reconocido a `_inbox/dudas/`;
  * `--dry-run` informa sin tocar nada; `GALERIA_ROOT` permite probar en otra ruta.
- Probado en `/tmp/gal-test` con 3 archivos: 2 clasificados (berserk/guts, blame/killy),
  1 a `dudas/`, tracker con 2 filas nuevas, originales conservados. Prueba eliminada.
- Verificado que `TerminalGallery.sh` ya excluye `_inbox` de la selección de imágenes.
- Decisión del usuario: el criterio «sin generación por IA» **no aplica a los wallpapers**
  (colección de producción propia); sí sigue aplicando a los assets de la galería.

## 2026-11-15 - Fase E (1/3): Readmode + Writemode
- Nuevos modos con el patrón existente (`<modo>_start.sh` / `_end.sh` + wrapper toggle),
  más un toggle genérico `gamemode_toggle.sh <modo>` y utilidades compartidas
  `gamemode_common.sh` (marcadores, hyprsunset, no molestar, exclusión mutua).
- **Readmode**: luz cálida 3800K (`hyprsunset`) + «no molestar» en swaync.
- **Writemode**: luz 5200K + «no molestar» + cierra el panel y la última notificación.
- Ninguno ejecuta `sudo`: no tocan gobernadores de CPU/iGPU ni el scheduler (requiere root).
  Lo único que cambia es luz de pantalla y notificaciones, y todo se restaura al salir.
- Exclusión mutua real: `gamemode_toggle.sh` apaga cualquier otro `*_start.sh` con marcador
  activo. Los wrappers de Devmode y Planingmode se reescribieron sobre el toggle genérico
  (misma semántica). Backups `.bak.20261115_200113`.
- `gamemode_status.sh` ampliado: modos activos, filtro de luz y estado de no molestar.
- Keybinds nuevos y libres (verificado con `hyprctl binds -j`): `SUPER+ALT+SHIFT+R` y
  `SUPER+ALT+SHIFT+W`. Añadidos a `user_keybinds.lua` (backup `.bak.20261115_200221`,
  `luac -p` OK) y aplicados en caliente con `hyprctl eval` → 201 → 203 binds, sin duplicados.
- Pruebas: sandbox `/tmp/gmtest` (3 modos falsos: alternancia y apagado correctos),
  y en real start/end de ambos modos (hyprsunset arranca y muere, DND se restaura al
  estado previo incluso si ya estaba activo, marcadores limpios).
- Pendiente: indicador en waybar (sigue bloqueado por wallust/I1) y los 3 modos restantes
  (GameDevmode, 3Dmode, AudioVisualmode).

## 2026-11-15 - Fase E (2/3): GameDevmode + 3Dmode
- **GameDevmode** y **3Dmode**: congelan el wallpaper de vídeo (`SIGSTOP` a `mpvpaper`) para
  liberar iGPU/CPU, activan «no molestar» y no aplican filtro de color (los colores de un
  juego/modelo 3D no deben falsearse). Al salir: `SIGCONT` y se restaura el DND previo.
- Añadido a `gamemode_common.sh`: `gm_wallpaper_pause` / `gm_wallpaper_resume` con marcador
  `/tmp/gamemode-wallpaper.frozen`. Si `mpvpaper` no corre (wallpaper estático), no hace nada.
- Sin `sudo`: no se tocan gobernadores de CPU/iGPU ni el scheduler. Lo único que se modifica
  es la reproducción del wallpaper y las notificaciones, y todo es reversible.
- Keybinds libres verificados: `SUPER+ALT+SHIFT+D` (GameDevmode) y `SUPER+ALT+SHIFT+3` (3Dmode).
  Añadidos a `user_keybinds.lua` (`luac -p` OK) y aplicados en caliente → 203 → 205 binds.
- `gamemode_status.sh` muestra también si el wallpaper está congelado.
- Pruebas reales: start/end de ambos (mpvpaper pasa a `T` y vuelve a `S/R`, DND se restaura),
  cambio Readmode → GameDevmode (hyprsunset muere, queda un solo modo activo), sin residuos.

## 2026-11-15 - Fase E (3/3): AudioVisualmode y cierre de los 7 modos
- **AudioVisualmode**: congela el wallpaper de vídeo, baja la latencia de PipeWire
  (`clock.force-quantum` 1024→128, restaurado a su valor previo al salir), DND y sin
  filtro de color. Sin `sudo`.
- Keybind `SUPER+ALT+SHIFT+A` añadido (`luac -p` OK) y aplicado en caliente → 205 → 206 binds.
- `gamemode_status.sh` muestra también la latencia de audio forzada.
- Barrido de exclusividad sobre los 5 modos sin `sudo` (read → write → gamedev → 3d →
  audiovisual): en cada paso queda un único marcador; al final 0 marcadores, sin
  hyprsunset, mpvpaper reproduciendo, DND apagado y quantum 0.
- **Los 7 modos existen ya**: Devmode, Planingmode, Readmode, Writemode, GameDevmode,
  3Dmode, AudioVisualmode. Pendiente: indicador en waybar y la capa de
  roles/tesoros/recompensas/puntos (propuesta a largo plazo).

## 2026-11-15 - Indicador de modo en waybar
- Módulo `custom/gamemode` (definido en `~/.config/waybar/UserModules`, el archivo pensado
  para extras) y añadido a `modules-right` del layout activo `[TOP] Default Laptop`.
- `GamemodeIndicator.sh` devuelve JSON: texto corto (`● READ`, `● 3D`, `● AV`…), tooltip con
  los efectos activos (luz cálida / wallpaper congelado / audio 128 / sin avisos) y una clase
  CSS por modo. Sin modo activo devuelve texto vacío y `hide-empty-text` lo oculta.
- Camino rápido sin modo: solo globs, sin subprocesos; ~7 ms por ejecución cada 2 s.
- Clic → `gamemode_status.sh`, que ahora **notifica** cuando no hay terminal (antes el keybind
  de estado no mostraba nada).
- Colores por modo en `style/[Black & White] Monochrome.css` (azul DEV, verde PLAN, ámbar READ,
  malva WRITE, rojo GAMEDEV, turquesa 3D, melocotón AV).
- Validación: instancia de prueba de waybar (config + CSS reales) sin errores; módulo probado
  con un `exec` de sonda → 4 ejecuciones en 4 s. Luego `Refresh.sh` (ruta oficial, sin reload
  del compositor): waybar reiniciado (PID 2252988 → 2328075) y vivo.
- **Deriva asumida**: si cambias el estilo de la barra desde el menú, el bloque
  `#custom-gamemode` no estará en el tema nuevo; el módulo seguirá funcionando sin color.
- Backups: `UserModules.bak.20261115_202714`, `[TOP] Default Laptop.bak.20261115_202714`,
  `[Black & White] Monochrome.css.bak.20261115_202714`.

## 2026-11-15 — Mediciones de consumo de la barra y helper energético

### Coste real de waybar (medido, no estimado)

| Medición | Valor | Método |
|---|---|---|
| waybar | 7.0 % CPU sostenido, 62 MB RSS | delta de `/proc/<pid>/stat` en 5 s |
| `cava` (módulo `custom/cava_mviz`) | **4.2 % CPU**, 12.5 MB RSS | idem sobre el hijo |
| Hijos persistentes | 2× `playerctl -F`, 2× `swaync-client -swb` | `pgrep -P` |

El 60 % del coste de la barra es el visualizador de audio. Los módulos
persistentes aparecen duplicados aunque en la config solo estén declarados una
vez: pendiente de localizar el origen (waybar 0.12 + `include` de 5 directorios).

### Capacidades reales de la máquina

- `acpi-cpufreq`, gobernadores **solo** `performance` y `schedutil`; política
  actual min = max = 1.90 GHz (clavada arriba).
- iGPU: `power_dpm_force_performance_level` presente; `pp_dpm_sclk` vacío (Kaveri).
- power-profiles-daemon activo con `PlatformDriver: placeholder` → no gestiona nada.
- Sin paquete `scx-scheds` en trixie → sched-ext descartado sin compilar.
- Delegación de cgroups del usuario **funciona**: `CPUWeight`, `CPUQuota`,
  `IOWeight` y `AllowedCPUs` se aplican con `systemctl --user` (probado y revertido).

### Entregable nuevo

`herramientas/power-modes/` — helper root mínimo (2 knobs: gobernador+techo de
frecuencia y nivel DPM de la iGPU) con las fuentes oficiales citadas por bloque,
sudoers acotado por argumento exacto, verificación y rollback. Probado sin root:
`status` lee, argumento inválido → rc 2, escritura sin root → rc 3.

### Decisión de criterio (usuario)

La IA generativa de imágenes **se acepta** para la colección y la galería, con
dos condiciones: que no consuma recursos de esta máquina y que sea de código
abierto o plan gratuito. Sustituye la regla anterior de «sin IA» en la galería.
Proveedor pendiente de elegir.

## 2026-11-15 (tarde) — Híbrido de waybar, enrutado de la galería y generador de imágenes

### Waybar híbrido (opción B) sobre `[TOP] Default Laptop`

Medido antes y después con delta de `/proc/<pid>/stat`:

| | Antes | Después |
|---|---|---|
| CPU de waybar | 7.0 % | **4.35 %** (media de 20 s) |
| `cava` | 4.2 % + 12.5 MB | ya no existe |
| `playerctl -F` persistente | sí | sustituido por módulo `mpris` (intervalo 10 s, se oculta solo) |
| RSS | 62 MB | 63 MB |

Nuevo reparto: izquierda menú+workspaces+ventana · centro reloj+avisos+inhibidor ·
derecha mpris, modo, bandeja, conexiones, portátil, hardware, audio, luz nocturna, energía.

- Se eliminaron `cava_mviz`, `custom/weather`, `network#speed`, `custom/hint` y
  `group/mobo_drawer` (llevaba `power-profiles-daemon`, que en este equipo es un
  placeholder y no muestra nada real).
- Grupo propio `group/mobo_light` (cpu, temperatura, memoria, disco) en `UserModules`,
  sin tocar los ficheros compartidos de KoolDots.
- Validación: JSONC parseado, instancia de prueba con `ipc:false` 6 s sin errores
  (solo dos avisos conocidos: rfkill no compilado y `disk.path` obsoleto).
  Reinicio por `Refresh.sh`; waybar vivo (PID 2485370).
- Pendiente: confirmación visual del usuario (anchos del lado derecho).

Reparto del coste restante (sondas con instancia aparte, `ipc:false`, 7-8 s cada una):

| Medición | CPU |
|---|---|
| barra completa | 4,75 % |
| solo lado derecho | 4,25 % |
| solo centro (reloj + avisos + inhibidor) | 0,88 % |
| solo izquierda (menú + workspaces + ventana) | 0,00 % |
| `group/status` (energía, bloqueo, teclado) | 1,00 % |
| `group/mobo_light` | 0,86 % |
| `group/laptop` / `custom/nightlight` | 0,43 % cada uno |
| `group/audio` | 0,00 % |

No queda ningún módulo devorador: el coste es «muchos módulos periódicos, cada
actualización repinta la superficie entera». Quitar uno solo se nota poco.

### Galería: enrutado por categoría

`GalleryIntake.py` tenía un hueco real: `stickers`, `meme`, `gifts` y `personaje`
no tienen personajes en el mapeo (149 entradas, solo anime/manga/series/juegos),
así que cualquier imagen de esas categorías acababa en `dudas/`. Añadido
`por_categoria()`: si el nombre trae la palabra clave, va a
`<categoria>/aportes--<slug>--NN.png`. El personaje sigue teniendo prioridad.

Probado en árbol aislado (`GALERIA_ROOT=/tmp/...`) con 5 sintéticos: 4 clasificados
(900 px → 512 px, tracker actualizado, originales a `procesados/`) y 1 a `dudas/`.
También se corrigió que `--dry-run` no diga «ya están en la galería».

### Generador de imágenes (IA aceptada)

Se midió el terreno antes de elegir:

| Vía | Resultado medido hoy |
|---|---|
| Pollinations (`sana`) | **HTTP 402 Payment Required** — la capa anónima ya no sirve imágenes |
| Cloudflare Workers AI · FLUX.1 schnell | 12B, Apache-2.0, 4,80 neuronas/baldosa + 9,60/paso → ~230 imágenes de 512² al día en el plan Free, sin tarjeta |
| Difusión local | descartada: 4 núcleos 1.9 GHz, 6.7 GB, HDD |

Entregado `herramientas/gallery-gen/`: `GalleryGen.py` (cf + pollinations como
diagnóstico, reintentos con backoff, `--check` que no gasta neuronas, `--dry-run`),
`README.md` con las fuentes y el coste, y `prompts.txt` con la regla de describir
sin nombrar personajes con copyright. Falta que el usuario cree la cuenta y exporte
`CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN`.

## 2026-11-18 — Enganche modos↔helper energético y generador↔galería

Sesión nueva tras reinicio (arranque 02:11). Los marcadores de modo viven en
`/tmp` y se pierden al reiniciar: ningún modo quedó activo y el perfil energético
se quedó en `schedutil 1.10–1.90 + iGPU auto`. Comportamiento esperado, pero
conviene saberlo.

### Hallazgo: la iGPU de este equipo rechaza el nivel DPM

`sudo -n mode-power perf` (y `eco`, `balanced`) devolvía **rc 234** después de
aplicar bien la CPU. Causa: la escritura en
`power_dpm_force_performance_level` recibe `EINVAL` (234 = -22 en complemento a
dos) y `pp_dpm_sclk` está vacío → este ASIC (Kaveri) no soporta forzar el nivel.
El helper ahora lo trata como aviso y sigue; el perfil de CPU sí se aplica.

También se corrigió el README, que decía que `sudo -n mode-power status` no
pediría contraseña: `status` no está en el sudoers a propósito.

### Enganche en los modos (una sola edición)

`gamemode_common.sh`: `gm_power_apply`, `gm_power_restore`, `gm_power_for_mode`.
`gamemode_toggle.sh`: aplica el perfil al entrar y lo restaura al salir.
Probado con Readmode (eco → techo 1.50 GHz) y su salida (vuelta a 1.90 GHz),
sin residuos y con el wallpaper intacto.

Pendiente del usuario: reinstalar helper y sudoers (hace falta su contraseña)
para tener el verbo `restore` y el arreglo de la iGPU.

### Generador → galería

`GalleryGen.py --intake` clasifica lo generado al terminar llamando a
`GalleryIntake.py`. Probado `--dry-run` y `--help`; la prueba real espera el token
de Cloudflare, que no está en el entorno (`CLOUDFLARE_API_TOKEN: ausente`).

### Primer lote real en la galería (21 imágenes)

El buzón `_inbox/` tenía 21 imágenes del usuario sin procesar. `blame_v1…v8`
salían como *dudosas* porque el clasificador solo miraba nombres de personaje.
Se añadió una segunda pasada por **serie** (`identificar()`): si no hay
personaje, una palabra de la serie vale y el personaje pasa a `generico`.
Resultado: 8 → `manga/blame--generico--NN.png`. Las 13 de Shingeki ya entraban
bien. Copia previa del script: `GalleryIntake.py.bak.20261118_043833`.

Ingesta completa: 13 en `anime/`, 8 en `manga/`, 21 originales en
`_inbox/procesados/`, 21 filas nuevas en `ASSETS_TRACKER.md`, 0 en `dudas/`.
`_inbox/*` está excluido del `find` de `TerminalGallery.sh`, así que ni
`procesados/` ni `dudas/` aparecen como imágenes de terminal.

### Token de Cloudflare: válido pero sin permiso

Medido: `/user/tokens/verify` → **200, active**. Pero
`/accounts/<id>/ai/models/search` → **403** y `/ai/run/@cf/…/flux-1-schnell` →
**401**, ambos `Authentication error`. `/accounts` → 200 con **0 cuentas**, o
sea que el token no tiene ningún recurso de cuenta: es un token de usuario sin
`Workers AI`. No es la longitud ni un espacio de más (53 caracteres, charset
`[A-Za-z0-9_-]`).

Según los docs, el camino fiable es **Workers AI → Use REST API → Create a
Workers AI API Token**; a mano hacen falta `Read` **y** `Edit`. `--check` ahora
distingue los tres fallos (revocado / sin permiso / Account ID de otra cuenta).

### Primer lote generado (5 imágenes) y dos defectos corregidos

Con el token bueno, `--check` → `permiso Workers AI: OK` y el primer lote salió:
`stickers/aportes--hooded-swordsman--01.png`, `stickers/aportes--cyber-hacker--01.png`,
`meme/aportes--flat-what--01.png`, `gifts/aportes--lantern-fox--01.png`,
`personaje/aportes--mech-pilot--01.png`. 512×512 tras normalizar, 142–269 KB.

**Defecto 1 — el 400 de FLUX.** El script mandaba `width`/`height` y el modelo los
rechaza: `AiError: Additional or unevaluated properties '/width, /height'`. Las 5
peticiones fallaron con `400` hasta quitarlos. Ahora la petición lleva solo
`prompt` + `steps`, y el error imprime el cuerpo de Cloudflare en vez de
«Bad Request». Medido: devuelve **1024×1024**, así que `--size` solo sirve para
pollinations.

**Defecto 2 — duplicados en `personaje/`.** Había 8 `blame_v*.jpg` (del 15 nov,
byte a byte iguales a los originales de `procesados/`) conviviendo con los 8
`manga/blame--generico--NN.png` nuevos. Movidos a
`~/.local/share/quarantine-20261118-galeria-personaje/` (reversible). La galería
pasa de 36 a **28 imágenes**.

También se arregló el tracker: no tenía cabecera (40 filas sueltas) y las filas
de IA decían «aportado por el usuario». Ahora `GalleryIntake.py` acepta
`--origen "<texto>"`, `GalleryGen.py --intake` pasa
«generado por IA (Cloudflare FLUX.1 schnell)», y `ASSETS_TRACKER.md` tiene
cabecera. Copia previa: `ASSETS_TRACKER.md.bak.20261118_051540`.

### Lote 2 (17 imágenes) y capa de contexto de prompt

El usuario detectó que el primer lote no se parecía a lo pedido. Causa: el prompt
iba desnudo («pixel art sticker of X») y el modelo decidía escena, encuadre y
fondo por su cuenta. Arreglo en `GalleryGen.py`:

- `BASE`: estilo fijo que se añade a **todos** los prompts (16-bit, píxel duro,
  12 colores, sombreado plano, sujeto centrado, fondo liso, sin texto ni marco).
- `CONTEXTOS`: una capa por categoría (sticker → contorno grueso y fondo liso;
  meme → formas simples sin pie de foto; personaje → busto; series → emblema sin
  logos; juegos → icono de silueta fuerte; gift → paleta cálida).
- `componer()`: sujeto primero, luego contexto de categoría, luego `BASE`.
- Se imprime el prompt **final** antes de cada petición, así se audita lo que se
  manda de verdad. Flags: `--contexto "<extra>"`, `--sin-contexto`.
- `--steps 6` en este lote (el 1º usó 4) para mejorar la adherencia.

También hubo que añadir `series` y `juegos` a `CATS` de `GalleryIntake.py`: sin
eso, `series-detective-badge.jpg` habría acabado en `dudas/` y esos dos catálogos
no se podían llenar (estaban a 0).

Resultado: 17 imágenes nuevas, 512×512, 0 dudas. Reparto: stickers 4, meme 2,
gifts 2, personaje 3, series 3, juegos 3. Galería **45 imágenes**
(anime 13, manga 8, stickers 6, meme 5, gifts 3, personaje 4, series 3, juegos 3).
Coste del lote: ~1 300 neuronas (17 × ~77).

Copia previa de prompts: `prompts.txt.bak.20261118_053608`.

## 2026-11-18 — Nace Questline (F9.0 + F9.1)

Subsistema de escritorio que convierte el trabajo real en un log de eventos y
una capa de recompensas encima. Documentado en ingles (decision del usuario) en
`docs/subsystem/`: `SPEC.md` (decisiones, modelo de datos, fases), `RULES.md`
(16 invariantes) y `BACKLOG.md` (17 items con criterio de aceptacion).

Decisiones cerradas: moneda **Fragments**, logros **Stamps**, backlog y
documentacion en el vault de Obsidian `~/Documentos/Vault`, tablero en **AGS**
(ya corriendo, 61 MB), puntos **hibridos** (tiempo + tareas), y sincronizacion
multidispositivo desde el primer dia.

### Por que el diseno es barato

El estado se **deriva** del log, asi que sincronizar varios equipos es solo
sincronizar ficheros: union de logs, dedupe por `event_id`, orden por
`(ts, device, seq)`. Dos equipos con los mismos eventos no pueden discrepar. No
hay servidor, ni CRDT, ni dialogos de conflicto.

### Implementado

- `herramientas/questline/ql.py` (solo stdlib): log append-only con `flock`,
  `event_id` uuid4, `device`, `seq`, y `day` local sellado por el equipo emisor
  (asi la racha no depende de zonas horarias).
- `fold()` puro: sesiones cerradas, tope de 4 h por sesion, 40/dia/modo, bonus
  de rol por sesion (rol vigente al **empezar**), racha y bonus.
- CLI: `ql mode start|stop`, `done`, `reopen`, `role`, `status [--json]`,
  `rebuild`, `events`, `device`, `log`.
- Hook `gm_quest` en `gamemode_common.sh`, llamado en `gamemode_toggle.sh` y en
  `gm_end_others` (cambio de modo cierra la sesion anterior). Si `ql` no existe,
  no hace nada: probado con `QL_BIN=/nonexistent`, el modo funciona igual.
- Vault creado: `Projects/`, `Weekly/`, `Inbox.md` y `Questline/` (visible, no
  oculto, porque las herramientas de sincronizacion suelen saltarse dotfiles).

### Verificado

- `python3 tests/smoke.py` -> **17/17**. Cubre dedupe, LWW en tareas, topes,
  bonus de rol, racha, merge de dos equipos y sesion abierta sin puntos.
- Prueba real: `readmode` activado y cerrado desde el keybind -> 2 eventos en
  `events/kasuirogroup-976616.tsv`, perfil energetico restaurado, sin residuos.
- Syntax check de ambos scripts de gamemode; backups `.bak.20261118_114745`.

Siguiente: F9.2 (escaneo del vault, block IDs `^ql-xxxxxx`, cache por mtime).

## 2026-11-18 — F9.2: el vault ya alimenta el sistema

`ql` lee el vault de Obsidian como si fuera una base de datos de tareas. Una
tarea es cualquier linea `- [ ]` / `- [x]`; `#project/<nombre>` la agrupa.

| Comando | Efecto |
|---|---|
| `ql tasks [--project X] [--json]` | lista, **nunca escribe** |
| `ql scan --write-ids` | añade `^ql-xxxxxx` una sola vez a cada tarea |
| `ql sync` | emite `task.done` / `task.reopen` solo si algo cambió |

### Identidad sin base de datos

El id se deriva de `sha1(ruta + texto)`; al escribirlo como block ID de Obsidian
(`^ql-a1b2c3`), la tarea sobrevive a que la linea se mueva de nota. Antes de
escribir, la nota se copia a `Questline/id-backups/`.

Regla importante: **el primer `sync` es una linea base y no da puntos**. Si no,
un vault con 200 casillas ya tildadas regalaria 2 000 fragmentos de golpe.

### Bug encontrado por los tests

El id derivado se comparaba contra el cache, que ya contenia ese mismo id, y el
script lo interpretaba como colision: extendia el hash de 6 a 8 caracteres en
cada pasada, cambiando la identidad de la tarea. El cache ahora guarda a quien
pertenece cada id y solo trata como colision un id de **otra** tarea.

### Verificado

- **300 notas / 6 000 tareas**: 0,52 s en frio y 0,40 s con cache caliente.
- 32 comprobaciones en `tests/smoke.py`, 0 fallos.
- Prueba real sobre `Vault/Inbox.md`: tildar dio 10 FRG, destildar los devolvio,
  y quedaron los dos eventos (`task.done`, `task.reopen`) en el log.

Siguiente: F9.3 (contador en waybar).

## 2026-11-18 — F9.3: contador en waybar, y 12× menos coste de paso

El modulo `custom/gamemode` corre **cada 2 s**. Añadir `ql status` ahi habria
costado ~1,5 % de CPU (arrancar Python 43 000 veces al dia). En su lugar, `ql
rebuild` deja dos ficheros de una linea y el script los lee con `read`:

```
~/.local/state/questline/line   ->  42 FRG · 3d
~/.local/state/questline/tip    ->  role artisan · racha 3d · 17 tareas
```

Resultado en la barra: `● READ · 42 FRG · 3d` (el segmento desaparece si aun no
hay fragmentos, para no ensuciar la barra).

### Hallazgo: el tooltip sondeaba cuatro cosas cada 2 s

Medido con 30 ejecuciones del indicador: **117 ms de CPU por vuelta** (5,8 % de
un nucleo) por `pgrep`, `pw-metadata` y `swaync-client -D`. Todo eso ya lo
muestra el clic del modulo (`gamemode_status.sh`), asi que se quito del tooltip.
Ahora son **9,8 ms por vuelta**: 12 veces menos.

| Medicion | Antes | Ahora |
|---|---|---|
| Coste del indicador (por vuelta) | 117 ms | **9,8 ms** |
| A 1 vuelta cada 2 s | 5,8 % de un nucleo | **0,49 %** |
| Coste añadido por el contador | — | **+0,01 %** (2 lecturas por vuelta) |
| JSON del modulo | valido | valido, mismo formato |

El 7 % que mide waybar con un modo activo es su propio repintado (ya estaba
documentado en el hibrido); el ahorro del indicador es CPU del sistema aparte.
Backup del script: `GamemodeIndicator.sh.bak.20261118_162505`.

Siguiente: F9.4 (tablero en AGS).

## 2026-11-18 — F9.4: tablero, y por que no hay socket

Tablero en **GTK4 + libadwaita** (`herramientas/questline/board.py`, symlink
`~/.local/bin/ql-board`): dos columnas Open/Done, filtro por proyecto, contador
en la cabecera. Lee con `ql tasks --json` y escribe con `ql done|reopen <id>`.

### Cambio importante: cerrar desde el tablero toca el vault

`ql done` ya no solo apunta el evento: **tilda la casilla** en la nota, con copia
previa en `Questline/id-backups/`. Asi Obsidian y el tablero no pueden discrepar.
Y como la cache de la nota se invalida, el `sync` siguiente no vuelve a contar
los mismos 10 fragmentos (4 comprobaciones nuevas).

### Bug que aparecio al probarlo a mano (y los tests no veian)

`done` imprimia la linea y despues caia con `UnboundLocalError: ev` porque el
`return 0` faltaba y el final de `main()` imprimia `ev`. **Los tests pasaban
igual**, porque el helper no miraba el codigo de salida. Arreglado el `return` y
endurecido el helper (`Env.ok()`, falla si rc != 0): 41 comprobaciones.

### Decision: nada de socket por ahora

El BACKLOG pedia un socket Unix. Eso exige un proceso escuchando siempre, que es
justo lo que prohibe el invariante 8 (sin daemon). Se aplaza hasta que exista un
cliente que no pueda ejecutar `ql` — el movil o un agente — y entonces sera una
unidad de socket de systemd: arranca con la primera conexion y muere al quedar
ociosa.

### Keybind

`SUPER+ALT+SHIFT+B` añadido a `UserConfigs/user_keybinds.lua` (backup
`.bak.20261118_1638`, `luac -p` OK). **No recargue Hyprland**: el bind estara
activo tras el siguiente reload, y recargar la config Lua ya tumbo el compositor
una vez. Mientras tanto, `ql-board` desde terminal o rofi funciona.

`board.py` arrancado 5 s sin errores (solo un aviso de Adwaita sobre el tema
oscuro global, inofensivo).

### Recarga hecha (2026-11-18), con el bind ya activo

Antes de recargar se validaron **solo los modulos que de verdad carga**
`hyprland.lua` (`user_defaults`, `animations`, `user_overrides`, `monitors`) y
los 10 `UserConfigs/user_*.lua`: todos `luac -p` OK. Aviso util: `lua/startup.lua`
**no compila** con `luac` pero es una plantilla inerte, no la carga nadie; no se
toco.

`hyprctl reload` devolvio **rc=6 "IPC didn't respond in time"**, pero el cambio
si se aplico: el bind `Questline: tablero` (modmask 73, tecla B) aparece en
`hyprctl binds`. El compositor no se cayo (mismo pid 4294), waybar 1 proceso,
`mpvpaper` intacto, las 2 ventanas siguen ahi y el wallpaper no cambio. Los 8
binds de gamemode siguen sin duplicados.

Moraleja: el codigo de salida de `hyprctl reload` en esta config Lua no es fiable;
lo que hay que mirar es `hyprctl binds` y que el pid de Hyprland no cambie.

## 2026-11-18 — F8 cerrada: 7 wallpapers nuevos y colección completa

`12-Akira` estaba vacío y `10-bandas` tenía 2 piezas flojas. Ahora: 5 piezas
nuevas en Akira y 2 reemplazos en bandas, generados con Cloudflare a partir de
los stills y animados con el ken burns de la colección.

| Dato | Valor |
|---|---|
| Piezas nuevas | 7 (5 Akira + 2 bandas) |
| Formato | 1366x768, 30 fps, 15.000 s, h264 `yuv420p` tv, 298–748 KB |
| Coste del encode | **178 s reales / 322 s de CPU** (46 s por vídeo de 15 s) |
| Pósters | 7, extraídos del segundo 2 → coinciden por construcción |
| Colección | **68 mp4 y 68 pósters**, todos 1366x768 |

El encode va con `nice -n 19 ionice -c 3`, medido con el `time` de bash. Ratio
≈3:1 CPU/vídeo: aceptable para un equipo de 4 núcleos, pero es el motivo de no
hacer más de un puñado a la vez.

Decisiones del usuario aplicadas: zoom **1.06** (el de la muestra) y **no tocar**
el wallpaper activo. Los originales de bandas no se borraron: están en
`_reemplazar/10-bandas/` (junto a los dos que ya había).

Detalle: la exportación del póster dejaba `yuvj420p` cuando el JPEG de origen es
rango completo; se añadió `-pix_fmt yuv420p -color_range tv` a `wallpaper.sh`
para que coincida con el resto de la colección.

Los stills 1024x1024 (fuente de los vídeos) se guardan en
`~/Imágenes/wallpapers/.stills/` — carpeta oculta, el picker la ignora — para no
depender de `/tmp` ni volver a gastar neuronas si hay que re-encodear.




## 2026-11-18 — F9.5a: la tarjeta fija (HUD)

El tablero era "abrir y mirar". Ahora hay una tarjeta que se queda en el
escritorio: rol, fragmentos, racha, la sesion abierta con su reloj y **tres
barras** (meta del dia, proyecto, racha de 7 dias), mas las 3 tareas siguientes.

### Por que GTK3 y no GTK4 como el tablero

`libgtk-layer-shell` solo existe compilado para GTK3 en esta maquina
(`GtkLayerShell-0.1.typelib`). Con GTK4 habria sido una ventana flotante y reglas
de Hyprland a mano; con GTK3 es una **capa de Wayland de verdad**: anclada arriba a
la derecha, sin foco de teclado (`KeyboardMode.NONE`), sin empujar nada
(`exclusive_zone 0`). Se comparte casi toda la libreria con waybar y swaync, asi
que el coste real es de 24 MB PSS, no los 58 MB de RSS.

### El socket de eventos de Hyprland no emite nada

Verificado con `socat` y con `socket` crudo: **cero bytes** al cambiar de
workspace o de monitor, ni suscribiendose con `all`. Por eso el HUD mira el
estado cada 12 s con dos `hyprctl` (monitor con foco y ventana activa). Cuesta
0,07 % de un nucleo en total, medido con el contador de `/proc`.

Dato util para el futuro: en esta config Lua `hyprctl dispatch` **evalua Lua**.
`hyprctl dispatch focusmonitor eDP-1` falla; hay que escribir
`hyprctl dispatch 'hl.dsp.focus({monitor="eDP-1"})'`.

### Detalles que hubo que resolver

| Problema | Solucion |
|---|---|
| GDK no da el nombre del conector (`eDP-1`), da el modelo EDID (`0x323C`) | emparejar monitores por geometria (`x`, `y` / escala) |
| `gtk-layer-shell` fija la salida al crear la superficie | ocultar, `set_monitor`, mostrar: la tarjeta salta al monitor con foco |
| Ocultar en pantalla completa | `activewindow.fullscreen != 0` -> `hide()`; al salir vuelve |
| Mostrar/ocultar a mano | `ql-hud-toggle` manda `SIGUSR1` al pid de `$XDG_RUNTIME_DIR` |

### Medido

| Metrica | Resultado |
|---|---|
| RSS / PSS | **58 MB / 24 MB** |
| CPU en reposo | **0,07 %** de un nucleo |
| Robo de foco | ninguno: la ventana activa sigue siendo la misma tras dos toggles |
| Seguir al monitor | `HDMI-A-1` <-> `eDP-1` verificado |
| Pantalla completa | 0 superficies dentro, 1 al salir |
| Tests | **47 / 47** (6 nuevas sobre `hud.json`) |

Waybar suma ahora `▣N` (tareas abiertas) a la misma linea, sin procesos extra. Y
ya no desaparece cuando no hay modo activo: si hay algo que contar, el modulo
sigue ahi con la clase `off` (sin color de modo).
El autostart va en `user_startup.lua` y el bind `SUPER+ALT+SHIFT+H` en
`user_keybinds.lua` (ambos con backup); **el bind necesita un reload** que no he
hecho: la tarjeta ya esta corriendo, pero la tecla aparece tras recargar.

### El bug que dejo la tarjeta invisible

Tras el reload la capa desaparecio. Causa: para mover la tarjeta de monitor hay
que `hide()` + `set_monitor()` + `show_all()`, pero `apply_visibility()` salia
antes por la guarda `if hidden == self.hidden: return` — el estado decia
"visible" y nunca volvia a mostrarla. Ahora acepta `force=True` y la primera
colocacion de monitor lo usa. Segunda leccion: una prueba aislada con `Gtk`
sin `require_version` carga GTK4 y hace fallar el import de `hud.py`; el orden
correcto es el que ya usa el fichero.

Estado final: **1 instancia**, capa en el monitor con foco, toggle y fullscreen
OK, **58 MB RSS · 0,05 % de un nucleo**.

Siguiente: F9.5b (avisos al cerrar tarea) y F9.5c (hitos + splash).

## F9.5b - Avisos al cerrar tarea (2026-11-18)

`ql done <id> --notify` publica un aviso por tarea cerrada. El tablero ya lo
manda al tildar; el CLI sigue callado sin el flag (los tests no ensucian la
sesion).

| Decision | Por que |
|---|---|
| Un solo `gdbus call`, sin `notify-send` | un proceso menos y el mismo id de burbuja |
| Id fijo `9170` | un grupo nuevo reemplaza al anterior en pantalla, no se apilan |
| Agrupacion por fichero (`notify.json`) | agrupar sin dejar ningun proceso vivo |
| Ventana de **5 s** | dos cierres seguidos se leen como uno: `2 tasks closed · +20 FRG` |
| Fallo del daemon silencioso | cerrar la tarea nunca depende del aviso |

Contenido: titulo `+10 FRG · gallery` y cuerpo con el texto de la tarea y
`N/60 FRG today`; con varias, lista de hasta 3 y `+N more`.

Tests: **58 / 58** (11 nuevas: silencio sin flag, reopen no avisa, tarea ya
cerrada no avisa, titulo, cuerpo, agrupacion de dos, fichero de grupo y
reinicio tras 60 s). Ruta real verificada con una burbuja de prueba enviada y
cerrada por DBus.

Siguiente: F9.5c (hitos + splash).

## F9.5c - Hitos y splash (2026-11-18)

Cuatro disparadores, un evento `milestone` por hito y una medalla que aparece
6 s. La clave del evento lleva la identidad (proyecto, inicio de racha, inicio
de sesion), asi que un rebuild no repite nada.

| Disparador | Clave | Medalla |
|---|---|---|
| 5 tareas del mismo proyecto en una sesion | `chain:<proyecto>:<inicio>` | Zoso |
| Proyecto al 100 % con >= 10 tareas | `project:<nombre>` | Icaro (Swan Song) |
| Racha 7 / 14 / 30 | `streak:<dias>:<inicio racha>` | Obelisco (Presence) |
| Semana perfecta (cada 7 dias) | `week:<dia>` | Ermitaño (IV) |

`ql milestones` lista los ganados. El splash (`splash.py`, symlink
`ql-splash`) es una capa overlay, teclado desactivado, centrada en el monitor
del puntero: popup de 300 ms con rebote, 6 s en pantalla, clic para cerrar.

| Metrica | Resultado |
|---|---|
| Posicion | 740,350 en HDMI-A-1 (440x380, centrada) |
| Foco | la ventana activa sigue siendo la misma |
| CPU | 0 % durante los 5 s de espera (solo dibuja al animar) |
| Render | una vez a un `ImageSurface`; cada frame es un blit |
| RSS | 57 MB mientras dura (6 s) |
| Tests | **69 / 69** (11 nuevas) |

El primer intento centraba mal: las margenes se calculaban con la geometria de
otro monitor y ademas se le sumaba `geom.x`; con `set_monitor` + geometria de
ese mismo monitor queda centrada. Tambien se bajo el coste: 60 fps dibujando
todo el rato -> 20 frames y un solo render cacheado.

Pendiente visual tuyo: `/tmp/opencode/splash-shot.png` (captura del emblema
Icaro). El pixel-art real llega en F9.6 y sustituye el dibujo sin tocar el
disparador.

Siguiente: F9.6 (emblemas pixel-art + pipeline de generacion).

## F9.5d - Emblemas pixel-art (2026-11-18)

Pipeline completo, sin instalar nada que tu no elijas. Documento de metodo:
`docs/subsystem/EMBLEMS.md`.

| Pieza | Estado |
|---|---|
| `ql-emblem prompt <proyecto>` | imprime el brief de 2 colores, elige glifo por hash y limita a 1 generacion diaria |
| `ql-emblem draw <proyecto>` | 3 candidatos gratis con Cairo, 128 px -> 512 px con pixeles 4x4 duros |
| `ql-emblem pick <proyecto> <n>` | valida PNG, cuadrado, tamano, area opaca y **exactamente 2 colores**; instala en `Vault/Questline/emblems/` |
| `ql-emblem status` | glifo, fichero y fecha |
| Splash | usa el PNG con escalado nearest; sin PNG vuelve al glifo Cairo |

El modelo de imagen que tengo configurado respondio **saldo insuficiente**
(pago por uso), asi que los 3 candidatos de `hyprland` salieron del renderer
local: `/tmp/questline-emblems/hyprland-{1,2,3}.png`, 512x512, 2 colores, 61/61/55 %
opaco. El prompt queda guardado y se puede usar en un generador gratuito cuando
quieras arte mas rico.

Validacion: 2 colores detectados leyendo los pixeles con Cairo; una imagen con
antialiasing o un tercer color se rechaza. Tests: **80 / 80** (11 nuevas).

Pendiente: que elijas candidato (`ql-emblem pick hyprland <1|2|3>`).

Actualizacion: elegiste el **candidato 3** (medalla octogonal) y ya esta en
`~/Documentos/Vault/Questline/emblems/hyprland.png`; el splash lo pinta con
escalado nearest. Captura real: `/tmp/opencode/splash-hyprland-shot.png`.
Cuando haya un servicio de imagen con plan free, se vuelve a lanzar el prompt
guardado y se elige de nuevo: `ql-emblem prompt hyprland --force`, 3 candidatos,
`pick` y listo.

## F9.6 - El metodo (2026-11-18)

Scrum/Kaizen dentro del log: todo son eventos, sin base de datos ni daemon.

| Pieza | Que hace |
|---|---|
| `ql sprint start --projects a,b` | ventana con id de semana ISO, 7/14/21 dias, tareas abiertas comprometidas |
| `ql sprint status [--json]` | dia N/M, `commit · done · open · carried` |
| `ql sprint close` | cierra y deja las abiertas como `carried` para el proximo `start` |
| `ql review [--days 7]` | tabla de minutos por modo, tareas, FRG y **una** sugerencia de experimento |
| `ql kaizen start/end/list` | hipotesis + metrica con `baseline → value`, guardado como evento |
| `nudge` | un aviso al dia en el primer `mode.start` con sprint activo; clave `(dia, dispositivo)` |

La sugerencia del review mira primero el arrastre, luego el proyecto con mas
abiertas, luego los modos sin sesion y, si no hay nada, propone mantener el ritmo
con un Kaizen. El nudge no usa temporizador: se dispara en la transicion y por
eso sobrevive a un rebuild y no se duplica al sincronizar.

| Verificacion | Resultado |
|---|---|
| Tests | **92 / 92** (12 nuevos: sprint, review, kaizen, nudge) |
| Escritura | solo `Vault/Questline/sprint.json` y eventos `kaizen`/`nudge` |
| Invariantes | sin daemon, sin polling, sin red, sin paquetes nuevos |

Docs: `BACKLOG` (QL-601..604), `README` (+ Method), `SPEC`, `RULES`,
`Checklist`. Sin residuos.

Siguiente: F9.5 (sellos y regalos) o F9.7 (tablero HTTP por Tailscale).

## F9.5 - Sellos y regalos (2026-11-18)

24 sellos en 3 familias de 8: milestone, streak y Kaizen. Cada criterio es una
funcion pura sobre el log (`stamps.py`), asi que un rebuild no repite nada y dos
dispositivos no pueden discrepar. Un evento `stamp` por id; un aviso por lote
(id 9171, distinto del de tareas).

| Pieza | Estado |
|---|---|
| `ql stamps [--json]` | ganados, reclamados y pendientes |
| `ql claim <id>` | evento `gift.claim`, PNG 640x360 + MD en `Vault/Questline/gallery/`, cosmético `✦N` en waybar y HUD |
| Idempotencia | un segundo claim no escribe nada; borrar el PNG no revoca el regalo |
| Generacion | solo dentro de `ql claim`; Cairo local, sin modelo y sin red |
| Metodo | `docs/subsystem/GIFTS.md` |

| Verificacion | Resultado |
|---|---|
| Tests | **106 / 106** (14 nuevos) |
| Antes del claim | directorio `gallery/` inexistente: cero generacion |
| Claim real | PNG 640x360, 2 colores, MD con el id; `✦1` en `line` |
| Rebuild | no re-emite sellos; el segundo claim deja un solo evento |

Docs: `BACKLOG` (QL-501..503), `README` (+ Stamps and gifts), `SPEC`, `RULES`,
`Checklist`. Sin residuos.

Siguiente: F9.7 (tablero HTTP por Tailscale).

## Decision: F9.7 diferido (2026-11-18)

El usuario decidio dejar F9.7 como **opcional y no prioritario** por los riesgos
de exponer el tablero y de tocar firewall/Syncthing. Los items `QL-701..704`
quedan abiertos, sin implementar, y requieren aprobacion explicita antes de
cualquier cambio de sistema. Registrado en `BACKLOG`, `SPEC` y `Checklist`.

Siguiente a evaluar: F9.8 (servidor MCP por stdio).

## F9.8 - Agentes, enlaces y lanzador (2026-11-18)

`ql-mcp` es un servidor MCP por stdio: una linea JSON entra, una sale. Sin
socket, sin puerto, sin daemon, sin red y sin paquetes nuevos; `stdout` solo
lleva el protocolo y los diagnosticos van a `stderr`. Expone `board`, `status`,
`done` y `add_task`, con `initialize` y `tools/list` para descubrimiento.

| Pieza | Estado |
|---|---|
| `mcp.py` + symlink `~/.local/bin/ql-mcp` | 4 herramientas; `done` idempotente, `add_task` escribe sin puntos |
| `ql add ... --link` | checkbox con `^ql-…` estable, `#project/x` y `[[wikilinks]]`, backup + escritura atomica |
| `ql scan` | guarda `links`; `board`/MCP los devuelven; texto visible sin etiquetas ni links |
| QL-802 | `~/.local/share/applications/questline.desktop` abre `ql-board` desde rofi/fuzzel |
| Identidad | el block id manda; los wikilinks son navegacion, no clave (Obsidian calcula backlinks) |

| Verificacion | Resultado |
|---|---|
| Tests | **119 / 119** (13 nuevos: add, links, MCP, idempotencia) |
| Seguridad | nota fuera del vault, symlink y carpetas excluidas rechazadas |
| Protocolo | respuesta por linea, error JSON para herramienta desconocida, sin crash |

Docs: `BACKLOG` (QL-801..803), `MCP.md`, `README`, `SPEC`, `RULES`, `Checklist`.
Sin residuos.

Siguiente: F9.7 sigue diferido; F9.8 cerrado.

## 2026-11-18 — F10 voice-bridge (prototipo)

Se implemento el modulo de voz para OpenCode: `pw-record` 16 kHz mono, Groq
Whisper en espanol, MCP stdio con 4 herramientas y push-to-talk global
`SUPER+ALT+SHIFT+V` (pulsar/soltar). La transcripcion entra al composer por el
PTY de kitty, con portapapeles como respaldo. Sin modelo local y sin TTS aun.

Decisiones: repo publico **ZeePhyNux** (el alias `zeep` queda para el subsistema
Questline), atajo A para no colisionar con binds existentes, y respuesta en audio
diferida a la validacion. `GROQ_API_KEY` solo por entorno.

Verificacion: 12 tests offline, JSON validado con `jq`, Lua validado con
`luac -p`, skill y comando descubiertos por OpenCode tras recargar config.
Pendiente: validacion con microfono real (la key no esta exportada en esta sesion)
y creacion del remoto GitHub (`gh` devuelve 401; requiere reautenticacion).
