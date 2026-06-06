"""
scraper_mundial.py
==================
Descarga todos los datos del Mundial 2026 desde FotMob:
  1. Lista de equipos con grupo
  2. Logos/banderas de cada equipo  → escudos/{slug}.png
  3. Plantel de cada equipo         → data/planteles/{slug}.json
  4. Fotos de jugadores             → fotos/{fid}.png

Uso:
    python scripts/scraper_mundial.py              # todo
    python scripts/scraper_mundial.py --solo-logos # solo banderas
    python scripts/scraper_mundial.py --equipo ARG # solo un equipo (por slug)
"""

import sys, os, json, time, argparse
import urllib.request
import urllib.error

# ── Rutas ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_ESCUDOS  = os.path.join(BASE_DIR, "escudos")
DIR_FOTOS    = os.path.join(BASE_DIR, "fotos")
DIR_PLANTELES = os.path.join(BASE_DIR, "data", "planteles")

for d in [DIR_ESCUDOS, DIR_FOTOS, DIR_PLANTELES]:
    os.makedirs(d, exist_ok=True)

# ── Constantes FotMob ─────────────────────────────────────────────────────────
LEAGUE_ID    = 77   # Copa del Mundo FIFA
LEAGUE_API   = f"https://www.fotmob.com/api/data/leagues?id={LEAGUE_ID}"
TEAM_API     = "https://www.fotmob.com/api/data/teams?id={team_id}"
LOGO_URL     = "https://images.fotmob.com/image_resources/logo/teamlogo/{team_id}.png"
FOTO_URL     = "https://images.fotmob.com/image_resources/playerimages/{fid}.png"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.fotmob.com/",
    "Accept-Language": "es-ES,es;q=0.9",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def download_image(url, dest_path, min_bytes=200):
    """Descarga imagen; retorna True si exitoso, False si falla o es un placeholder."""
    if os.path.exists(dest_path):
        return True  # ya existe
    try:
        req = urllib.request.Request(url, headers={**HEADERS, "Accept": "image/png,image/*"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < min_bytes:
            print(f"    ⚠️  Imagen muy pequeña ({len(data)} bytes), omitida: {url}")
            return False
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            return False
        print(f"    ❌ HTTP {e.code}: {url}")
        return False
    except Exception as e:
        print(f"    ❌ Error descargando {url}: {e}")
        return False

def nombre_a_slug(nombre):
    """'South Korea' → 'southkorea'  |  'Ivory Coast' → 'ivorycoast'"""
    import unicodedata
    s = unicodedata.normalize("NFKD", nombre.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace(" ", "").replace("-", "").replace("'", "")
    return s

# ── 1. Obtener lista de equipos ───────────────────────────────────────────────
def obtener_equipos():
    print("📡 Obteniendo equipos del Mundial desde FotMob...")
    data = fetch_json(LEAGUE_API)
    tables = data["table"][0]["data"]["tables"]

    equipos = {}   # id → dict (deduplicado)
    for grupo in tables:
        nombre_grupo = grupo.get("leagueName", "")
        # Solo los grupos A–L (no "Best 3rd placed teams")
        if not nombre_grupo.startswith("Grp."):
            continue
        letra = nombre_grupo.replace("Grp. ", "")
        for row in grupo["table"]["all"]:
            tid = row["id"]
            if tid not in equipos:
                slug = nombre_a_slug(row["name"])
                equipos[tid] = {
                    "id": tid,
                    "nombre": row["name"],
                    "slug": slug,
                    "grupo": letra,
                    "pageUrl": row["pageUrl"],
                }

    # Ordenar por grupo y nombre
    lista = sorted(equipos.values(), key=lambda e: (e["grupo"], e["nombre"]))
    print(f"✅ {len(lista)} equipos encontrados en {len(set(e['grupo'] for e in lista))} grupos\n")
    return lista

# ── 2. Descargar logos/banderas ───────────────────────────────────────────────
def descargar_logos(equipos):
    print("🏳️  Descargando logos/banderas...")
    ok = fail = 0
    for eq in equipos:
        dest = os.path.join(DIR_ESCUDOS, f"{eq['slug']}.png")
        url  = LOGO_URL.format(team_id=eq["id"])
        if download_image(url, dest):
            print(f"  ✅ {eq['nombre']:25} → escudos/{eq['slug']}.png")
            ok += 1
        else:
            print(f"  ❌ {eq['nombre']:25} → sin imagen")
            fail += 1
        time.sleep(0.2)
    print(f"\n  Logos: {ok} OK, {fail} fallidos\n")

# ── 3. Descargar planteles ────────────────────────────────────────────────────
POSICION_MAP = {
    "Goalkeepers": "GK",
    "Defenders":   "DEF",
    "Midfielders": "MED",
    "Forwards":    "DEL",
}

def descargar_plantel(eq):
    slug = eq["slug"]
    dest = os.path.join(DIR_PLANTELES, f"{slug}.json")
    if os.path.exists(dest):
        print(f"  ⏭️  {eq['nombre']:25} ya tiene plantel, omitiendo")
        return

    url = TEAM_API.format(team_id=eq["id"])
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f"  ❌ Error API equipo {eq['nombre']}: {e}")
        return

    squad_raw = data.get("squad", {}).get("squad", [])
    if not squad_raw:
        # Algunos endpoints devuelven estructura diferente
        squad_raw = data.get("squad", [])

    jugadores = []
    for grupo_pos in squad_raw:
        titulo = grupo_pos.get("title", "")
        posicion = POSICION_MAP.get(titulo, titulo)
        miembros = grupo_pos.get("members", [])
        for m in miembros:
            # Saltar cuerpo técnico
            if m.get("role", {}).get("fallback", "") in ("Coach", "Assistant Coach"):
                continue
            fid = str(m.get("id", ""))
            jugadores.append({
                "fid": fid,
                "nombre": m.get("name", ""),
                "numero": m.get("shirtNumber"),
                "posicion": posicion,
                "nacionalidad": m.get("ccode", ""),
            })

    plantel_json = {
        "equipo": eq["nombre"],
        "slug": slug,
        "grupo": eq["grupo"],
        "fotmob_id": eq["id"],
        "jugadores": jugadores,
    }

    with open(dest, "w", encoding="utf-8") as f:
        json.dump(plantel_json, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {eq['nombre']:25} → {len(jugadores)} jugadores guardados")
    return jugadores

def descargar_planteles(equipos):
    print("👥 Descargando planteles...")
    for eq in equipos:
        descargar_plantel(eq)
        time.sleep(0.8)
    print()

# ── 4. Descargar fotos de jugadores ──────────────────────────────────────────
def descargar_fotos(equipos):
    print("📸 Descargando fotos de jugadores...")
    total_ok = total_fail = 0

    for eq in equipos:
        plantel_path = os.path.join(DIR_PLANTELES, f"{eq['slug']}.json")
        if not os.path.exists(plantel_path):
            print(f"  ⚠️  Sin plantel para {eq['nombre']}, omitiendo fotos")
            continue

        with open(plantel_path, encoding="utf-8") as f:
            plantel = json.load(f)

        jugadores = plantel.get("jugadores", [])
        ok = fail = 0
        print(f"  📷 {eq['nombre']} ({len(jugadores)} jugadores)...")

        for j in jugadores:
            fid = j.get("fid", "")
            if not fid:
                continue
            dest = os.path.join(DIR_FOTOS, f"{fid}.png")
            url  = FOTO_URL.format(fid=fid)
            if download_image(url, dest):
                ok += 1
            else:
                fail += 1
            time.sleep(0.25)

        print(f"     → {ok} OK, {fail} sin foto")
        total_ok += ok
        total_fail += fail
        time.sleep(0.5)

    print(f"\n  Fotos totales: {total_ok} OK, {total_fail} sin foto\n")

# ── 5. Guardar equipos.json ───────────────────────────────────────────────────
def guardar_equipos_json(equipos):
    dest = os.path.join(BASE_DIR, "data", "equipos.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(equipos, f, ensure_ascii=False, indent=2)
    print(f"💾 Lista de equipos guardada en data/equipos.json ({len(equipos)} equipos)\n")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Scraper Mundial 2026 - FotMob")
    parser.add_argument("--solo-logos",   action="store_true", help="Solo descarga logos")
    parser.add_argument("--solo-planteles", action="store_true", help="Solo descarga planteles")
    parser.add_argument("--solo-fotos",   action="store_true", help="Solo descarga fotos")
    parser.add_argument("--equipo",       type=str, default=None, help="Slug del equipo a procesar (ej: argentina)")
    args = parser.parse_args()

    equipos = obtener_equipos()

    # Filtro por equipo individual
    if args.equipo:
        equipos = [e for e in equipos if e["slug"] == args.equipo.lower()]
        if not equipos:
            print(f"❌ Equipo '{args.equipo}' no encontrado")
            print("Slugs disponibles:", ", ".join(e["slug"] for e in obtener_equipos()))
            sys.exit(1)
        print(f"🔍 Procesando solo: {equipos[0]['nombre']}\n")

    # Siempre guardamos el JSON de equipos
    guardar_equipos_json(equipos)

    todo = not (args.solo_logos or args.solo_planteles or args.solo_fotos)

    if todo or args.solo_logos:
        descargar_logos(equipos)

    if todo or args.solo_planteles:
        descargar_planteles(equipos)

    if todo or args.solo_fotos:
        descargar_fotos(equipos)

    print("🎉 ¡Scraping completado!")

if __name__ == "__main__":
    main()
