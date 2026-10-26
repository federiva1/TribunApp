"""
fetch_mundial_standings.py
Actualiza data/estado_torneo.json con standings del Mundial 2026 desde api-sports.
"""
import os, json, urllib.request, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT  = ROOT / 'data' / 'estado_torneo.json'

from apikey import api_headers
LEAGUE  = 1
SEASON  = 2026

TEAM_SLUG = {
    1532:'algeria',26:'argentina',20:'australia',775:'austria',1:'belgium',
    1113:'bosniaandherzegovina',6:'brazil',5529:'canada',1533:'capeverde',
    8:'colombia',1508:'drcongo',3:'croatia',5530:'curacao',770:'czechia',
    2382:'ecuador',32:'egypt',10:'england',2:'france',25:'germany',1504:'ghana',
    2386:'haiti',22:'iran',1567:'iraq',1501:'ivorycoast',12:'japan',1548:'jordan',
    16:'mexico',31:'morocco',1118:'netherlands',4673:'newzealand',1090:'norway',
    11:'panama',2380:'paraguay',27:'portugal',1569:'qatar',23:'saudiarabia',
    1108:'scotland',13:'senegal',1531:'southafrica',17:'southkorea',9:'spain',
    5:'sweden',15:'switzerland',28:'tunisia',777:'turkiye',2384:'usa',7:'uruguay',
    1568:'uzbekistan',
}

def get(path):
    url = f'https://v3.football.api-sports.io{path}'
    req = urllib.request.Request(url, headers=api_headers())
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def detect_fase(standings_groups):
    """Detectar en qué fase está el torneo según rondas disponibles."""
    # Por ahora solo hay fase de grupos; se amplía a medida que avanza el torneo
    return 'grupos'

def main():
    d = get(f'/standings?league={LEAGUE}&season={SEASON}')
    if d.get('errors') and d['errors'] != []:
        print('Error API:', d['errors'])
        sys.exit(1)

    resp = d.get('response', [])
    if not resp:
        print('Sin datos de standings todavía')
        return

    standings_raw = resp[0]['league']['standings']

    tablas   = {}
    clasificados = []
    eliminados   = []

    for grupo in standings_raw:
        if not grupo:
            continue
        letra = grupo[0]['group'].replace('Group ', '')  # "Group A" → "A"
        tabla_grupo = []
        for eq in grupo:
            slug = TEAM_SLUG.get(eq['team']['id'])
            if not slug:
                slug = eq['team']['name'].lower().replace(' ', '').replace('&','')
            stats = eq.get('all', {})
            tabla_grupo.append({
                'slug':  slug,
                'pts':   eq['points'],
                'pj':    stats.get('played', 0) or 0,
                'pg':    stats.get('win', 0) or 0,
                'pe':    stats.get('draw', 0) or 0,
                'pp':    stats.get('lose', 0) or 0,
                'gf':    (stats.get('goals') or {}).get('for', 0) or 0,
                'gc':    (stats.get('goals') or {}).get('against', 0) or 0,
                'dg':    eq.get('goalsDiff', 0) or 0,
                'desc':  eq.get('description', ''),
            })
            desc = (eq.get('description') or '').lower()
            if 'qualified' in desc or 'round of 16' in desc or 'playoffs' in desc:
                pass  # clasificados se determinan post grupos
            if eq.get('status') == 'eliminated':
                eliminados.append(slug)
        tablas[letra] = tabla_grupo

    fase = detect_fase(standings_raw)

    estado = {
        'fase':       fase,
        'clasificados': clasificados,
        'eliminados':   eliminados,
        'tablas':       tablas,
    }

    OUT.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'estado_torneo.json actualizado — fase: {fase}, grupos: {list(tablas.keys())}')

if __name__ == '__main__':
    main()
