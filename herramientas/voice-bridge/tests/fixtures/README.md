# Fixtures

No se guarda audio real en este repositorio.

`tests/smoke.py` genera un WAV sintético (1 segundo, 16 kHz, mono, s16) en un
directorio temporal en cada ejecución. Esto mantiene las pruebas deterministas
y evita que voces reales o grabaciones del micrófono terminen versionadas.

Para una prueba real, usa `python3 voicectl.py listen --seconds 3`: el WAV queda
en `~/.local/state/voice-bridge/capture.wav`, fuera del repo y cubierto por
`.gitignore`.
