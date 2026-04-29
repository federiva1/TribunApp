"""One-shot scraper de FotMob para los 4 partidos de AAAJ con votos
migrados de Formaaajcion (Banfield, Indep. Rivadavia, Atl. Tucumán, Huracán).

Lee __NEXT_DATA__ de cada match page y agrega los jugadores con stats
individuales en el formato de data/estadisticas/argentinosjuniors.json.

Uso:
    python scripts/scrape_fotmob_partidos.py            # headless
    python scripts/scrape_fotmob_partidos.py --headed   # browser visible
    python scripts/scrape_fotmob_partidos.py --only 2026-04-06   # solo una fecha

Dependencias: playwright (ya instalado en el entorno).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
JSON_FILE = ROOT / "data" / "estadisticas" / "argentinosjuniors.json"
RAW_DIR = ROOT / "scripts" / "_fotmob_raw"

TEAM_ID = 10086  # Argentinos Juniors en FotMob

PARTIDOS = [
    {"date": "2026-04-06", "rival": "Banfield",
     "url": "https://www.fotmob.com/matches/argentinos-juniors-vs-banfield/3d5luq#5102060"},
    {"date": "2026-04-11", "rival": "Independiente Rivadavia",
     "url": "https://www.fotmob.com/matches/argentinos-juniors-vs-independiente-rivadavia/6s3zk25#5102082"},
    {"date": "2026-04-19", "rival": "Atletico Tucuman",
     "url": "https://www.fotmob.com/matches/argentinos-juniors-vs-atletico-tucuman/6s3s6wu#5102090"},
    {"date": "2026-04-28", "rival": "Huracan",
     "url": "https://www.fotmob.com/matches/huracan-vs-argentinos-juniors/3d30gy#5102110"},
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")


def to_int(v):
    if v in (None, ""):
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def to_num(v):
    if v in (None, ""):
        return None
    try:
        f = float(v)
        return int(f) if f == int(f) else round(f, 2)
    except (ValueError, TypeError):
        return None


def _player_entry(p: dict) -> dict:
    """Aplana stats de un jugador FotMob al schema TribunApp."""
    flat = {}
    for section in p.get("stats", []):
        for stat_name, stat_obj in (section.get("stats") or {}).items():
            if stat_name == "Shotmap":
                continue
            stat = (stat_obj or {}).get("stat", {})
            if stat_name not in flat:
                flat[stat_name] = (stat.get("value"), stat.get("total"))

    minutos = to_int(flat.get("Minutes played", (None, None))[0]) or 0
    jugo = minutos > 0

    def f(key):
        return flat.get(key, (None, None))[0]

    pases_v, pases_t = flat.get("Accurate passes", (None, None))

    return {
        "nombre":           (p.get("name") or "").strip(),
        "jugo":             jugo,
        "minutos":          minutos if jugo else 0,
        "goles":            to_int(f("Goals")),
        "asistencias":      to_int(f("Assists")),
        "xG":               to_num(f("Expected goals (xG)")),
        "xA":               to_num(f("Expected assists (xA)")),
        "xGxA":             to_num(f("xG + xA")),
        "accDefensivas":    to_int(f("Defensive actions")),
        "disparos":         to_int(f("Shots on target")),
        "toques":           to_int(f("Touches")),
        "pasesAcertados":   to_int(pases_v),
        "pasesIntentados":  to_int(pases_t),
    }


def extract_players(nd: dict) -> tuple[list[dict], list[dict], int]:
    """De __NEXT_DATA__ de un match: jugadores AAAJ, jugadores rival, rival_team_id."""
    ps = nd["props"]["pageProps"]["content"]["playerStats"]
    aaaj, rival = [], []
    rival_id = None
    for pid, p in ps.items():
        tid = p.get("teamId")
        entry = _player_entry(p)
        if str(tid) == str(TEAM_ID):
            aaaj.append(entry)
        else:
            rival.append(entry)
            if rival_id is None and tid is not None:
                rival_id = int(tid)

    sort_key = lambda x: (-1 if x["jugo"] else 0, -(x["minutos"] or 0), x["nombre"])
    aaaj.sort(key=sort_key)
    rival.sort(key=sort_key)
    return aaaj, rival, rival_id


def sum_xg(jugadores: list[dict]) -> float | None:
    vals = [j.get("xG") for j in jugadores if j.get("jugo") and j.get("xG") is not None]
    return round(sum(vals), 2) if vals else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true", help="Browser visible")
    ap.add_argument("--only", help="Procesar solo el partido de esta fecha (YYYY-MM-DD)")
    args = ap.parse_args()

    if not JSON_FILE.exists():
        print(f"ERROR: no existe {JSON_FILE}", file=sys.stderr)
        return 1
    RAW_DIR.mkdir(exist_ok=True)

    payload = json.loads(JSON_FILE.read_text(encoding="utf-8"))
    partidos = payload.get("partidos", [])
    by_date = {p.get("date"): p for p in partidos}

    targets = [p for p in PARTIDOS if not args.only or p["date"] == args.only]
    if not targets:
        print(f"No matchea ningún partido con date={args.only!r}")
        return 1

    headless = not args.headed
    print(f"Browser headless={headless}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=100)
        context = browser.new_context(user_agent=UA, locale="es-AR",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()
        for i, par in enumerate(targets, 1):
            date = par["date"]; rival = par["rival"]; url = par["url"]
            print(f"\n[{i}/{len(targets)}] {date} vs {rival}")
            print(f"  {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(6)
                nd = page.evaluate("() => window.__NEXT_DATA__")
                if not nd:
                    print("  ERROR: sin __NEXT_DATA__")
                    continue
                raw_path = RAW_DIR / f"{date}.json"
                raw_path.write_text(
                    json.dumps(nd, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                aaaj, rival_jug, rival_id = extract_players(nd)
                jugaron_aaaj = sum(1 for j in aaaj if j["jugo"])
                jugaron_rival = sum(1 for j in rival_jug if j["jugo"])
                print(f"  AAAJ: {len(aaaj)} jugadores ({jugaron_aaaj} jugaron)")
                print(f"  Rival (id={rival_id}): {len(rival_jug)} jugadores ({jugaron_rival} jugaron)")
                if date in by_date:
                    target = by_date[date]
                    target["jugadores"] = aaaj
                    target["jugadoresRival"] = rival_jug
                    # Recomputar xG sumando individual (mas confiable que api-sports en LPF)
                    if "stats_partido" in target:
                        sp = target["stats_partido"]
                        new_eq_xg = sum_xg(aaaj)
                        new_rv_xg = sum_xg(rival_jug)
                        if new_eq_xg is not None:
                            sp["equipo"]["xG"] = new_eq_xg
                        if new_rv_xg is not None:
                            sp["rival"]["xG"] = new_rv_xg
                        print(f"  xG: AAAJ={new_eq_xg} rival={new_rv_xg}")
                    print(f"  -> partido actualizado en JSON")
                else:
                    print(f"  WARN: no encontre partido con date={date} en el JSON; skip")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(2)
        browser.close()

    JSON_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nOK escrito a {JSON_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
