# Checklist - Debian_Hyprland_Look_And_Feel

## F0 - Base
- [x] Leer vault y auditar sistema

## F1 - Decorations
- [x] Blur = off, opacidad = 0.85 (backup ok)

## F2 - Fuentes
- [x] Fuentes instaladas, kitty reparado a JetBrainsMono Nerd Font

## F3 - Galería
- [x] Estructura creada + TerminalGallery.sh + fish hook
- [x] Pool: 27 assets genéricos -> hoy 45 (21 del usuario + 22 de IA, ver F7)
- [x] TerminalGallery.sh: 3 bugs corregidos (mapfile, stty size, timeout) — verificado
- [x] Banner reescrito: icat --place mueve el cursor, geometría por proporción real, bloque de H líneas + separador
- [x] Causa de "no se ve la imagen": marcadores /tmp obsoletos (kitty reutiliza ids) + umbral COLS>=60
- [x] Modo apilado para ventanas < 60 columnas (imagen arriba, texto debajo)
- [x] Diagnóstico: /tmp/termgal-last.log (una línea por ventana)
- [x] Imagen ajustada a caja 2D (55% ancho / 60% alto, tope 22 filas): se adapta a la forma de cada ventana
- [x] Texto centrado verticalmente contra la imagen + separador, sin desbordes (44 combinaciones probadas)
- [x] Ctrl+L recompone el banner al tamaño actual (imagen forzada, sin repetir selección)
- [x] F3 CERRADA — validación visual del usuario 2026-11-13: estructura, imagen por ventana y Ctrl+L tras redimensionar

## Fase B - Auditoria de wallpapers
- [x] Inventario completo (65 mp4, 2 estaticas, 11 temas)
- [x] AUDITORIA_WALLPAPERS.md con tabla archivo->estado y 8 hallazgos con evidencia
- [x] Posters regenerados y uniformados: 63/63 PNG 1366x768 exactos al frame 2s (backups en quarantine)
- [x] 4 archivos movidos a _reemplazar/ (2 estaticas + 2 duplicados); posters huerfanos a cuarentena
- [x] Decision: 08-codigo queda como excepcion declarada (texto por diseno)
- [x] Decision sobre el criterio "sin IA": aceptada la IA generativa (open source o plan free, sin carga local)
- [ ] Reemplazos de video: 5 en 12-Akira (carpeta vacia) y 2 en 10-bandas (acid-bath-crt, system-of-a-down-caotico)
  - [x] Duplicados resueltos: se movio 1 archivo de cada pareja a _reemplazar/
  - [ ] Stills de IA (5 Akira + 2 bandas) en /tmp/opencode/wall
  - [ ] Muestra de 3 s aprobada por el usuario
  - [ ] Codificar 7 videos 1366x768 / 30 fps / 15 s + posters en .posters/
  - [ ] Mover los 2 originales a _reemplazar/ y actualizar AUDITORIA_WALLPAPERS.md

## Fase D - Buzon de assets
- [x] galeria/_inbox/ + dudas/ + LEEME.md con instrucciones
- [x] GalleryIntake.py (antes clasificaba por personajes_mapeo.json —retirado—, normaliza a PNG <=512, registra en ASSETS_TRACKER.md)
- [x] Probado con 3 archivos sinteticos: 2 clasificados, 1 a dudas, tracker actualizado
- [x] Enrutado por categoria cuando no hay personaje (sticker/meme/gift/personaje -> aportes--<slug>) - probado con 5 sinteticos
- [x] Imagenes del usuario ingeridas: 21 el 2026-11-18; el buzon ya no espera nada
- [x] Base simple 2026-11-19: retirados 3 PNG sueltos, personajes_mapeo.json y 2 copias .bak; sin mapas de personajes, cada persona aporta su propia personalizacion
- [x] Criterio IA: aceptada si es codigo abierto o plan free y no consume recursos locales (2026-11-15)
- [x] Proveedor elegido: Cloudflare Workers AI FLUX.1 schnell (~230 img/dia gratis, Apache-2.0)
- [x] GalleryGen.py + README + prompts.txt en herramientas/gallery-gen/ (dry-run y lotes reales OK)

## Fase E - Gamemode (7 modos)
- [x] Devmode + Planingmode (2026-11-12)
- [x] Readmode (luz 3800K + DND) y Writemode (luz 5200K + DND + cierra avisos)
- [x] Toggle generico + exclusion mutua entre todos los modos con marcador
- [x] Keybinds SUPER+ALT+SHIFT+R / SUPER+ALT+SHIFT+W (aplicados en caliente, sin duplicados)
- [x] GameDevmode (wallpaper congelado + DND) y 3Dmode (idem, color exacto)
- [x] AudioVisualmode (PipeWire 128 + wallpaper congelado + DND)
- [x] Los 7 modos existen y son mutuamente excluyentes (barrido verificado)
- [x] Indicador de modo en waybar (custom/gamemode, texto + tooltip + color por modo)
- [x] Confirmacion visual del indicador por el usuario
- [ ] Roles/tesoros/recompensas/puntos: en planificacion (ver ROLES_Y_TESOROS.md)

## F4 - Waybar
- [x] Cambiar a [BOT] Simple + Monochrome (restaurado, waybar restarted OK)
- [x] Hibrido opcion B sobre [TOP] Default Laptop: 7.0% -> 4.35% CPU, cava eliminado, mpris en vez de playerctl -F, grupo mobo_light propio
- [x] Confirmacion visual del usuario (orden y anchos del lado derecho)

## F5 - Gamemode (empezar 2 modos)
- Fusionado con Fase E: los cinco items de esta seccion eran duplicados. Se conserva la historia en la Bitacora.

## F6 - Perfil energetico de los modos (2026-11-15 / 18)
- [x] Helper root minimo: gobernador + techo de frecuencia (iGPU rechaza DPM en Kaveri)
- [x] Sudoers acotado por verbo exacto (instalado por el usuario)
- [x] Enganche en gamemode_common.sh + gamemode_toggle.sh (probado con Readmode)
- [ ] Reinstalar helper + sudoers actualizados (verbo restore) - PENDIENTE, requiere la contrasena del usuario
- [x] Cuenta y token de Cloudflare con permiso Workers AI; dos lotes lanzados (ver F7)

## F7 - Galeria: primer lote real e IA (2026-11-18)
- [x] Ingesta del primer lote: 21 imagenes (13 anime + 8 manga), 0 dudas, 21 originales en procesados/
- [x] Clasificador con segunda pasada por serie (blame -> manga/blame--generico)
- [x] GalleryGen.py --check diagnostica revocado / sin permiso / cuenta ajena
- [x] Token de Cloudflare con permiso Workers AI (verify 200 + models 200)
- [x] Primer lote de IA: 5 imagenes (stickers x2, meme, gifts, personaje) con --intake
- [x] Fix 400 de FLUX (no acepta width/height; devuelve 1024x1024)
- [x] Tracker con cabecera y procedencia real (--origen)
- [x] Duplicados blame_v*.jpg de personaje/ movidos a cuarentena
- [x] Lote 2: capa de contexto (BASE + CONTEXTOS) y 17 imagenes nuevas - galeria en 45
- [x] series/ y juegos/ en CATS (estaban a 0 y no eran enrutables)
- [ ] Revisar los dos lotes en kitty (Ctrl+L) y ajustar prompts si hace falta

## F8 - Wallpapers con IA (2026-11-18)
- [x] `--estilo` en GalleryGen.py para reemplazar la capa pixel-art por la de wallpaper
- [x] 7 stills 1024x1024 generados en `/tmp/opencode/wall` (5 Akira + 2 bandas)
- [x] Muestra de 3 s: `muestra-akira-3s.mp4` (1366x768, 30 fps, yuv420p, 203 KB)
- [x] Aprobacion visual de la muestra -> codificar los 7 (15 s) y publicar
- [x] Posters en `.posters/<tema>/` (creado `.posters/12-Akira/`)
- [x] Medir el coste real de CPU del encode y anotarlo en la Bitacora
- [x] Originales de 10-bandas movidos a `_reemplazar/10-bandas/` (sin borrar)

## F9 - Questline (subsistema de escritorio, 2026-11-18)
- [x] FU9.0 Especificacion: `docs/subsystem/SPEC.md`, `RULES.md`, `BACKLOG.md` (ingles)
- [x] FU9.1 Nucleo: log de eventos, fold puro, CLI `ql`, hook en los 7 modos
- [x] FU9.1 17 comprobaciones en `herramientas/questline/tests/smoke.py`
- [x] Vault creado en `~/Documentos/Vault` (+ `Questline/` visible para sincronizar)
- [x] F9.2 Escaneo de Obsidian: checkboxes, block IDs, cache por mtime (32 tests, 300 notas en 0,52 s)
- [x] F9.3 Contador en waybar (FRG / racha / rol) + indicador 12x mas barato
- [x] F9.4 Tablero GTK4 (`ql-board`) + `ql done` tilda la casilla del vault
- [x] F9.4 Keybind `SUPER+ALT+SHIFT+B` activo tras reload (verificado en `hyprctl binds`)
- [~] F9.4 Socket Unix aplazado: exigiria un daemon (invariante 8) hasta que haya cliente movil/agente
- [x] F9.5a Tarjeta fija (HUD GTK3 layer-shell): rol, barras, reloj de sesion, 3 tareas
- [x] F9.5a Waybar suma `▣N` (tareas abiertas) en la misma linea
- [x] F9.5a Sigue al monitor con foco, se oculta en fullscreen, `SUPER+ALT+SHIFT+H` (tras reload)
- [x] F9.5b Avisos agrupados al cerrar tarea (11 tests, burbuja unica por grupo de 5 s)
- [x] F9.5c Hitos + splash (4 disparadores, evento `milestone`, medalla Cairo con glifo Zep, 11 tests)
- [x] F9.5d Emblemas pixel-art: `ql-emblem` prompt/draw/pick/status, splash lee el PNG, 80 tests
- [x] F9.5d Elegir candidato de emblema para `hyprland` (1/2/3) e instalarlo
- [x] F9.5d Instalado el **candidato 3** (octogonal) en `Vault/Questline/emblems/hyprland.png`
- [x] F9.5 24 sellos + flujo de regalo (claim idempotente, PNG 640x360, `✦N`, 106 tests)
- [x] F9.6 Sprint, daily nudge, review semanal y experimentos Kaizen (92 tests)
- [ ] F9.7 Tablero HTTP por Tailscale + Syncthing en el HUAWEI Y9 2019 — **opcional/diferido por riesgo (no prioridad)**
- [x] F9.8 Servidor MCP stdio + `ql add` con wikilinks + lanzador rofi/fuzzel (119 tests)

## F10 - Voice Bridge (prototipo)
- [x] Modulo `herramientas/voice-bridge/` (MCP + CLI + rules + skill + comando)
- [x] Push-to-talk `SUPER+ALT+SHIFT+V` press/release (backup + `luac -p`, sin reload)
- [x] Cloudflare Whisper por defecto (Groq descartado: `signup_blocked`)
- [x] Entrega por PTY de kitty con fallback a portapapeles
- [x] Plugin TUI `Ctrl+Alt+V` (clipboard -> `prompt.paste` -> `input.submit`)
- [x] MCP con 5 tools: `listen`, `transcribe`, `last`, `languages`, `speak`
- [x] Backoff 429/5xx + `[api]` en `rules.toml` + toast amigable
- [x] STT local Vosk en Docker (one-shot, `--network none`, es/en, sin credenciales)
- [x] Imagenes construidas en local: `voice-bridge-vosk-es:0.42` / `-en:0.15` (lgraph descartado: 3m55/24s; ES grande descartado: 4,24 GB RAM y 118s/24s)
- [x] `vosk==0.3.45` fijado (0.3.50 no existe para Python 3.12 en PyPI)
- [x] Estructura del repo: README, `.gitignore`, `docker/`, `tests/fixtures/`
- [x] 47 tests offline (sin red, microfono ni secretos)
- [x] Atajos documentados en `KeyHints.sh` y menu rofi (7 modos + voz + Questline)
- [x] Transcripcion real en español validada (WAV de 21,8 s, sin red)
- [x] Imagen Vosk es/en cargada y probada (falta muestra de voz en ingles real)
- [x] Whisper local `base` integrado como default (int8, 4 hilos, beam 5, VAD; venv y cache en `/home`)
- [x] `faster-whisper==1.2.1` + `av==14.4.0` fijados (`av==19` fallo verificado)
- [x] Whisper `small` evaluado y descartado (~46 s vs ~24 s de `base`; ~653 MB RAM)
- [x] Transcripcion real con Whisper `base` validada en WAV de 24,23 s (reconoce `OpenCode` y `comunicarse mediante voz`)
- [x] Validacion final del dictado por el usuario (2026-11-20): acepto Whisper `base` pese a errores parciales (`OpenCop` por `OpenCode`)
- [x] TTS local con Piper `1.8.0` como default (venv y voces en `/home`, sin paquetes del sistema)
- [x] Voces Piper oficiales `es_ES-davefx-medium` / `en_US-lessac-medium` descargadas y reproducidas con `pw-play`
- [x] Cloudflare TTS queda como fallback explicito (`[tts].provider = "cloudflare"`)
- [ ] `ql-ffe4bea3`: activacion manos libres «oye, zeep»

## F11 - Modulo documental (fases 0-5 completadas)
- [x] Aprobacion del administrador para fases 2-4 y fase 5 condicionada (2026-11-20)
- [x] Investigacion A: PDF sin LibreOffice (ReportLab / WeasyPrint / Pandoc)
- [x] Investigacion B: DOCX (Pandoc frente a python-docx)
- [x] Investigacion C: XLSX y CSV (openpyxl + csv, sin Pandas)
- [x] Investigacion D: skills de OpenCode y skill `document-workflow`
- [x] Investigacion E: sistema de plantillas reutilizables
- [x] Disenar contratos de entrada/salida y directorio de entregables por proyecto
- [x] Instalar Pandoc 3.14 estatico y venv con ReportLab 5.1.0 / openpyxl 3.1.5 en `/home`
- [x] Implementar skill y validar entregables sinteticos DOCX/PDF/CSV/XLSX
- [x] Validacion del usuario con entregables de prueba (2026-11-20); pulido de diseno diferido
