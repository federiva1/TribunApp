"""
Genera data/fixtures/{slug}.json (Liga) y data/fixtures/{slug}_libertadores.json /
data/fixtures/{slug}_sudamericana.json para los clubes que juegan copas.

Uso:
    python scripts/fetch_fixtures.py           # liga + copas
    python scripts/fetch_fixtures.py --liga    # solo liga
    python scripts/fetch_fixtures.py --copas   # solo copas

Requiere Python 3.7+ y urllib (stdlib, sin dependencias externas).
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from apikey import API_KEY
SEASON     = 2026
OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'fixtures'

CLUBES = {
    'velezsarsfield':           438,
    'estudiantes':              450,
    'bocajuniors':              451,
    'defensayjusticia':         442,
    'union':                    441,
    'lanus':                    446,
    'talleres':                 456,
    'independiente':            453,
    'sanlorenzo':               460,
    'clubatleticoplatense':     1064,
    'gimnasiamendoza':          1066,
    'centralcordobadesantiago': 1065,
    'instituto':                478,
    'deportivoriestra':         476,
    'newellsoldboys':           457,
    'independienterivadavia':   473,
    'riverplate':               435,
    'argentinosjuniors':        458,
    'belgrano':                 440,
    'racingclub':               436,
    'rosariocentral':           437,
    'tigre':                    452,
    'barracascentral':          2432,
    'sarmiento':                474,
    'huracan':                  445,
    'gimnasialp':               434,
    'banfield':                 449,
    'atleticotucuman':          455,
    'aldosivi':                 463,
    'estudiantesderiocuarto':   2424,
}

# league_id → suffix
COPAS = {
    13: {  # Libertadores
        'suffix': 'libertadores',
        'slugs': [
            'estudiantes', 'independienterivadavia', 'bocajuniors',
            'clubatleticoplatense', 'lanus', 'rosariocentral',
        ],
    },
    11: {  # Sudamericana
        'suffix': 'sudamericana',
        'slugs': [
            'tigre', 'sanlorenzo', 'racingclub',
            'deportivoriestra', 'riverplate', 'barracascentral',
            # Tercero del grupo de Libertadores → cruza a octavos de Sudamericana.
            # Mantiene también su archivo _libertadores (historia de la fase de grupos).
            'bocajuniors',
        ],
    },
}


def fetch_fixtures(team_id, league_id):
    url = (f'https://v3.football.api-sports.io/fixtures'
           f'?team={team_id}&season={SEASON}&league={league_id}')
    req = urllib.request.Request(url, headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())['response']


def build_entries(fixtures, team_id):
    fixtures = sorted(fixtures, key=lambda f: f['fixture']['date'])
    entries = []
    for num, f in enumerate(fixtures, 1):
        is_home = f['teams']['home']['id'] == team_id
        opp     = f['teams']['away' if is_home else 'home']
        st      = f['fixture']['status']['short']
        played  = st in ('FT', 'AET', 'PEN')
        if played:
            g_home  = f['goals']['home'] or 0
            g_away  = f['goals']['away'] or 0
            g_arg   = g_home if is_home else g_away
            g_rival = g_away if is_home else g_home
            goles   = [g_arg, g_rival]
        else:
            goles = None
        entries.append({
            'num':   num,
            'fecha': f['fixture']['date'][:10],
            'rival': opp['name'],
            'local': is_home,
            'goles': goles,
        })
    return entries


def write_json(path, entries):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(entries, fh, ensure_ascii=False, indent=2)


def run_liga():
    print('=== LIGA PROFESIONAL (league=128) ===')
    total = len(CLUBES)
    for i, (slug, team_id) in enumerate(CLUBES.items(), 1):
        if slug == 'argentinosjuniors':
            print(f'[{i}/{total}] {slug} — skipped (manual file)')
            if i < total: time.sleep(7)
            continue
        print(f'[{i}/{total}] {slug} (id={team_id})... ', end='', flush=True)
        try:
            fixtures = fetch_fixtures(team_id, 128)
            entries  = build_entries(fixtures, team_id)
            write_json(OUTPUT_DIR / f'{slug}.json', entries)
            played = sum(1 for e in entries if e['goles'] is not None)
            print(f'{len(entries)} partidos ({played} jugados)')
        except Exception as e:
            print(f'ERROR: {e}')
        if i < total:
            time.sleep(7)


def run_copas():
    print('=== COPAS INTERNACIONALES ===')
    for league_id, info in COPAS.items():
        suffix = info['suffix']
        slugs  = info['slugs']
        print(f'\n--- {suffix.upper()} (league={league_id}) ---')
        for i, slug in enumerate(slugs, 1):
            team_id = CLUBES.get(slug)
            if not team_id:
                print(f'  [{i}/{len(slugs)}] {slug} — no encontrado en CLUBES')
                continue
            print(f'  [{i}/{len(slugs)}] {slug} (id={team_id})... ', end='', flush=True)
            try:
                fixtures = fetch_fixtures(team_id, league_id)
                entries  = build_entries(fixtures, team_id)
                write_json(OUTPUT_DIR / f'{slug}_{suffix}.json', entries)
                played = sum(1 for e in entries if e['goles'] is not None)
                print(f'{len(entries)} partidos ({played} jugados)')
            except Exception as e:
                print(f'ERROR: {e}')
            if i < len(slugs):
                time.sleep(7)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    if '--liga' in args:
        run_liga()
    elif '--copas' in args:
        run_copas()
    else:
        run_liga()
        print()
        run_copas()
    print('\nListo.')


if __name__ == '__main__':
    main()
