#!/usr/bin/env python3
"""GalleryGen.py — genera imágenes para la galería con un modelo abierto.

Decisión del usuario (2026-11-15): la IA generativa se acepta si es de código
abierto o plan gratuito y no consume recursos de esta máquina. Por eso NO se
ejecuta ningún modelo en local: se llama a una API.

Proveedores:
  cf           Cloudflare Workers AI · FLUX.1 [schnell] (12B, Apache-2.0)
               plan Free: 10.000 neuronas/día ≈ 230 imágenes de 512x512 a 4 pasos
               Docs: https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/
               Precio: https://developers.cloudflare.com/workers-ai/platform/pricing/
  pollinations Sin clave, modelo abierto 'sana' (más rápido, menos fiel).
               Solo como prueba del circuito.

Formato del archivo de prompts (una línea por imagen, '#' = comentario):

    <nombre-archivo> :: <prompt>

El nombre debe llevar la palabra clave de categoría (sticker, meme, gift,
personaje) o el nombre de un personaje del mapeo, porque el que clasifica
después es GalleryIntake.py.

Uso:
  ./GalleryGen.py --dry-run                 # ver qué haría, sin red
  ./GalleryGen.py --provider cf             # requiere CLOUDFLARE_ACCOUNT_ID y CLOUDFLARE_API_TOKEN
  ./GalleryGen.py --provider pollinations   # sin claves
  ./GalleryGen.py --check                   # valida el token sin gastar neuronas
"""
import argparse, base64, json, os, re, subprocess, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path

HOME = Path.home()
INBOX = HOME / "Imágenes/wallpapers/galeria/_inbox"
PROMPTS = Path(__file__).with_name("prompts.txt")
INTAKE = Path(os.environ.get("GALLERY_INTAKE",
                             HOME / ".config/hypr/UserScripts/GalleryIntake.py"))

# [1] Modelo y coste (docs oficiales, ver cabecera)
CF_MODEL = "@cf/black-forest-labs/flux-1-schnell"
CF_URL = "https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/" + CF_MODEL
POLL_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&nologo=true&model=sana"

# [2] Nombre de archivo seguro: minúsculas, sin acentos, guiones
def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")[:48]

# [2b] Contexto del prompt: se compone ANTES de llamar a la API.
#  Lección del primer lote: un prompt suelto («pixel art sticker of X») deja
#  demasiadas decisiones al modelo: mete escenario, texto y recorta el sujeto.
#  Aquí se fija lo que no debe variar (estilo, encuadre, fondo) y el prompt del
#  archivo solo describe el sujeto. FLUX usa T5, lee prompts largos bien.
BASE = ("16-bit pixel art, crisp square pixels, hard edges, no anti-aliasing, "
        "limited palette of 12 colors, flat shading with one light source, "
        "single centered subject, clean solid background, generous margin, "
        "no text, no letters, no watermark, no frame, no photorealism")

CONTEXTOS = {
    "sticker":   "die-cut sticker look, thick dark outline, subject fully inside the frame, plain background, no scenery",
    "meme":      "reaction-image composition, simple bold shapes, exaggerated expression, plain background, no caption",
    "gift":      "gift illustration, warm palette, tidy silhouette, readable at small size",
    "personaje": "character portrait, bust framing, neutral background, readable silhouette",
    "series":    "series emblem, symbolic composition, no logos, no letters",
    "juegos":    "game icon, strong readable silhouette, contrasting background",
}
# El prefijo del nombre decide el contexto; se aceptan los mismos sinónimos que
# GalleryIntake.py para que no haya dos listas de verdad.
ALIAS = {"stickers": "sticker", "pegatina": "sticker", "calcomania": "sticker",
         "memes": "meme", "regalo": "gift", "regalos": "gift", "gifts": "gift",
         "chibi": "personaje", "avatar": "personaje", "personajes": "personaje",
         "serie": "series", "tv": "series", "peli": "series", "pelicula": "series",
         "juego": "juegos", "game": "juegos", "games": "juegos", "arcade": "juegos"}


def contexto_de(nombre: str) -> str:
    return CONTEXTOS.get(ALIAS.get(nombre.split("-")[0], nombre.split("-")[0]), "")


def componer(nombre: str, prompt: str, extra: str = "", base: str = BASE) -> str:
    """Sujeto primero (manda en el modelo), luego contexto de categoría, luego estilo."""
    partes = [prompt.strip(), contexto_de(nombre), extra.strip(), base]
    return ". ".join(p.rstrip(".") for p in partes if p)


# [3] Lectura de prompts: 'nombre :: prompt'
def leer_prompts(path: Path):
    out = []
    for i, linea in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if "::" not in linea:
            sys.exit(f"línea {i}: falta el separador ' :: '")
        nombre, prompt = (p.strip() for p in linea.split("::", 1))
        if not nombre or not prompt:
            sys.exit(f"línea {i}: nombre o prompt vacío")
        out.append((slug(nombre), prompt))
    return out

# [4] Destino sin pisar nada
def destino_libre(base: str, out_dir: Path = INBOX) -> Path:
    p = out_dir / f"{base}.jpg"
    n = 2
    while p.exists():
        p = out_dir / f"{base}-{n}.jpg"
        n += 1
    return p

# [5] Cloudflare: POST JSON -> base64 dentro de result.image
#  flux-1-schnell NO acepta width/height: devuelve 1024x1024 fijo y rechaza
#  cualquier propiedad extra con «Additional or unevaluated properties».
#  GalleryIntake.py se encarga de normalizar a 512 px para la galería.
def generar_cf(prompt: str, w: int, h: int, steps: int) -> bytes:
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not acct or not tok:
        sys.exit("faltan CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN en el entorno")
    cuerpo = json.dumps({"prompt": prompt, "steps": steps}).encode()
    req = urllib.request.Request(
        CF_URL.format(acct=acct), data=cuerpo,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            datos = json.loads(r.read())
    except urllib.error.HTTPError as e:
        # Sin esto un 400 se queda en «Bad Request» y no dice qué propiedad sobra.
        detalle = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code}: {detalle}") from None
    if not datos.get("success", False):
        raise RuntimeError(f"Cloudflare rechazó la petición: {datos.get('errors')}")
    return base64.b64decode(datos["result"]["image"])

# [6] Pollinations: GET directo, devuelve la imagen tal cual
def generar_pollinations(prompt: str, w: int, h: int, steps: int) -> bytes:
    url = POLL_URL.format(prompt=urllib.parse.quote(prompt), w=w, h=h)
    with urllib.request.urlopen(url, timeout=180) as r:
        return r.read()

# [6b] Reintentos: 503/429 son habituales en los planes gratuitos
def con_reintentos(fn, *args, intentos=3):
    for i in range(1, intentos + 1):
        try:
            return fn(*args)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            codigo = getattr(e, "code", 0)
            if i == intentos or codigo not in (0, 429, 500, 502, 503, 504):
                raise
            espera = 4 * i
            print(f"        reintento {i}/{intentos - 1} en {espera}s ({codigo or 'red'})")
            time.sleep(espera)

# [7] Comprobación de credenciales sin gastar neuronas
#  Distingue tres fallos que se confunden a menudo y piden arreglos distintos:
#    a) token mal copiado / revocado   -> /user/tokens/verify falla
#    b) token válido sin permiso AI    -> verify 200, /ai devuelve 401/403
#    c) account id de otra cuenta      -> /accounts no incluye ese id
def _cf_get(url: str, tok: str):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"_net": str(e)}


def comprobar_cf() -> int:
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not acct or not tok:
        print("faltan variables de entorno (CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN)")
        return 2

    # a) ¿el token existe y está activo?
    cod, d = _cf_get("https://api.cloudflare.com/client/v4/user/tokens/verify", tok)
    if cod != 200 or not d.get("success"):
        msg = ""
        for e in (d.get("errors") or []):
            msg += f"{e.get('code')}: {e.get('message')} "
        print(f"token inválido o revocado (HTTP {cod}) {msg}".rstrip())
        print(f"   el valor tiene {len(tok)} caracteres")
        print("   cópialo con el botón de copiar del panel: seleccionar a mano")
        print("   suele cortar el final. Se muestra una sola vez, al crearlo.")
        return 1
    print("token: válido y activo")

    # b) ¿tiene permiso sobre Workers AI?
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/models/search?per_page=1"
    cod, d = _cf_get(url, tok)
    if cod == 200 and d.get("success"):
        print("permiso Workers AI: OK -> listo para generar")
        return 0

    if cod in (401, 403):
        print(f"permiso Workers AI: FALTA (HTTP {cod})")
        # c) ¿la cuenta del Account ID es la del token?
        cod2, d2 = _cf_get("https://api.cloudflare.com/client/v4/accounts?per_page=50", tok)
        ids = {str(a.get("id")) for a in (d2.get("result") or [])}
        if cod2 == 200 and ids and acct not in ids:
            print(f"   ADEMÁS: el Account ID no está entre las cuentas del token:")
            for a in (d2.get("result") or [])[:5]:
                print(f"   - {a.get('id')}  {a.get('name')}")
            print("   usa el Account ID de la MISMA cuenta que el token")
        print("   arreglo recomendado (docs oficiales): Workers AI > 'Use REST API'")
        print("   > 'Create a Workers AI API Token'. Si lo creas a mano, el token")
        print("   necesita  Account > Workers AI > Read  Y  Edit.")
        return 1

    print(f"respuesta inesperada de Cloudflare (HTTP {cod})")
    return 1

# [8] main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=("cf", "pollinations"), default="cf")
    ap.add_argument("--size", default="512x512",
                    help="solo para pollinations; flux-1-schnell devuelve 1024x1024")
    ap.add_argument("--steps", type=int, default=4, help="1..8, por defecto 4")
    ap.add_argument("--delay", type=float, default=2.0, help="segundos entre peticiones")
    ap.add_argument("--out-dir", default=str(INBOX), help="por defecto, el buzón de la galería")
    ap.add_argument("--prompts", default=str(PROMPTS), help="archivo de prompts")
    ap.add_argument("--intake", action="store_true",
                    help="clasificar lo generado con GalleryIntake.py al terminar")
    ap.add_argument("--contexto", default="",
                    help="texto extra de estilo que se añade a cada prompt")
    ap.add_argument("--sin-contexto", action="store_true",
                    help="enviar el prompt tal cual, sin la capa de estilo")
    ap.add_argument("--estilo", default="",
                    help="sustituye la capa BASE (para wallpapers, fuera del pixel art)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if a.check:
        return comprobar_cf()
    if not Path(a.prompts).is_file():
        sys.exit(f"no existe {a.prompts}")
    w, h = (int(x) for x in a.size.lower().split("x"))
    tareas = leer_prompts(Path(a.prompts))
    if not tareas:
        sys.exit("el archivo de prompts está vacío")
    if not a.sin_contexto:
        tareas = [(n, componer(n, p, a.contexto, a.estilo or BASE)) for n, p in tareas]
    elif a.estilo:
        tareas = [(n, f"{p.rstrip('.')}. {a.estilo}") for n, p in tareas]
    if a.provider == "cf" and a.steps not in range(1, 9):
        sys.exit("--steps debe estar entre 1 y 8")
    out = Path(a.out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    for base, prompt in tareas:
        dst = destino_libre(base, out)
        print(f"{'[dry] ' if a.dry_run else ''}{dst.name}")
        print(f"        prompt: {prompt}")
        if a.dry_run:
            continue
        try:
            datos = con_reintentos((generar_cf if a.provider == "cf" else generar_pollinations),
                                   prompt, w, h, a.steps)
        except Exception as e:
            print(f"        FALLO {base}: {e}")
            continue
        dst.write_bytes(datos)
        print(f"        {dst.stat().st_size // 1024} KB en {dst}")
        time.sleep(a.delay)
    if not a.dry_run:
        if a.intake:
            if not INTAKE.is_file():
                print(f"no encuentro {INTAKE}", file=sys.stderr)
                return 1
            print("\nClasificando con GalleryIntake.py…")
            return subprocess.run([sys.executable, str(INTAKE), "--origen",
                                   "generado por IA (Cloudflare FLUX.1 schnell)"]).returncode
        print("\nAhora: GalleryIntake.py --dry-run  y luego sin --dry-run")
    return 0

if __name__ == "__main__":
    sys.exit(main())
