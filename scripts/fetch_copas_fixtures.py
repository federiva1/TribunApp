"""
fetch_copas_fixtures.py
Genera data/fixtures/copas.json con los partidos de la instancia ACTUAL de
Copa Libertadores (league=13) y Copa Sudamericana (league=11) 2026 en los que
juega un equipo argentino.

- Solo fase de eliminación (knockout). Incluye la serie ACTUAL de cada club
  argentino (sus partidos de su ronda más avanzada). Las rondas pueden estar
  solapadas — caso real: Boca ya con los Cuartos programados mientras River
  tenía pendiente la revancha de la ronda anterior — así que NO se queda con
  una sola ronda: conserva toda serie con partidos sin terminar, más las de la
  ronda más avanzada. Un club eliminado en una ronda vieja (serie terminada y
  ronda superada) queda afuera. `ronda` top-level = la más avanzada del set;
  cada partido lleva además su `ronda` propia.
- Rivales extranjeros: se usa el logo de api-sports (media.api-sports.io). Los
  argentinos usan el escudo local (escudos/{slug}.png), por eso guardamos slug.

Formato:
{
  "libertadores": { "ronda": "Octavos de Final", "partidos": [ ... ] },
  "sudamericana": { "ronda": "Dieciseisavos",     "partidos": [ ... ] }
}
"""
import json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT  = ROOT / 'data' / 'fixtures' / 'copas.json'
SEASON = 2026
COPAS = [('libertadores', 13), ('sudamericana', 11)]

from apikey import get_api_key, api_headers
API_KEY = get_api_key()   # env API_SPORTS_KEY o scripts/.apikey (gitignored); nunca hardcodeada

# Rondas de eliminación en orden + etiqueta en español
KO_ORDER = ['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
RONDA_ES = {
    'Round of 32': 'Dieciseisavos', 'Round of 16': 'Octavos de Final',
    'Quarter-finals': 'Cuartos de Final', 'Semi-finals': 'Semifinales', 'Final': 'Final',
}
STATUS_FIN = {'FT', 'AET', 'PEN'}
STATUS_LIVE = {'1H', 'HT', '2H', 'ET', 'BT', 'P', 'SUSP'}

def _slug_map():
    src = (ROOT / 'js' / 'clubes.js').read_text(encoding='utf-8')
    return {int(m.group(2)): m.group(1)
            for m in re.finditer(r'^\s{2}([a-z0-9]+):\s*\{[^}]*?\bid:\s*(\d+)', src, re.MULTILINE | re.DOTALL)}

SLUG = _slug_map()
ARG = set(SLUG)

def get(lg):
    req = urllib.request.Request(
        'https://v3.football.api-sports.io/fixtures?league=%d&season=%d' % (lg, SEASON),
        headers=api_headers())
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read()).get('response', [])

def side(t):
    """Info de un equipo: slug (si es argentino) + logo (api-sports para extranjeros)."""
    if t['id'] in ARG:
        return {'name': t['name'], 'slug': SLUG[t['id']], 'logo': None, 'arg': True}
    return {'name': t['name'], 'slug': None, 'logo': t.get('logo'), 'arg': False}

def build(f, ronda=None):
    fix, teams, goals = f['fixture'], f['teams'], f['goals']
    score = f.get('score', {}) or {}
    pen = score.get('penalty') or {}
    winner = None
    if teams['home'].get('winner'):   winner = 'home'
    elif teams['away'].get('winner'): winner = 'away'
    return {
        'api_id': str(fix['id']),
        'utcTime': fix['date'],
        'short': fix['status']['short'],
        'home': side(teams['home']),
        'away': side(teams['away']),
        'home_score': goals['home'],
        'away_score': goals['away'],
        'home_pen': pen.get('home'),
        'away_pen': pen.get('away'),
        'winner': winner,
        'ronda': RONDA_ES.get(ronda, ronda),
    }

def ronda_actual(fixtures):
    """Serie KO actual de cada club argentino, tolerando rondas solapadas.

    Antes se quedaba con UNA sola ronda (la más avanzada con algún partido sin
    terminar), lo que borraba del JSON a un club con la revancha de una ronda
    anterior pendiente apenas otro club ya tenía la ronda siguiente programada
    (caso real: Boca con Cuartos NS ⇒ desaparecía River, que aún debía la
    vuelta vs Santa Fe). Ahora, por cada club argentino se toma su ronda más
    avanzada y se incluye esa serie si tiene partidos sin terminar O si es la
    ronda más avanzada de la copa (así los recién clasificados no desaparecen
    entre que ganan y se cargan los cruces nuevos). Un club cuya última serie
    está terminada en una ronda ya superada queda afuera (eliminado o ya
    reflejado en la ronda siguiente).

    Devuelve (ronda_mas_avanzada, [(ronda, fixture), ...]).
    """
    por_ronda = {}
    for f in fixtures:
        r = f['league']['round']
        if r not in KO_ORDER:
            continue
        if f['teams']['home']['id'] in ARG or f['teams']['away']['id'] in ARG:
            por_ronda.setdefault(r, []).append(f)
    if not por_ronda:
        return None, []
    mas_avanzada = max(por_ronda, key=lambda r: KO_ORDER.index(r))

    def _es_del(f, tid):
        return f['teams']['home']['id'] == tid or f['teams']['away']['id'] == tid

    clubes = {t['id'] for fs in por_ronda.values() for f in fs
              for t in (f['teams']['home'], f['teams']['away']) if t['id'] in ARG}
    elegidos = {}   # fixture_id -> (ronda, fixture)
    for tid in clubes:
        rondas_club = [r for r, fs in por_ronda.items() if any(_es_del(f, tid) for f in fs)]
        r = max(rondas_club, key=lambda x: KO_ORDER.index(x))
        serie = [f for f in por_ronda[r] if _es_del(f, tid)]
        pendiente = any(f['fixture']['status']['short'] not in STATUS_FIN for f in serie)
        if pendiente or r == mas_avanzada:
            for f in serie:
                elegidos[f['fixture']['id']] = (r, f)
    if not elegidos:
        return None, []
    label = max({r for r, _ in elegidos.values()}, key=lambda r: KO_ORDER.index(r))
    return label, list(elegidos.values())

def main():
    out = {}
    for nombre, lg in COPAS:
        print('Fetching %s (league=%d)...' % (nombre, lg))
        fx = get(lg)
        ronda, partidos = ronda_actual(fx)
        if not ronda:
            print('  sin partidos argentinos en KO'); out[nombre] = {'ronda': None, 'partidos': []}; continue
        partidos = sorted(partidos, key=lambda rf: rf[1]['fixture']['date'])
        out[nombre] = {'ronda': RONDA_ES.get(ronda, ronda), 'partidos': [build(f, r) for r, f in partidos]}
        print('  ronda: %s (%d partidos argentinos)' % (RONDA_ES.get(ronda, ronda), len(partidos)))
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print('  Guardado:', OUT)

if __name__ == '__main__':
    main()
