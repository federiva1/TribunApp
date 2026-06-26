"""
fetch_mundial_fixtures.py
Sincroniza data/fixtures/mundial.json desde api-sports (league=1, season=2026).
Preserva los campos stats_id y pageUrl del JSON existente (datos de FotMob).
"""
import os, json, urllib.request, datetime, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT  = ROOT / 'data' / 'fixtures' / 'mundial.json'

from apikey import API_KEY
LEAGUE  = 1
SEASON  = 2026

# Mapping api-sports team id → slug (para escudos y links)
TEAM_SLUG = {
    1532: 'algeria',      26: 'argentina',    20: 'australia',
     775: 'austria',       1: 'belgium',     1113: 'bosniaandherzegovina',
       6: 'brazil',     5529: 'canada',      1533: 'capeverde',
       8: 'colombia',   1508: 'drcongo',        3: 'croatia',
    5530: 'curacao',     770: 'czechia',     2382: 'ecuador',
      32: 'egypt',        10: 'england',        2: 'france',
      25: 'germany',    1504: 'ghana',        2386: 'haiti',
      22: 'iran',       1567: 'iraq',         1501: 'ivorycoast',
      12: 'japan',      1548: 'jordan',         16: 'mexico',
      31: 'morocco',    1118: 'netherlands',  4673: 'newzealand',
    1090: 'norway',       11: 'panama',       2380: 'paraguay',
      27: 'portugal',   1569: 'qatar',          23: 'saudiarabia',
    1108: 'scotland',     13: 'senegal',      1531: 'southafrica',
      17: 'southkorea',    9: 'spain',           5: 'sweden',
      15: 'switzerland',  28: 'tunisia',       777: 'turkiye',
    2384: 'usa',           7: 'uruguay',      1568: 'uzbekistan',
}

# Mapping round api-sports → round interno
ROUND_MAP = {
    'Group Stage - 1': '1',
    'Group Stage - 2': '2',
    'Group Stage - 3': '3',
    'Round of 32':     '1/32',
    'Round of 16':     '1/16',
    'Quarter-finals':  '1/4',
    'Semi-finals':     '1/2',
    '3rd Place Final': 'bronze',
    'Final':           'final',
}

ROUND_NAME = {
    '1': 'Fase de Grupos - Jornada 1',
    '2': 'Fase de Grupos - Jornada 2',
    '3': 'Fase de Grupos - Jornada 3',
    '1/32': 'Ronda de 32',
    '1/16': 'Octavos de Final',
    '1/4':  'Cuartos de Final',
    '1/2':  'Semifinales',
    'bronze': 'Tercer Puesto',
    'final':  'Final',
}

STATUS_MAP = {
    'NS':  {'started': False, 'finished': False, 'cancelled': False},
    '1H':  {'started': True,  'finished': False, 'cancelled': False},
    'HT':  {'started': True,  'finished': False, 'cancelled': False},
    '2H':  {'started': True,  'finished': False, 'cancelled': False},
    'ET':  {'started': True,  'finished': False, 'cancelled': False},
    'BT':  {'started': True,  'finished': False, 'cancelled': False},
    'P':   {'started': True,  'finished': False, 'cancelled': False},
    'FT':  {'started': True,  'finished': True,  'cancelled': False},
    'AET': {'started': True,  'finished': True,  'cancelled': False},
    'PEN': {'started': True,  'finished': True,  'cancelled': False},
    'CANC':{'started': False, 'finished': False, 'cancelled': True},
    'PST': {'started': False, 'finished': False, 'cancelled': False},
    'SUSP':{'started': True,  'finished': False, 'cancelled': False},
}

def get(path):
    url = f'https://v3.football.api-sports.io{path}'
    req = urllib.request.Request(url, headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def fetch_fixtures():
    d = get(f'/fixtures?league={LEAGUE}&season={SEASON}')
    if d.get('errors'):
        print('Error API:', d['errors'])
        sys.exit(1)
    return d['response']

def build_entry(f, existing_by_id):
    fix   = f['fixture']
    teams = f['teams']
    goals = f['goals']
    league= f['league']

    api_id   = str(fix['id'])
    home_id  = teams['home']['id']
    away_id  = teams['away']['id']
    home_slug= TEAM_SLUG.get(home_id, teams['home']['name'].lower().replace(' ', ''))
    away_slug= TEAM_SLUG.get(away_id, teams['away']['name'].lower().replace(' ', ''))
    round_key= ROUND_MAP.get(league['round'], league['round'])
    status_s = fix['status']['short']
    st       = STATUS_MAP.get(status_s, {'started': False, 'finished': False, 'cancelled': False})

    # Preservar stats_id y pageUrl del JSON existente si había entrada previa
    prev = existing_by_id.get(api_id, {})

    return {
        'round':      round_key,
        'roundName':  ROUND_NAME.get(round_key, round_key),
        'api_id':     api_id,                        # id de api-sports (para live scores)
        'stats_id':   prev.get('stats_id', None),    # id de datos FotMob, si existe
        'pageUrl':    prev.get('pageUrl', None),
        'home': {
            'name':      teams['home']['name'],
            'shortName': teams['home']['name'],
            'id':        str(home_id),
            'slug':      home_slug,
        },
        'away': {
            'name':      teams['away']['name'],
            'shortName': teams['away']['name'],
            'id':        str(away_id),
            'slug':      away_slug,
        },
        'home_score': goals['home'],
        'away_score': goals['away'],
        'group':      league.get('round', '').replace('Group Stage - ', 'Group ') if 'Group Stage' in league.get('round','') else None,
        'status': {
            'utcTime':   fix['date'],
            'started':   st['started'],
            'finished':  st['finished'],
            'cancelled': st['cancelled'],
            'elapsed':   fix['status'].get('elapsed'),
            'short':     status_s,
        },
    }

def main():
    # Cargar JSON existente para preservar stats_id / pageUrl de amistosos FotMob
    existing = []
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding='utf-8'))

    # Index por api_id (si ya tenía) y también preservar amistosos (no vienen de api-sports)
    existing_by_id = {e['api_id']: e for e in existing if e.get('api_id')}
    amistosos = [e for e in existing if e.get('round') == 'amistoso']

    print(f'Fetching fixtures league={LEAGUE} season={SEASON}...')
    fixtures = fetch_fixtures()
    print(f'  {len(fixtures)} partidos recibidos')

    # Ordenar por fecha
    fixtures.sort(key=lambda f: f['fixture']['date'])

    entries = [build_entry(f, existing_by_id) for f in fixtures]

    # Amistosos al principio (ya jugados, datos de FotMob)
    resultado = amistosos + entries

    OUT.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'  Guardado: {OUT} ({len(resultado)} partidos total)')

    # Mostrar resumen de estados
    from collections import Counter
    estados = Counter(e['status']['short'] for e in entries)
    print('  Estados:', dict(estados))

if __name__ == '__main__':
    main()
