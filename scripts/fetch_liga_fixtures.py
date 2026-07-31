"""
fetch_liga_fixtures.py
Genera data/fixtures/liga.json con los partidos del Torneo Clausura 2026 de la
Liga Profesional argentina (api-sports league=128).

Solo se toma **Clausura en adelante** (Apertura queda afuera).
Formato análogo a data/fixtures/mundial.json (para que fixture.html lo consuma
con la misma estructura): array de partidos con home/away (slug de club),
scores, penales, ganador y estado.

La API key sale de scripts/apikey.py (env var API_SPORTS_KEY o scripts/.apikey).
"""
import json, re, sys, urllib.request
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
OUT  = ROOT / 'data' / 'fixtures' / 'liga.json'
LEAGUE, SEASON = 128, 2026

from apikey import get_api_key
API_KEY = get_api_key()   # env API_SPORTS_KEY o scripts/.apikey (gitignored); nunca hardcodeada

# id api-sports -> slug, parseado de js/clubes.js (única fuente de verdad de los 30 clubes)
def _slug_map():
    src = (ROOT / 'js' / 'clubes.js').read_text(encoding='utf-8')
    m = {}
    for mt in re.finditer(r'^\s{2}([a-z0-9]+):\s*\{[^}]*?\bid:\s*(\d+)', src, re.MULTILINE | re.DOTALL):
        m[int(mt.group(2))] = mt.group(1)
    return m

SLUG = _slug_map()

STATUS_MAP = {
    'NS':  (False, False), '1H': (True, False), 'HT': (True, False),
    '2H':  (True, False),  'ET': (True, False), 'BT': (True, False), 'P': (True, False),
    'FT':  (True, True),   'AET': (True, True), 'PEN': (True, True),
    'SUSP':(True, False),  'PST': (False, False), 'CANC': (False, False),
}

def get(path):
    req = urllib.request.Request(f'https://v3.football.api-sports.io{path}',
                                 headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())

def build(f):
    fix, teams, goals = f['fixture'], f['teams'], f['goals']
    score = f.get('score', {}) or {}
    pen = score.get('penalty') or {}
    round_s = f['league']['round']                 # "Clausura - 7"
    fecha = int(round_s.split('-')[1].strip()) if '-' in round_s else None
    short = fix['status']['short']
    started, finished = STATUS_MAP.get(short, (False, False))
    hid, aid = teams['home']['id'], teams['away']['id']
    winner = None
    if teams['home'].get('winner'):   winner = SLUG.get(hid)
    elif teams['away'].get('winner'): winner = SLUG.get(aid)
    return {
        'round':    round_s,
        'fecha':    fecha,
        'api_id':   str(fix['id']),
        'home': {'name': teams['home']['name'], 'id': str(hid), 'slug': SLUG.get(hid, str(hid))},
        'away': {'name': teams['away']['name'], 'id': str(aid), 'slug': SLUG.get(aid, str(aid))},
        'home_score': goals['home'],
        'away_score': goals['away'],
        'home_pen':   pen.get('home'),
        'away_pen':   pen.get('away'),
        'winner':     winner,
        'status': {
            'utcTime':  fix['date'],
            'started':  started,
            'finished': finished,
            'short':    short,
            'elapsed':  fix['status'].get('elapsed'),
        },
    }

def main():
    print(f'Fetching Liga (league={LEAGUE} season={SEASON})...')
    resp = get(f'/fixtures?league={LEAGUE}&season={SEASON}').get('response', [])
    if not resp:
        print('Sin respuesta de la API'); sys.exit(1)
    # Solo Clausura
    clausura = [f for f in resp if f['league']['round'].startswith('Clausura')]
    entries = [build(f) for f in clausura]
    entries.sort(key=lambda e: (e['fecha'] or 0, e['status']['utcTime']))
    OUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'  Guardado: {OUT} ({len(entries)} partidos de Clausura)')
    print('  Estados:', dict(Counter(e['status']['short'] for e in entries)))
    print('  Fechas:', len(set(e['fecha'] for e in entries)))

if __name__ == '__main__':
    main()
