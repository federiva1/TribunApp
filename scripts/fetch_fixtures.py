"""
Genera data/fixtures/{slug}.json para todos los clubes de la Liga Profesional.
Llama a api-sports una vez por club (league=128, season=2026).

Uso:
    python scripts/fetch_fixtures.py

Requiere Python 3.7+ y urllib (stdlib, sin dependencias externas).
"""

import json
import os
import time
import urllib.request
from pathlib import Path

API_KEY    = 'b8bbfc856fd5cf12cd7d697b2b01887d'
LEAGUE     = 128
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


def fetch_fixtures(team_id):
    url = f'https://v3.football.api-sports.io/fixtures?team={team_id}&season={SEASON}&league={LEAGUE}'
    req = urllib.request.Request(url, headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())['response']


def build_entry(f, team_id):
    is_home = f['teams']['home']['id'] == team_id
    opp     = f['teams']['away' if is_home else 'home']
    rival   = opp['name']
    local   = is_home
    fecha   = f['fixture']['date'][:10]  # YYYY-MM-DD

    st = f['fixture']['status']['short']
    played = st in ('FT', 'AET', 'PEN')

    if played:
        g_home = f['goals']['home'] or 0
        g_away = f['goals']['away'] or 0
        g_arg  = g_home if is_home else g_away
        g_rival = g_away if is_home else g_home
        goles = [g_arg, g_rival]
    else:
        goles = None

    return {
        'fecha': fecha,
        'rival': rival,
        'local': local,
        'goles': goles,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    total = len(CLUBES)

    for i, (slug, team_id) in enumerate(CLUBES.items(), 1):
        out_path = OUTPUT_DIR / f'{slug}.json'

        # Skip argentinosjuniors — already hand-crafted with correct rival names
        if slug == 'argentinosjuniors':
            print(f'[{i}/{total}] {slug} — skipped (manual file)')
            continue

        print(f'[{i}/{total}] {slug} (id={team_id})... ', end='', flush=True)
        try:
            fixtures = fetch_fixtures(team_id)
            fixtures.sort(key=lambda f: f['fixture']['date'])

            entries = []
            for num, f in enumerate(fixtures, 1):
                entry = build_entry(f, team_id)
                entry['num'] = num
                # Reorder keys for readability
                entries.append({
                    'num':   entry['num'],
                    'fecha': entry['fecha'],
                    'rival': entry['rival'],
                    'local': entry['local'],
                    'goles': entry['goles'],
                })

            with open(out_path, 'w', encoding='utf-8') as fh:
                json.dump(entries, fh, ensure_ascii=False, indent=2)

            played = sum(1 for e in entries if e['goles'] is not None)
            print(f'{len(entries)} partidos ({played} jugados)')

        except Exception as e:
            print(f'ERROR: {e}')

        # Respect api-sports rate limit (free: 100 req/day, ~10 req/min)
        if i < total:
            time.sleep(7)

    print('\nListo. Archivos generados en data/fixtures/')


if __name__ == '__main__':
    main()
