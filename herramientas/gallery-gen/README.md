# Generación de imágenes para la galería (IA, gratis, sin cargar la máquina)

Decisión registrada (2026-11-15): se acepta IA generativa **si** es de código
abierto o plan gratuito **y** no consume recursos de este equipo. Por eso aquí no
se ejecuta nada en local: el A10-7300 con 6.7 GB de RAM y HDD tardaría minutos
por imagen y calentaría de más.

## Proveedor elegido: Cloudflare Workers AI · FLUX.1 [schnell]

| Criterio | Dato | Fuente |
|---|---|---|
| Modelo | FLUX.1 [schnell], 12B parámetros, Apache-2.0 | página oficial del modelo |
| Precio | 4,80 neuronas por baldosa 512×512 + 9,60 por paso | tabla de precios |
| Coste real | ~43 neuronas/imagen (512², 4 pasos) | cálculo con la tabla |
| Plan Free | 10.000 neuronas/día → **~230 imágenes/día**, sin tarjeta | tabla de precios |
| Retención de datos | cero (`Zero data retention: Yes`) | página del modelo |
| Salida | JPEG en Base64 dentro de `result.image` | esquema de la API |
| Pasos | 1–8, por defecto 4 | esquema de la API |

Docs: <https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/>
Precios: <https://developers.cloudflare.com/workers-ai/platform/pricing/>

Por qué no los otros:

| Alternativa | Motivo |
|---|---|
| Pollinations (`sana`) | **Probado hoy: HTTP 402 Payment Required** desde esta máquina. La capa anónima ya no sirve imágenes; queda en el script solo como diagnóstico (`--provider pollinations`). |
| Difusión en local | 4 núcleos a 1.9 GHz, 6.7 GB, HDD: viola la condición de no consumir recursos. |
| SDXL en Workers AI | disponible, más lento y con peor adherencia al prompt que FLUX schnell. |

## Puesta en marcha (5 minutos, lo haces tú)

1. Cuenta gratuita en <https://dash.cloudflare.com/sign-up>.
2. En el panel: **Workers AI** → **Use REST API** → copiar el **Account ID**.
3. En esa misma pantalla, **Create a Workers AI API Token** → *Create API Token*
   → copiar el valor (solo se muestra una vez).

> Si creas el token a mano (**My Profile → API Tokens**), necesita **dos**
> permisos: `Account > Workers AI > Read` **y** `Edit`. Con solo uno la API
> responde `403 Authentication error`, aunque `/user/tokens/verify` diga que el
> token está activo y válido. Medido en esta máquina el 2026-11-18.
4. Exportar en la sesión (no se guardan en disco):

```bash
export CLOUDFLARE_ACCOUNT_ID="<account-id>"
export CLOUDFLARE_API_TOKEN="<token>"
```

Mejor aún, en `~/.config/fish/config.fish` con `set -Ux` si quieres que persista;
es decisión tuya, el script solo lee el entorno.

## Uso

```bash
cd ~/Documentos/Debian_Hyprland_Look_And_Feel/herramientas/gallery-gen
./GalleryGen.py --check                  # valida el token, no gasta neuronas
./GalleryGen.py --dry-run                # qué generaría, sin red
./GalleryGen.py                          # Cloudflare FLUX schnell
./GalleryGen.py --intake                 # generar y clasificar de una vez
./GalleryGen.py --prompts otros.txt --out-dir /tmp/prueba
```

`flux-1-schnell` devuelve **1024×1024 fijo** y rechaza `width`/`height` con `400`
(«Additional or unevaluated properties»). Por eso `--size` solo afecta a
`--provider pollinations`; el reescalado a 512 px para la galería lo hace
`GalleryIntake.py`. Si la petición falla, el error incluye el cuerpo de
Cloudflare, no solo «Bad Request».

`--intake` llama a `GalleryIntake.py` al terminar: la imagen pasa de `_inbox` a
su categoría sin pasos manuales.

Las imágenes caen en `galeria/_inbox/`. Después, el circuito de siempre:

```bash
~/.config/hypr/UserScripts/GalleryIntake.py --dry-run
~/.config/hypr/UserScripts/GalleryIntake.py
```

`--check` es la única llamada de red que no gasta neuronas. Distingue tres
fallos distintos: token revocado, token válido **sin** permiso de Workers AI, y
Account ID de otra cuenta. Las variables son universales de fish (`set -Ux`),
así que solo están en el entorno de procesos lanzados desde fish; desde bash hay
que envolver: `fish -c './GalleryGen.py --check'`.

## Contexto de prompt (la capa que se añade antes de llamar a la API)

Un prompt desnudo deja al modelo decidir escena, encuadre y fondo, y el resultado
se parece poco a lo pedido. Por eso `GalleryGen.py` compone siempre:

```text
<sujeto del prompts.txt>. <contexto de la categoría>. <BASE>
```

- `BASE` (todos): 16-bit, píxel duro, 12 colores, sombreado plano, sujeto
  centrado, fondo liso, sin texto ni marco.
- `CONTEXTOS` (por prefijo del nombre): `sticker`, `meme`, `gift`, `personaje`,
  `series`, `juegos`. Acepta los mismos sinónimos que `GalleryIntake.py`.
- El prompt final se imprime antes de cada petición, así que `--dry-run` enseña
  exactamente lo que se enviaría.

```bash
./GalleryGen.py --dry-run                 # ver el prompt compuesto
./GalleryGen.py --steps 6 --intake        # lote real (más pasos = más adherencia)
./GalleryGen.py --sin-contexto            # mandar el prompt tal cual
./GalleryGen.py --contexto "night scene"  # añadir algo puntual a todo el lote
```

## Formato de `prompts.txt`

```
<nombre> :: <prompt>
```

El nombre lleva la categoría (`sticker`, `meme`, `gift`/`regalo`, `personaje`,
`series`/`serie`, `juegos`/`juego`) o un personaje del mapeo, para que
`GalleryIntake.py` sepa dónde va:

`sticker-gato-negro` → `stickers/aportes--gato-negro--01.png`

## Regla de contenido

Se describe, no se nombra. «hooded swordsman with a giant sword» funciona;
«Guts from Berserk» da peor resultado y puede chocar con los términos del
proveedor. Los prompts de ejemplo siguen esa regla.

## Rollback

Nada que deshacer en el sistema: no se instala nada, no hay servicio, no hay
credenciales guardadas. Se borra la carpeta y las imágenes de `_inbox`.
