"""Rellena los dorsales en blanco de data/planteles/{slug}.json cruzando con el
plantel oficial de api-sports (players/squads), que trae el número de todo el
plantel actual. NO toca los números ya presentes — solo completa los vacíos.

Motivo: FotMob (fuente de los planteles) a veces no lista el dorsal de un jugador
(quedaba vacío tras el fix de scraper_planteles). api-sports sí lo tiene para el
plantel actual, así que "los que juegan" recuperan su número.

Uso:
    python scripts/backfill_plantel_nums.py --dry-run          # previsualiza, no escribe
    python scripts/backfill_plantel_nums.py                    # todos los clubes
    python scripts/backfill_plantel_nums.py independiente racingclub   # solo esos slugs

Matching por nombre (plantel FotMob usa nombre completo; api-sports abrevia
"M. Meza"): exacto normalizado → apellido+inicial único → apellido único.
Lee API_SPORTS_KEY del entorno / scripts/.apikey (via apikey.py).
"""
from __future__ import annotations

import json
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from clubes_map import CLUBES          # noqa: E402
from apikey import API_KEY             # noqa: E402

PLANTELES = ROOT / 'data' / 'planteles'
SEASON = 2026


def norm(s: str) -> str:
    s = (s or '').lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('.', ' ').strip()


def toks(s: str) -> list[str]:
    return [t for t in norm(s).split() if t]


def api_squad(team_id: int) -> list[dict]:
    url = f'https://v3.football.api-sports.io/players/squads?team={team_id}'
    req = urllib.request.Request(url, headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    resp = data.get('response', [])
    return resp[0].get('players', []) if resp else []


def build_index(squad: list[dict]):
    """Devuelve (by_full, by_last) con nombre normalizado -> (num, name)."""
    by_full, by_last = {}, {}
    for p in squad:
        num = p.get('number')
        if num is None:
            continue
        name = p.get('name', '')
        tk = toks(name)
        if not tk:
            continue
        by_full[' '.join(tk)] = (str(num), name)
        by_last.setdefault(tk[-1], []).append((str(num), name, tk[0]))
    return by_full, by_last


def match_num(plantel_name: str, by_full: dict, by_last: dict):
    tk = toks(plantel_name)
    if not tk:
        return None
    full = ' '.join(tk)
    if full in by_full:
        return by_full[full]
    cands = by_last.get(tk[-1], [])
    if len(cands) == 1:
        return (cands[0][0], cands[0][1])
    if len(cands) > 1:
        # Desambiguar por inicial del nombre
        first_init = tk[0][0]
        narrowed = [c for c in cands if c[2][0] == first_init]
        if len(narrowed) == 1:
            return (narrowed[0][0], narrowed[0][1])
    return None


def fill_blanks(apisports_id: int, players: list[dict]) -> list[str]:
    """Rellena IN-PLACE los `num` vacíos de `players` con el dorsal de api-sports
    (players/squads). No pisa números existentes. Devuelve ['Nombre=num', ...] de
    los rellenados. Reutilizable desde fetch_planteles_liga.py."""
    blancos = [p for p in players if not str(p.get('num') or '').strip()]
    if not blancos:
        return []
    by_full, by_last = build_index(api_squad(apisports_id))
    filled = []
    for p in blancos:
        m = match_num(p.get('name', ''), by_full, by_last)
        if m:
            p['num'] = m[0]
            filled.append(f"{p.get('name')}={m[0]}")
    return filled


def main() -> int:
    dry = '--dry-run' in sys.argv
    only = {a for a in sys.argv[1:] if not a.startswith('--')}

    total_fill = 0
    total_blank_left = 0
    for slug, cfg in CLUBES.items():
        if only and slug not in only:
            continue
        pf = PLANTELES / f'{slug}.json'
        if not pf.exists():
            continue
        plantel = json.loads(pf.read_text(encoding='utf-8'))
        if not isinstance(plantel, list):
            continue
        blancos = [p for p in plantel if not str(p.get('num') or '').strip()]
        if not blancos:
            continue

        try:
            # fill_blanks muta el plantel en memoria; en dry-run no se persiste.
            filled = fill_blanks(cfg['apisports'], plantel)
        except Exception as e:
            print(f'  ✗ {slug:26s} api-sports ERROR: {e}')
            continue
        left = len(blancos) - len(filled)
        total_fill += len(filled)
        total_blank_left += left

        prefix = '[dry] ' if dry else '      '
        detail = f"  ({', '.join(filled[:5])}{'…' if len(filled) > 5 else ''})" if filled else ''
        print(f"{prefix}{slug:26s} rellenados {len(filled):2d}/{len(blancos):2d}  (quedan {left} sin número){detail}")

        if not dry and filled:
            pf.write_text(json.dumps(plantel, ensure_ascii=False, indent=2), encoding='utf-8')
        time.sleep(0.4)  # rate-limit api-sports

    tag = '[dry-run] ' if dry else ''
    print(f"\n{tag}Total rellenados: {total_fill} · sin número tras cruce: {total_blank_left}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
