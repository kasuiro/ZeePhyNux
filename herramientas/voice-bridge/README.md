# voice-bridge

Accesibilidad por voz para los agentes de OpenCode en Debian 13 / Hyprland /
Wayland. **Todo el circuito de voz es local por defecto**: `faster-whisper`
(modelo `base`, int8) convierte el WAV en texto y Piper sintetiza las respuestas;
cada uno corre en su propio venv dentro de `~/.local/state/voice-bridge/`.
No hay cupo de tokens ni credenciales para dictar ni para hablar.

Vosk en Docker sigue disponible como alternativa local, y los proveedores en la
nube (Cloudflare, Groq) como opción explícita, pero ya no son el camino principal.

## Estado

- STT local Whisper `base` (es/en, detección automática) como proveedor default.
- STT local Vosk (es/en) disponible con `[stt].provider = "vosk"`.
- TTS local Piper `1.8.0` (es/en) como default; Cloudflare Aura-2 queda como fallback.
- PTT `SUPER+ALT+SHIFT+V` y plugin TUI `Ctrl+Alt+V`.
- Activación manos libres por sesión: «oye, zeep» / «oye, linux zeep».
- 62 pruebas offline, sin red, micrófono ni credenciales.

## Estructura

```
rules.toml              defaults; nunca guarda credenciales
voicectl.py             CLI: capture / transcribe / deliver / speak / wake-*
mcp.py                  servidor MCP stdio: listen, transcribe, last, languages, speak
wake.py                 helpers puros de frase de activación
wake_listener.py        listener por sesión: PCM crudo + Whisper sesgado
plugin/tui.js           plugin TUI de OpenCode (Ctrl+Alt+V)
commands/voice.md       comando /voice de respaldo
skill/SKILL.md          vocabulario y reglas de voz para el agente
requirements.txt        TTS local Piper, fijado
whisper_transcribe.py   worker local: WAV → JSON (corre en el venv)
tools/install-whisper.sh  crea el venv de STT en ~/.local/state, nunca en el repo
tools/install-piper.sh    crea el venv de TTS y descarga las voces es/en
docker/
  Dockerfile            imagen Vosk (ARG de modelo, sin secretos)
  .dockerignore         excluye WAV/JSON/estado del contexto de build
  requirements.stt.txt  vosk fijado
  transcribe.py         WAV → JSON por stdout
  build.sh              construye las imágenes es y en
tests/
  smoke.py              47 pruebas offline
  fixtures/             WAV sintético, nunca voz real
.gitignore              estado, audio, logs y plugin-load.json
```

## Requisitos previos

- Python 3.13 en el host (sin paquetes de terceros).
- `pw-record` / `pw-play` (PipeWire) para captura y reproducción.
- Para Whisper (default): el venv se instala con el script de abajo; los modelos
  se descargan una sola vez a `~/.local/state/voice-bridge/whisper/hf`.
- Para Piper (default TTS): el script de abajo instala `piper-tts==1.8.0` y las
  voces `es_ES-davefx-medium` / `en_US-lessac-medium` (63 MB c/u) en
  `~/.local/state/voice-bridge/piper/`.
- Para Vosk (opcional): Docker con `data-root` en `/home` (en este equipo:
  `/home/dev/ia_local/docker_data_root`, definido en `/etc/docker/daemon.json`).
  **Nunca se construye ni se ejecuta nada desde `/`**.

## Instalación del STT local (Whisper)

```sh
cd herramientas/voice-bridge
./tools/install-whisper.sh
python3 voicectl.py status
python3 voicectl.py transcribe /home/dev/.local/state/voice-bridge/capture.wav
```

El script fija `faster-whisper==1.2.1` y `av==14.4.0` (con `av==19` falla en
este equipo). Todo queda bajo `~/.local/state/voice-bridge/whisper/`, fuera del
repo. No instala paquetes del sistema.

## Instalación del TTS local (Piper)

```sh
cd herramientas/voice-bridge
./tools/install-piper.sh
python3 voicectl.py speak 'Hola, esta es una prueba local.' --no-play
python3 voicectl.py speak 'Listo, Piper funciona.'
```

Las voces oficiales `es_ES-davefx-medium` y `en_US-lessac-medium` se descargan
desde `rhasspy/piper-voices` (fuentes y licencias verificadas el 2026-11-20).
`[tts].provider = "piper"` es el default; para volver a Cloudflare basta cambiar
ese valor a `"cloudflare"` (requiere credenciales). No se instala `espeak-ng`
en el sistema: Piper lo incorpora para la fonemización.

## Construcción de las imágenes Vosk (opcional)

El `data-root` ya está configurado; compruébalo antes de construir:

```sh
docker info --format '{{.DockerRootDir}}'
```

Debe empezar por `/home`. Si no, **no construyas**: pide revisión del
administrador del sistema.

```sh
cd herramientas/voice-bridge/docker
./build.sh
```

`build.sh` crea:

| Imagen | Modelo | Idioma |
|---|---|---|
| `voice-bridge-vosk-es:0.42` | `vosk-model-small-es-0.42` | español |
| `voice-bridge-vosk-en:0.15` | `vosk-model-small-en-us-0.15` | inglés |

Los modelos se descargan durante el build (~39 MB es). El `Dockerfile` no
incorpora credenciales ni audio. Las etiquetas `org.opencontainers.image.*`
vinculan la imagen con el repositorio.

GHCR (GitHub Container Registry) está previsto **solo como publicación futura**,
después de la validación y con criterios de aceptación aprobados. El empuje
manual requiere un token clásico con `write:packages`; no se usa todavía.

## Uso

`[stt].provider` en `rules.toml` admite:

| Valor | Origen | Credenciales |
|---|---|---|
| `whisper` (default) | venv local, modelo `base` int8 | ninguna |
| `vosk` | contenedor local | ninguna |
| `cloudflare` | Whisper hospedado | `cf_token` + `cf_account` (0600) |
| `groq` | Whisper hospedado | `key` (0600) o `GROQ_API_KEY` |

`[tts].provider` admite:

| Valor | Origen | Credenciales |
|---|---|---|
| `piper` (default) | venv local, voz `es_ES-davefx-medium` / `en_US-lessac-medium` | ninguna |
| `cloudflare` | Aura-2 hospedado | `cf_token` + `cf_account` (0600) |

Los archivos de credenciales se leen en cada petición; OpenCode no necesita
reinicio. **Nunca** se escriben secretos en el repo ni en logs.

Comandos:

```sh
python3 voicectl.py status
python3 voicectl.py start                 # pulsar: empieza a grabar
python3 voicectl.py stop                  # soltar: transcribe y entrega
python3 voicectl.py listen --seconds 5
python3 voicectl.py transcribe archivo.wav
python3 voicectl.py last
python3 voicectl.py speak "Probando audio"
python3 voicectl.py wake-start              # activar «oye, zeep» por sesión
python3 voicectl.py wake-stop               # apagar el listener
python3 voicectl.py wake-dictate            # dictado por silencio (usan el trigger)
```

Flujo:

```
tecla abajo -> pw-record 16 kHz mono -> tecla arriba -> WAV
            -> whisper_transcribe.py (venv local) -> JSON
            -> last.txt -> PTY de kitty / portapapeles -> OpenCode -> Enter
            -> respuesta -> piper (venv local) -> pw-play

TUI:  Ctrl+Alt+V -> grabar -> Ctrl+Alt+V -> portapapeles -> prompt.paste
```

Manos libres: `wake-start` -> «oye, zeep» -> Piper «Escuchando» -> dictado
hasta silencio -> Whisper -> PTY o portapapeles -> Enter -> `wake-stop`.

El agente también puede iniciar un turno con `voice_listen(seconds: 8)`.

## Idiomas

`[stt].language = "auto"` deja que Whisper detecte es/en; también se puede fijar
`es` o `en`, o pasar `language` como argumento de herramienta. Para TTS,
`[voice].language = "auto"` detecta el idioma del texto y elige la voz Piper
correspondiente; en textos mixtos conviene fijarlo explícitamente.

## Verificación

```sh
python3 tests/smoke.py                    # 62 pruebas, sin red
python3 voicectl.py status
docker info --format '{{.DockerRootDir}}'
node --check --input-type=module < plugin/tui.js
```

Para la prueba real con micrófono (requiere tu validación):

```sh
python3 voicectl.py listen --seconds 8
```

`listen` tiene una ventana fija y recorta si sigues hablando. Para frases largas
usa el PTT `SUPER+ALT+SHIFT+V` o el toggle `Ctrl+Alt+V` del plugin TUI: no tienen
límite de duración. El flujo manos libres (`wake-start`) usa fin por silencio con
tope duro de 30 s definido en `[wake]`; el listener es el único proceso de
escucha y solo vive durante la sesión (excepción aprobada en `RULES.md` 8).

## Privacidad y límites

- Whisper y Piper corren en local; el audio y el texto solo salen de la máquina
  si eliges un proveedor cloud. Tras la primera descarga, los modelos quedan en
  caché bajo `/home`.
- El contenedor Vosk corre con `--network none`: el audio **no sale** de la máquina.
- No se guarda audio real en el repo; `.gitignore` excluye `*.wav`, `*.mp3`,
  `state/` y `plugin-load.json`.
- En la muestra real de 24,23 s, Whisper `base` reconoció `OpenCode` y
  `comunicarse mediante voz`; Vosk small no. Whisper `small` fue más preciso pero
  tardó ~46 s de decodificación frente a ~24 s de `base` (int8, 4 hilos).
- Los modelos Vosk pequeños priorizan velocidad sobre precisión; se mantienen
  como alternativa, no como default.
- TTS local con Piper `1.8.0`: WAV en `reply.wav` del state dir, sin cupo ni
  credenciales. Voz ES `es_ES-davefx-medium` y EN `en_US-lessac-medium`; en la
  prueba real la síntesis tardó ~10 s y `pw-play` reprodujo el audio.
- Cloudflare Aura-2 sigue disponible como fallback explícito (`$0.03/1k chars`,
  MP3 en `reply.mp3`); su cupo puede agotarse, por eso no es el default.
- Rollback: cambiar `[stt].provider` a `cloudflare`/`groq`, o desactivar el
  servidor `voice` en `opencode.json`, quitar los dos binds de Hyprland y
  retirar la entrada del plugin en `cli.json`
  (backup: `cli.json.bak-20261119-voice-tui`).
