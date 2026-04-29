"""Trae stats globales del partido desde api-sports y las inyecta en
data/estadisticas/{slug}[_copa].json bajo `partidos[].stats_partido`.

Genérico: funciona para cualquier club + competencia (liga, libertadores,
sudamericana). Resuelve el api-sports id desde scripts/clubes_map.py.

Uso:
    # Default = AAAJ liga, los 4 fixtures con votos migrados (Banfield, IndRiv,
    # Atl. Tucumán, Huracán):
    python scripts/fetch_match_stats.py

    # Otros clubes:
    python scripts/fetch_match_stats.py --slug clubatleticoplatense --copa libertadores
    python scripts/fetch_match_stats.py --slug racingclub --copa sudamericana --date 2026-04-29

Sin dependencias externas (urllib stdlib).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from clubes_map import lookup, league_id, estadisticas_path  # noqa: E402

API_KEY = os.environ.get('API_SPORTS_KEY', 'b8bbfc856fd5cf12cd7d697b2b01887d')
SEASON = 2026

# Default: rivales con votos migrados de Formaaajcion (solo AAAJ).
TARGET_RIVALS_AAAJ = {
    449: 'banfield',
    473: 'independienterivadavia',
    455: 'atleticotucuman',
    445: 'huracan',
}

STAT_MAP = {
    'Ball Possession':  'posesion',
    'expected_goals':   'xG',
    'Total Shots':      'tiros',
    'Shots on Goal':    'tirosAlArco',
    'Passes accurate':  'pasesAcertados',
    'Total passes':     'pasesIntentados',
    'Fouls':            'faltas',
    'Corner Kicks':     'corners',
    'Yellow Cards':     'amarillas',
    'Red Cards':        'rojas',
}


def api_get(path: str, params: dict) -> dict:
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    url = f'https://v3.football.api-sports.io/{path}?{qs}'
    req = urllib.request.Request(url, headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def parse_stat_value(raw):
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return raw
    s = str(raw).strip()
    if s == '' or s.lower() == 'null':
        return None
    if s.endswith('%'):
        s = s[:-1].strip()
    try:
        n = float(s)
        return int(n) if n.is_integer() else round(n, 2)
    except ValueError:
        return s


def stats_to_dict(stats_list: list[dict]) -> dict:
    out = {k: None for k in STAT_MAP.values()}
    for s in stats_list or []:
        key = STAT_MAP.get(s.get('type'))
        if not key:
            continue
        out[key] = parse_stat_value(s.get('value'))
    return out


def fecha_from_round(round_str: str, fallback: int) -> int:
    if not round_str:
        return fallback
    m = re.search(r'(\d+)\s*$', round_str)
    return int(m.group(1)) if m else fallback


def sum_player_xg(jugadores: list[dict]) -> float | None:
    if not jugadores:
        return None
    vals = [j.get('xG') for j in jugadores if j.get('jugo') and j.get('xG') is not None]
    return round(sum(vals), 2) if vals else None


def fetch_target_fixtures(team_id: int, league: int, target_rivals: set[int] | None,
                          date_filter: str | None, only_finished: bool):
    """Devuelve los fixtures filtrados, ordenados por fecha."""
    print(f'GET fixtures team={team_id} season={SEASON} league={league}')
    data = api_get('fixtures', {'team': team_id, 'season': SEASON, 'league': league})
    all_fx = data.get('response', [])
    out = []
    for f in all_fx:
        is_home = f['teams']['home']['id'] == team_id
        opp = f['teams']['away' if is_home else 'home']
        if target_rivals is not None and opp['id'] not in target_rivals:
            continue
        d = f['fixture']['date'][:10]
        if date_filter and d != date_filter:
            continue
        st = f['fixture']['status']['short']
        if only_finished and st not in ('FT', 'AET', 'PEN'):
            print(f'  skip (no jugado): vs {opp["name"]} {d} status={st}')
            continue
        out.append(f)
    out.sort(key=lambda f: f['fixture']['date'])
    print(f'  {len(out)} fixtures objetivo encontrados')
    return out


def build_partido_entry(fx: dict, team_id: int, existing: dict | None,
                        rival_slug_map: dict[int, str] | None) -> dict:
    """Construye/actualiza la entrada de partido en el JSON."""
    fid = fx['fixture']['id']
    is_home = fx['teams']['home']['id'] == team_id
    opp = fx['teams']['away' if is_home else 'home']
    opp_id = opp['id']
    g_home = fx['goals']['home'] or 0
    g_away = fx['goals']['away'] or 0
    g_arg = g_home if is_home else g_away
    g_riv = g_away if is_home else g_home
    fecha_num = fecha_from_round(fx['league'].get('round', ''), 0)
    date_str = fx['fixture']['date'][:10]

    # Stats por equipo
    print(f'  GET fixtures/statistics fixture={fid} (vs {opp["name"]})')
    sdata = api_get('fixtures/statistics', {'fixture': fid})
    teams = sdata.get('response', [])
    eq_raw = next((t for t in teams if t['team']['id'] == team_id), None)
    rv_raw = next((t for t in teams if t['team']['id'] == opp_id), None)
    eq_stats = stats_to_dict(eq_raw['statistics'] if eq_raw else [])
    rv_stats = stats_to_dict(rv_raw['statistics'] if rv_raw else [])

    # Fallback xG: sumar xG individual del JSON existente
    if eq_stats.get('xG') is None and existing:
        eq_stats['xG'] = sum_player_xg(existing.get('jugadores', []))
    if rv_stats.get('xG') is None and existing:
        rv_stats['xG'] = sum_player_xg(existing.get('jugadoresRival', []))

    rival_slug = (rival_slug_map or {}).get(opp_id)

    if existing:
        entry = dict(existing)
        entry['fecha'] = fecha_num
        entry['rival'] = existing.get('rival') or opp['name']
        entry['date'] = date_str
        entry['condicion'] = 'Local' if is_home else 'Visitante'
        entry['resultado'] = existing.get('resultado') or f'{g_arg} - {g_riv}'
        entry['rivalId'] = opp_id
        if rival_slug:
            entry['rivalSlug'] = rival_slug
        entry['stats_partido'] = {'equipo': eq_stats, 'rival': rv_stats}
        entry.setdefault('jugadores', [])
        return entry

    new_entry = {
        'fecha': fecha_num,
        'rival': opp['name'],
        'date': date_str,
        'condicion': 'Local' if is_home else 'Visitante',
        'resultado': f'{g_arg} - {g_riv}',
        'rivalId': opp_id,
        'stats_partido': {'equipo': eq_stats, 'rival': rv_stats},
        'jugadores': [],
    }
    if rival_slug:
        new_entry['rivalSlug'] = rival_slug
    return new_entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', default='argentinosjuniors',
                    help='Club (slug TribunApp). Default: argentinosjuniors')
    ap.add_argument('--copa', default='', choices=['', 'libertadores', 'sudamericana'],
                    help='Vacío = liga; libertadores | sudamericana')
    ap.add_argument('--date', default=None,
                    help='Filtrar a un solo partido por fecha YYYY-MM-DD')
    ap.add_argument('--all', action='store_true',
                    help='Para AAAJ liga: trae los 4 rivales con votos migrados (default). '
                         'Para otros clubes: trae todos los partidos jugados.')
    ap.add_argument('--include-pending', action='store_true',
                    help='Incluir partidos no jugados aún (default solo FT/AET/PEN)')
    args = ap.parse_args()

    cfg = lookup(args.slug)
    team_id = cfg['apisports']
    league = league_id(args.copa)
    json_file = ROOT / estadisticas_path(args.slug, args.copa)

    # Filtros default
    target_rivals = None
    if args.slug == 'argentinosjuniors' and args.copa == '' and not args.all and not args.date:
        target_rivals = set(TARGET_RIVALS_AAAJ.keys())

    # Leer JSON existente o crear estructura nueva
    if json_file.exists():
        payload = json.loads(json_file.read_text(encoding='utf-8'))
    else:
        json_file.parent.mkdir(parents=True, exist_ok=True)
        temporada = 'Apertura 2026' if args.copa == '' else f'Copa {args.copa.title()} 2026'
        payload = {'club': args.slug, 'temporada': temporada, 'partidos': [], 'acumulado': []}

    partidos = payload.get('partidos', [])
    by_date = {p.get('date'): p for p in partidos}

    fixtures = fetch_target_fixtures(
        team_id, league, target_rivals, args.date, only_finished=not args.include_pending,
    )
    if not fixtures:
        print('Sin fixtures objetivo. Nada que hacer.')
        return 0

    rival_slug_map = TARGET_RIVALS_AAAJ if (args.slug == 'argentinosjuniors' and args.copa == '') else {}

    for i, fx in enumerate(fixtures, 1):
        if i > 1:
            time.sleep(7)  # rate limit api-sports
        date_str = fx['fixture']['date'][:10]
        existing = by_date.get(date_str)
        entry = build_partido_entry(fx, team_id, existing, rival_slug_map)
        if existing:
            idx = partidos.index(existing)
            partidos[idx] = entry
            print(f'  [{i}/{len(fixtures)}] update F{entry["fecha"]} vs {entry["rival"]} ({date_str})')
        else:
            partidos.append(entry)
            print(f'  [{i}/{len(fixtures)}] add    F{entry["fecha"]} vs {entry["rival"]} ({date_str})')

    partidos.sort(key=lambda p: (p.get('date') or '', p.get('fecha') or 0))
    payload['partidos'] = partidos

    json_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nOK escrito a {json_file.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
