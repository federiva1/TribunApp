"""
scraper_seleccion.py
Obtiene los jugadores argentinos que aparecieron en los últimos 5 partidos
de la Selección Argentina (team=6) desde api-sports.io y descarga sus fotos
desde FotMob.

Uso:
    python scripts/scraper_seleccion.py

Salida:
    data/seleccion.json              → jugadores elegibles con datos
    fotos/seleccion/{fid}.png        → fotos de jugadores (FotMob ID)

Nota sobre IDs:
    api-sports.io usa sus propios player IDs (apid).
    FotMob usa fid distintos. Para matchear se usa el nombre del jugador
    contra el plantel ya descargado en data/planteles/*.json.
    Si no hay match, la foto se descarga con el apid de api-sports.io
    desde su propia CDN, y fid quedará null.
"""

import json
import os
import time
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
from apikey import API_KEY
TEAM_ID    = 6       # Argentina en api-sports.io
LEAGUE_ID  = 1       # FIFA World Cup (cambia a 10 para WC Qualifying CONMEBOL)
# También probar: league=10 (WC Qualification CONMEBOL), season=2026
# La selección puede tener fixtures en múltiples ligas/torneos

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "data")
FOTOS_DIR  = os.path.join(BASE_DIR, "fotos", "seleccion")

API_BASE   = "https://v3.football.api-sports.io"

HEADERS_API = {
    "x-apisports-key": API_KEY,
    "Accept": "application/json",
}

HEADERS_FOTMOB = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.fotmob.com/",
}

FOTMOB_PHOTO_URL  = "https://images.fotmob.com/image_resources/playerimages/{fid}.png"
APISPORTS_PHOTO   = "https://media.api-sports.io/football/players/{pid}.png"


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_api(path: str, params: dict = None) -> dict:
    """GET a api-sports.io con autenticación."""
    url = f"{API_BASE}/{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers=HEADERS_API)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_photo_fotmob(fid: int, dest: str) -> bool:
    """Descarga foto desde FotMob. Retorna True si éxito."""
    if os.path.exists(dest):
        return True
    url = FOTMOB_PHOTO_URL.format(fid=fid)
    try:
        req = urllib.request.Request(url, headers=HEADERS_FOTMOB)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        if len(data) < 100:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            return False
        return False
    except Exception:
        return False


def download_photo_apisports(pid: int, dest: str) -> bool:
    """Descarga foto desde api-sports.io CDN como fallback."""
    if os.path.exists(dest):
        return True
    url = APISPORTS_PHOTO.format(pid=pid)
    try:
        req = urllib.request.Request(url, headers=HEADERS_API)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        if len(data) < 100:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False


def load_local_planteles() -> dict:
    """
    Carga todos los JSONs de planteles ya descargados para poder matchear
    jugadores por nombre y obtener sus FotMob IDs.
    Retorna dict: nombre_normalizado → fid
    """
    planteles_dir = os.path.join(DATA_DIR, "planteles")
    name_to_fid = {}
    if not os.path.isdir(planteles_dir):
        print("  Advertencia: no se encontró data/planteles/. Ejecutá primero scraper_planteles.py")
        return name_to_fid

    for fname in os.listdir(planteles_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(planteles_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                players = json.load(f)
            for p in players:
                normalized = p.get("name", "").lower().strip()
                if normalized and p.get("fid"):
                    name_to_fid[normalized] = p["fid"]
        except Exception:
            pass

    print(f"  {len(name_to_fid)} jugadores en planteles locales para matching")
    return name_to_fid


def get_last_5_fixtures() -> list:
    """
    Obtiene los últimos 5 partidos jugados por la Selección Argentina.
    Prueba múltiples ligas si no encuentra resultados.
    """
    # Ligas en las que suele aparecer Argentina:
    # 1 = FIFA World Cup, 10 = WC Qualification CONMEBOL,
    # 4 = Copa América, 26 = Friendlies
    leagues_to_try = [
        {"league": 10, "season": 2026, "desc": "WC Qual CONMEBOL 2026"},
        {"league": 10, "season": 2025, "desc": "WC Qual CONMEBOL 2025"},
        {"league": 1,  "season": 2026, "desc": "FIFA World Cup 2026"},
        {"league": 4,  "season": 2024, "desc": "Copa America 2024"},
        {"league": 26, "season": 2025, "desc": "Amistosos 2025"},
    ]

    for league_cfg in leagues_to_try:
        print(f"  Buscando fixtures en: {league_cfg['desc']}...")
        try:
            resp = fetch_api("fixtures", {
                "team":   TEAM_ID,
                "league": league_cfg["league"],
                "season": league_cfg["season"],
                "status": "FT",       # solo partidos terminados
            })
            fixtures = resp.get("response", [])
            if fixtures:
                # Ordenar por fecha descendente y tomar los 5 más recientes
                fixtures.sort(key=lambda x: x["fixture"]["date"], reverse=True)
                last5 = fixtures[:5]
                print(f"  Encontrados {len(fixtures)} partidos, usando los últimos {len(last5)}")
                return last5
        except Exception as e:
            print(f"  Error en {league_cfg['desc']}: {e}")
        time.sleep(0.5)

    print("  No se encontraron partidos terminados. Buscando sin filtro de status...")
    try:
        resp = fetch_api("fixtures", {
            "team":   TEAM_ID,
            "last":   10,
        })
        fixtures = resp.get("response", [])
        fixtures.sort(key=lambda x: x["fixture"]["date"], reverse=True)
        return fixtures[:5]
    except Exception as e:
        print(f"  Error en búsqueda sin filtro: {e}")
        return []


def get_fixture_players(fixture_id: int) -> list:
    """
    Obtiene los jugadores que participaron en un partido específico.
    Filtra solo los de Argentina (team_id=6).
    """
    try:
        resp = fetch_api("fixtures/players", {"fixture": fixture_id})
        teams_data = resp.get("response", [])
        for team_entry in teams_data:
            team_info = team_entry.get("team", {})
            if team_info.get("id") == TEAM_ID:
                return team_entry.get("players", [])
    except Exception as e:
        print(f"    Error obteniendo jugadores del fixture {fixture_id}: {e}")
    return []


def main():
    print("=" * 60)
    print("  Scraper Selección Argentina — api-sports.io + FotMob")
    print("=" * 60)

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FOTOS_DIR, exist_ok=True)

    # ── Cargar planteles locales para matching ────────────────────────────────
    name_to_fid = load_local_planteles()

    # ── Obtener últimos 5 partidos ────────────────────────────────────────────
    print("\nObteniendo últimos 5 partidos de Argentina...")
    fixtures = get_last_5_fixtures()

    if not fixtures:
        print("ERROR: No se pudieron obtener partidos. Verificá la API key y los parámetros.")
        return

    print(f"\nPartidos a procesar: {len(fixtures)}")
    for fx in fixtures:
        home = fx["teams"]["home"]["name"]
        away = fx["teams"]["away"]["name"]
        date = fx["fixture"]["date"][:10]
        print(f"  {date}: {home} vs {away} (ID: {fx['fixture']['id']})")

    # ── Recolectar jugadores de los 5 partidos ────────────────────────────────
    print("\nRecolectando jugadores...")
    players_seen = {}   # apid → datos del jugador

    for fx in fixtures:
        fx_id   = fx["fixture"]["id"]
        fx_date = fx["fixture"]["date"][:10]
        home    = fx["teams"]["home"]["name"]
        away    = fx["teams"]["away"]["name"]
        print(f"  Fixture {fx_id} ({fx_date}: {home} vs {away})...")

        fx_players = get_fixture_players(fx_id)
        print(f"    {len(fx_players)} jugadores de Argentina")

        for entry in fx_players:
            p    = entry.get("player", {})
            apid = p.get("id")
            if not apid or apid in players_seen:
                continue

            name_norm = p.get("name", "").lower().strip()
            fotmob_id = name_to_fid.get(name_norm)

            players_seen[apid] = {
                "apid":        apid,
                "name":        p.get("name", ""),
                "nationality": "Argentina",
                "fid":         fotmob_id,   # puede ser None si no hay match
                "photo_api":   p.get("photo", ""),
            }

        time.sleep(0.5)

    jugadores = list(players_seen.values())
    jugadores.sort(key=lambda x: x["name"])

    print(f"\nTotal jugadores únicos: {len(jugadores)}")
    matched = sum(1 for j in jugadores if j["fid"] is not None)
    print(f"Con FotMob ID (para fotos HD): {matched}")
    print(f"Sin FotMob ID (foto estándar): {len(jugadores) - matched}")

    # ── Guardar JSON ──────────────────────────────────────────────────────────
    seleccion_path = os.path.join(DATA_DIR, "seleccion.json")
    # Exportar sin el campo interno photo_api
    export = [{k: v for k, v in j.items() if k != "photo_api"} for j in jugadores]
    with open(seleccion_path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {seleccion_path}")

    # ── Descargar fotos ───────────────────────────────────────────────────────
    print("\nDescargando fotos...")
    ok_fotmob = 0
    ok_api    = 0
    failed    = 0

    for j in jugadores:
        name   = j["name"]
        apid   = j["apid"]
        fid    = j["fid"]

        # Nombre del archivo: usamos fid si existe, sino apid
        file_id  = fid if fid else apid
        dest     = os.path.join(FOTOS_DIR, f"{file_id}.png")

        if fid:
            success = download_photo_fotmob(fid, dest)
            if success:
                ok_fotmob += 1
                print(f"  [FotMob OK] {name} ({fid})")
            else:
                # Fallback a api-sports CDN
                dest_api = os.path.join(FOTOS_DIR, f"{apid}.png")
                success2 = download_photo_apisports(apid, dest_api)
                if success2:
                    ok_api += 1
                    print(f"  [API OK]    {name} (fotmob sin foto, usando api-sports)")
                else:
                    failed += 1
                    print(f"  [SKIP]      {name} — sin foto disponible")
        else:
            # Sin FotMob ID → usar api-sports CDN
            dest_api = os.path.join(FOTOS_DIR, f"{apid}.png")
            success = download_photo_apisports(apid, dest_api)
            if success:
                ok_api += 1
                print(f"  [API OK]    {name} (sin fid)")
            else:
                failed += 1
                print(f"  [SKIP]      {name} — sin foto disponible")

        time.sleep(0.3)

    print(f"\nResumen fotos:")
    print(f"  FotMob (HD): {ok_fotmob}")
    print(f"  api-sports:  {ok_api}")
    print(f"  Sin foto:    {failed}")

    print("\n" + "=" * 60)
    print("  Proceso completado.")
    print(f"  JSON guardado en: {seleccion_path}")
    print(f"  Fotos en:         {FOTOS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
