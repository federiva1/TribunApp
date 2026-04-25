"""
Actualiza data/estado.json consultando api-sports para cada club.
- Si el partido del rival actual está con status FT/AET/PEN → puntajesOpen: true
- Si no hay partido en curso o no terminó → puntajesOpen: false

Uso:
    python scripts/update_estado.py

Requiere la variable de entorno API_SPORTS_KEY.
"""

import json
import os
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

API_KEY    = os.environ.get('API_SPORTS_KEY', '')
SEASON     = 2026
BASE_DIR   = Path(__file__).parent.parent
ESTADO_PATH = BASE_DIR / 'data' / 'estado.json'

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

FINISHED = {'FT', 'AET', 'PEN'}


def fetch_fixtures_today(team_id):
    today = date.today().isoformat()
    url = (f'https://v3.football.api-sports.io/fixtures'
           f'?team={team_id}&season={SEASON}&league=128&date={today}')
    req = urllib.request.Request(url, headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())['response']


def main():
    if not API_KEY:
        print('ERROR: API_SPORTS_KEY no definida', file=sys.stderr)
        sys.exit(1)

    with open(ESTADO_PATH, encoding='utf-8') as f:
        estado = json.load(f)

    slugs = list(CLUBES.keys())
    total = len(slugs)
    changed = False

    for i, slug in enumerate(slugs, 1):
        team_id = CLUBES[slug]
        entry = estado.get(slug, {})
        rival = entry.get('rival', '')
        match_date = entry.get('matchDate', '')
        already_open = entry.get('puntajesOpen', False)

        # Solo consultar si hay partido configurado y aún no está abierto
        if not rival or already_open:
            print(f'[{i}/{total}] {slug} — skip (rival={repr(rival)}, open={already_open})')
            if i < total:
                time.sleep(6)
            continue

        print(f'[{i}/{total}] {slug} (id={team_id})... ', end='', flush=True)
        try:
            fixtures = fetch_fixtures_today(team_id)
            finished = any(
                f['fixture']['status']['short'] in FINISHED
                for f in fixtures
            )
            if finished:
                estado[slug]['puntajesOpen'] = True
                changed = True
                print('FT → puntajesOpen=true')
            else:
                print(f'no terminado ({len(fixtures)} partidos hoy)')
        except Exception as e:
            print(f'ERROR: {e}')

        if i < total:
            time.sleep(6)

    if changed:
        with open(ESTADO_PATH, 'w', encoding='utf-8') as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        print('\nEstado actualizado.')
    else:
        print('\nSin cambios.')


if __name__ == '__main__':
    main()
