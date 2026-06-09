"""
scraper_dt_mundial.py
Scrapes el director técnico de cada selección mundialista desde FotMob.
- Lee data/planteles/{slug}.json (necesita campo fotmob_id)
- Extrae el coach del endpoint de squad
- Descarga su foto a fotos/{fid}.png
- Actualiza el JSON con tecnico: {"nombre": "...", "fid": ...}

Uso:
    python scripts/scraper_dt_mundial.py            # todos los equipos
    python scripts/scraper_dt_mundial.py --slug brazil  # solo uno
    python scripts/scraper_dt_mundial.py --dry-run  # sin escribir
"""
import argparse, json, os, time, urllib.request, urllib.error
from pathlib import Path

ROOT      = Path(__file__).parent.parent
PLANTELES = ROOT / "data" / "planteles"
FOTOS     = ROOT / "fotos"

FOTO_URL = "https://images.fotmob.com/image_resources/playerimages/{fid}.png"
TEAM_API = "https://www.fotmob.com/api/data/teams?id={team_id}&ccode3=ARG"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.fotmob.com/",
}

# Slugs mundialistas (los 48 equipos)
MUNDIAL_SLUGS = [
    "algeria","argentina","australia","austria","belgium","bosniaandherzegovina",
    "brazil","canada","capeverde","colombia","drcongo","croatia","curacao","czechia",
    "ecuador","egypt","england","france","germany","ghana","haiti","iran","iraq",
    "ivorycoast","japan","jordan","mexico","morocco","netherlands","newzealand",
    "norway","panama","paraguay","portugal","qatar","saudiarabia","scotland",
    "senegal","southafrica","southkorea","spain","sweden","switzerland","tunisia",
    "turkiye","usa","uruguay","uzbekistan",
]


def fetch_squad_raw(team_id: int) -> dict:
    url = TEAM_API.format(team_id=team_id)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def extract_coach(data: dict) -> dict | None:
    """Extrae nombre y fid del coach del squad response de FotMob."""
    squad_list = data.get("squad", {}).get("squad", [])
    for group in squad_list:
        if group.get("title", "").lower() == "coach":
            members = group.get("members", [])
            if members:
                m = members[0]
                fid = m.get("id")
                nombre = m.get("name", "")
                if fid and nombre:
                    return {"nombre": nombre, "fid": int(fid)}
    return None


def download_photo(fid: int) -> bool:
    dest = FOTOS / f"{fid}.png"
    if dest.exists():
        return True
    url = FOTO_URL.format(fid=fid)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 100:
            return False
        dest.write_bytes(data)
        return True
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            return False
        print(f"    HTTP {e.code} para fid={fid}")
        return False
    except Exception as e:
        print(f"    Error fid={fid}: {e}")
        return False


def process(slug: str, dry_run: bool) -> None:
    plantel_path = PLANTELES / f"{slug}.json"
    if not plantel_path.exists():
        print(f"  [{slug}] SIN PLANTEL JSON — skip")
        return

    plantel = json.loads(plantel_path.read_text(encoding="utf-8"))
    fotmob_id = plantel.get("fotmob_id")
    if not fotmob_id:
        print(f"  [{slug}] sin fotmob_id — skip")
        return

    try:
        data = fetch_squad_raw(int(fotmob_id))
    except Exception as e:
        print(f"  [{slug}] ERROR fetch: {e}")
        return

    coach = extract_coach(data)
    if not coach:
        print(f"  [{slug}] sin coach en FotMob")
        return

    print(f"  [{slug}] Coach: {coach['nombre']} (fid={coach['fid']})", end="")

    if dry_run:
        print(" [DRY-RUN]")
        return

    # Descargar foto
    ok = download_photo(coach["fid"])
    print(f" — foto: {'OK' if ok else 'NO DISPONIBLE'}")

    # Actualizar JSON
    plantel["tecnico"] = coach
    plantel_path.write_text(json.dumps(plantel, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", help="Procesar solo este equipo")
    parser.add_argument("--dry-run", action="store_true", help="Sin escribir archivos")
    args = parser.parse_args()

    slugs = [args.slug] if args.slug else MUNDIAL_SLUGS

    print(f"Scraping DT de {len(slugs)} equipo(s)...")
    for i, slug in enumerate(slugs, 1):
        print(f"[{i}/{len(slugs)}]", end=" ")
        process(slug, args.dry_run)
        if len(slugs) > 1:
            time.sleep(0.6)

    print("\nListo.")


if __name__ == "__main__":
    main()
