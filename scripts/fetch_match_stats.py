"""Trae stats globales del partido desde api-sports y las inyecta en
data/estadisticas/{slug}.json bajo `partidos[].stats_partido`.

Por ahora hardcodeado para argentinosjuniors y los 4 rivales con votos
migrados de Formaaajcion: Banfield, Independiente Rivadavia, Atlético
Tucumán, Huracán. La fecha se toma de `league.round` de api-football.

Uso:
    python scripts/fetch_match_stats.py

Sin dependencias externas (urllib stdlib).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

API_KEY = os.environ.get("API_SPORTS_KEY", "b8bbfc856fd5cf12cd7d697b2b01887d")
SEASON = 2026
LEAGUE = 128  # Liga Profesional
TEAM_ID = 458  # Argentinos Juniors

# Rivales objetivo: id api-sports → slug (para escudo)
TARGET_RIVALS = {
    449: "banfield",
    473: "independienterivadavia",
    455: "atleticotucuman",
    445: "huracan",
}

ROOT = Path(__file__).resolve().parent.parent
JSON_FILE = ROOT / "data" / "estadisticas" / "argentinosjuniors.json"

# api-sports stat type → clave nuestra
STAT_MAP = {
    "Ball Possession":  "posesion",
    "expected_goals":   "xG",
    "Total Shots":      "tiros",
    "Shots on Goal":    "tirosAlArco",
    "Passes accurate":  "pasesAcertados",
    "Total passes":     "pasesIntentados",
    "Fouls":            "faltas",
    "Corner Kicks":     "corners",
    "Yellow Cards":     "amarillas",
    "Red Cards":        "rojas",
}


def api_get(path: str, params: dict) -> dict:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://v3.football.api-sports.io/{path}?{qs}"
    req = urllib.request.Request(url, headers={"x-apisports-key": API_KEY})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def parse_stat_value(raw):
    """Normaliza valores. '43%' → 43, '1.91' → 1.91, None → None."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return raw
    s = str(raw).strip()
    if s == "" or s.lower() == "null":
        return None
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        n = float(s)
        return int(n) if n.is_integer() else round(n, 2)
    except ValueError:
        return s


def stats_to_dict(stats_list: list[dict]) -> dict:
    """Convierte la lista raw de api-sports a un dict con nuestras claves."""
    out = {k: None for k in STAT_MAP.values()}
    for s in stats_list or []:
        key = STAT_MAP.get(s.get("type"))
        if not key:
            continue
        out[key] = parse_stat_value(s.get("value"))
    return out


def fecha_from_round(round_str: str, fallback: int) -> int:
    """Extrae el número de fecha de strings tipo 'Apertura - 14'."""
    if not round_str:
        return fallback
    m = re.search(r"(\d+)\s*$", round_str)
    return int(m.group(1)) if m else fallback


def sum_player_xg(jugadores: list[dict]) -> float | None:
    """xG agregado del equipo a partir de los jugadores que jugaron."""
    if not jugadores:
        return None
    vals = [j.get("xG") for j in jugadores if j.get("jugo") and j.get("xG") is not None]
    if not vals:
        return None
    return round(sum(vals), 2)


def fetch_target_fixtures():
    """Devuelve los fixtures vs los 4 rivales objetivo, jugados, ordenados por fecha."""
    print(f"GET fixtures team={TEAM_ID} season={SEASON} league={LEAGUE}")
    data = api_get("fixtures", {"team": TEAM_ID, "season": SEASON, "league": LEAGUE})
    all_fx = data.get("response", [])
    out = []
    for f in all_fx:
        is_home = f["teams"]["home"]["id"] == TEAM_ID
        opp = f["teams"]["away" if is_home else "home"]
        if opp["id"] not in TARGET_RIVALS:
            continue
        st = f["fixture"]["status"]["short"]
        if st not in ("FT", "AET", "PEN"):
            print(f"  skip (no jugado): vs {opp['name']} status={st}")
            continue
        out.append(f)
    out.sort(key=lambda f: f["fixture"]["date"])
    print(f"  {len(out)} fixtures objetivo encontrados")
    return out


def build_partido_entry(fx: dict, existing: dict | None) -> dict:
    """Construye/actualiza la entrada de partido en el JSON."""
    fid = fx["fixture"]["id"]
    is_home = fx["teams"]["home"]["id"] == TEAM_ID
    opp = fx["teams"]["away" if is_home else "home"]
    opp_id = opp["id"]
    g_home = fx["goals"]["home"] or 0
    g_away = fx["goals"]["away"] or 0
    g_arg = g_home if is_home else g_away
    g_riv = g_away if is_home else g_home
    fecha_num = fecha_from_round(fx["league"].get("round", ""), 0)
    date_str = fx["fixture"]["date"][:10]

    # Stats por equipo
    print(f"  GET fixtures/statistics fixture={fid} (vs {opp['name']})")
    sdata = api_get("fixtures/statistics", {"fixture": fid})
    teams = sdata.get("response", [])
    eq_raw = next((t for t in teams if t["team"]["id"] == TEAM_ID), None)
    rv_raw = next((t for t in teams if t["team"]["id"] == opp_id), None)
    eq_stats = stats_to_dict(eq_raw["statistics"] if eq_raw else [])
    rv_stats = stats_to_dict(rv_raw["statistics"] if rv_raw else [])

    # Fallback xG: sumar xG individual de jugadores existentes (solo AAAJ)
    if eq_stats.get("xG") is None and existing:
        eq_stats["xG"] = sum_player_xg(existing.get("jugadores", []))

    # Si la entrada ya existía, conservamos jugadores y resultado/condicion del JSON.
    if existing:
        entry = dict(existing)
        entry["fecha"] = fecha_num
        entry["rival"] = existing.get("rival") or opp["name"]
        entry["date"] = date_str
        entry["condicion"] = "Local" if is_home else "Visitante"
        entry["resultado"] = existing.get("resultado") or f"{g_arg} - {g_riv}"
        entry["rivalId"] = opp_id
        entry["rivalSlug"] = TARGET_RIVALS[opp_id]
        entry["stats_partido"] = {"equipo": eq_stats, "rival": rv_stats}
        # asegurar que jugadores exista
        entry.setdefault("jugadores", [])
        return entry

    # Nueva entrada (IndRiv y AtlTuc, sin stats individuales todavía)
    return {
        "fecha": fecha_num,
        "rival": opp["name"],
        "date": date_str,
        "condicion": "Local" if is_home else "Visitante",
        "resultado": f"{g_arg} - {g_riv}",
        "rivalId": opp_id,
        "rivalSlug": TARGET_RIVALS[opp_id],
        "stats_partido": {"equipo": eq_stats, "rival": rv_stats},
        "jugadores": [],
    }


def main() -> int:
    if not JSON_FILE.exists():
        print(f"ERROR: no encuentro {JSON_FILE}", file=sys.stderr)
        return 1

    payload = json.loads(JSON_FILE.read_text(encoding="utf-8"))
    partidos = payload.get("partidos", [])

    fixtures = fetch_target_fixtures()
    if not fixtures:
        print("Sin fixtures objetivo. Nada que hacer.")
        return 0

    # Index de partidos existentes por date
    by_date = {p.get("date"): p for p in partidos}

    for i, fx in enumerate(fixtures, 1):
        if i > 1:
            time.sleep(7)  # rate limit api-sports
        date_str = fx["fixture"]["date"][:10]
        existing = by_date.get(date_str)
        entry = build_partido_entry(fx, existing)
        if existing:
            idx = partidos.index(existing)
            partidos[idx] = entry
            print(f"  [{i}/{len(fixtures)}] update F{entry['fecha']} vs {entry['rival']} ({date_str})")
        else:
            partidos.append(entry)
            print(f"  [{i}/{len(fixtures)}] add    F{entry['fecha']} vs {entry['rival']} ({date_str})")

    # Reordenar por fecha (num) ascendente
    partidos.sort(key=lambda p: p.get("fecha") or 0)
    payload["partidos"] = partidos

    JSON_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nOK escrito a {JSON_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
