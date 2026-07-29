"""
scraper_planteles.py
Descarga el plantel y fotos de los 30 equipos de la Liga Profesional Argentina
desde la API pública de FotMob.

Uso:
    python scripts/scraper_planteles.py

Estructura de salida:
    data/planteles/{slug}.json  → lista de jugadores por equipo
    fotos/{slug}/{fid}.png      → foto de cada jugador
"""

import json
import os
import time
import urllib.request
import urllib.error

# ── Directorio raíz del proyecto (relativo a este script) ─────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "planteles")
FOTOS_DIR = os.path.join(BASE_DIR, "fotos")

# ── Headers para no ser bloqueado por FotMob ──────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.fotmob.com/",
}

# ── 30 equipos de la Liga Profesional Argentina ────────────────────────────────
# IDs obtenidos de: fotmob.com/teams/{ID}/overview/{slug}
# Fuente verificada: API FotMob league 112 (temporada Apertura 2026)
EQUIPOS = [
    # ── Grupo A ──────────────────────────────────────────────────────────────
    {"name": "Velez Sarsfield",              "fid": 10079,  "slug": "velez-sarsfield"},
    {"name": "Estudiantes",                  "fid": 10094,  "slug": "estudiantes"},
    {"name": "Boca Juniors",                 "fid": 10077,  "slug": "boca-juniors"},
    {"name": "Union",                        "fid": 10096,  "slug": "union"},
    {"name": "Defensa y Justicia",           "fid": 161730, "slug": "defensa-y-justicia"},
    {"name": "Lanus",                        "fid": 10082,  "slug": "lanus"},
    {"name": "Talleres",                     "fid": 10101,  "slug": "talleres"},
    {"name": "Independiente",                "fid": 10078,  "slug": "independiente"},
    {"name": "San Lorenzo",                  "fid": 10083,  "slug": "san-lorenzo"},
    {"name": "Club Atletico Platense",       "fid": 10089,  "slug": "club-atletico-platense"},
    {"name": "Instituto",                    "fid": 10090,  "slug": "instituto"},
    {"name": "Gimnasia Mendoza",             "fid": 568727, "slug": "gimnasia-mendoza"},
    {"name": "Central Cordoba de Santiago",  "fid": 213596, "slug": "central-cordoba-de-santiago"},
    {"name": "Newells Old Boys",             "fid": 10201,  "slug": "newells-old-boys"},
    {"name": "Deportivo Riestra",            "fid": 298629, "slug": "deportivo-riestra"},
    # ── Grupo B ──────────────────────────────────────────────────────────────
    {"name": "Independiente Rivadavia",      "fid": 161729, "slug": "independiente-rivadavia"},
    {"name": "River Plate",                  "fid": 10076,  "slug": "river-plate"},
    {"name": "Argentinos Juniors",           "fid": 10086,  "slug": "argentinos-juniors"},
    {"name": "Rosario Central",              "fid": 10084,  "slug": "rosario-central"},
    {"name": "Belgrano",                     "fid": 10092,  "slug": "belgrano"},
    {"name": "Racing Club",                  "fid": 10080,  "slug": "racing-club"},
    {"name": "Tigre",                        "fid": 89396,  "slug": "tigre"},
    {"name": "Huracan",                      "fid": 10081,  "slug": "huracan"},
    {"name": "Barracas Central",             "fid": 213534, "slug": "barracas-central"},
    {"name": "Sarmiento",                    "fid": 202757, "slug": "sarmiento"},
    {"name": "Gimnasia LP",                  "fid": 10103,  "slug": "gimnasia-lp"},
    {"name": "Banfield",                     "fid": 10087,  "slug": "banfield"},
    {"name": "Atletico Tucuman",             "fid": 161727, "slug": "atletico-tucuman"},
    {"name": "Aldosivi",                     "fid": 161728, "slug": "aldosivi"},
    {"name": "Estudiantes de Rio Cuarto",    "fid": 213591, "slug": "estudiantes-de-rio-cuarto"},
]

# ── URL de imagen de jugador en FotMob ────────────────────────────────────────
FOTO_URL = "https://images.fotmob.com/image_resources/playerimages/{fid}.png"
TEAM_API = "https://www.fotmob.com/api/data/teams?id={team_id}&ccode3=ARG"


def fetch_json(url: str) -> dict:
    """Descarga y parsea JSON desde una URL usando los headers de FotMob."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_squad(team_id: int) -> list:
    """
    Llama a la API de FotMob y devuelve lista de jugadores con:
        num, name, fid, nationality, position
    """
    url = TEAM_API.format(team_id=team_id)
    data = fetch_json(url)

    players = []
    seen_ids = set()

    squad_list = data.get("squad", {}).get("squad", [])
    for group in squad_list:
        role = group.get("title", "")
        # Saltar entrenadores
        if role == "coach":
            continue
        for member in group.get("members", []):
            pid = str(member.get("id", ""))
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            players.append({
                # `.get(k, "")` NO cubre el caso clave-presente-con-valor-None:
                # devolvería None y str(None) == 'None' (bug). El `or ""` lo evita.
                "num":         str(member.get("shirtNumber") or ""),
                "name":        member.get("name", ""),
                "fid":         int(pid),
                "nationality": member.get("ccode", ""),
                "position":    role,
            })

    return players


def download_photo(fid: int, dest_path: str) -> bool:
    """
    Descarga la foto del jugador desde FotMob.
    Devuelve True si tuvo éxito, False si no existe o hay error.
    """
    if os.path.exists(dest_path):
        return True  # ya descargada

    url = FOTO_URL.format(fid=fid)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        # Verificar que sea una imagen válida (no una respuesta vacía)
        if len(data) < 100:
            return False
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            return False  # foto no disponible → skip sin error
        print(f"    HTTP {e.code} al descargar foto {fid}: {e}")
        return False
    except Exception as e:
        print(f"    Error al descargar foto {fid}: {e}")
        return False


def process_team(equipo: dict, team_idx: int, total: int) -> None:
    name  = equipo["name"]
    fid   = equipo["fid"]
    slug  = equipo["slug"]

    print(f"\n[{team_idx}/{total}] {name} (FotMob ID: {fid})")
    print(f"  Consultando API...")

    # ── Crear carpetas ────────────────────────────────────────────────────────
    fotos_equipo = os.path.join(FOTOS_DIR, slug)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(fotos_equipo, exist_ok=True)

    # ── Obtener plantel ───────────────────────────────────────────────────────
    try:
        players = fetch_squad(fid)
    except Exception as e:
        print(f"  ERROR al obtener plantel: {e}")
        return

    print(f"  {len(players)} jugadores encontrados")

    # ── Guardar JSON del plantel ──────────────────────────────────────────────
    json_path = os.path.join(DATA_DIR, f"{slug}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    print(f"  Guardado: {json_path}")

    # ── Descargar fotos ───────────────────────────────────────────────────────
    ok = 0
    skip = 0
    for player in players:
        player_fid = player["fid"]
        dest = os.path.join(fotos_equipo, f"{player_fid}.png")
        success = download_photo(player_fid, dest)
        if success:
            ok += 1
        else:
            skip += 1
        time.sleep(0.3)  # delay entre fotos

    print(f"  Fotos: {ok} descargadas, {skip} no disponibles")


def main():
    print("=" * 60)
    print("  Scraper Liga Profesional Argentina — FotMob")
    print("=" * 60)
    print(f"  Equipos: {len(EQUIPOS)}")
    print(f"  Salida JSON:  {DATA_DIR}")
    print(f"  Salida fotos: {FOTOS_DIR}")
    print("=" * 60)

    # Crear directorios raíz si no existen
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FOTOS_DIR, exist_ok=True)

    total = len(EQUIPOS)
    for i, equipo in enumerate(EQUIPOS, start=1):
        process_team(equipo, i, total)
        # Delay entre equipos para no sobrecargar la API
        if i < total:
            time.sleep(1.0)

    print("\n" + "=" * 60)
    print("  Proceso completado.")
    print(f"  JSONs guardados en: {DATA_DIR}")
    print(f"  Fotos guardadas en: {FOTOS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
