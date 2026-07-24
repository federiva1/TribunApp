"""
fetch_copas_fixtures.py
Genera data/fixtures/copas.json con los partidos de la instancia ACTUAL de
Copa Libertadores (league=13) y Copa Sudamericana (league=11) 2026 en los que
juega un equipo argentino.

- Solo fase de eliminación (knockout). Detecta automáticamente la ronda en curso
  (la más avanzada con algún partido argentino sin terminar; si están todas
  terminadas, la última con partidos argentinos).
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

try:
    from apikey import get_api_key
    API_KEY = get_api_key()
except (Exception, SystemExit):
    API_KEY = 'b8bbfc856fd5cf12cd7d697b2b01887d'

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
        headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read()).get('response', [])

def side(t):
    """Info de un equipo: slug (si es argentino) + logo (api-sports para extranjeros)."""
    if t['id'] in ARG:
        return {'name': t['name'], 'slug': SLUG[t['id']], 'logo': None, 'arg': True}
    return {'name': t['name'], 'slug': None, 'logo': t.get('logo'), 'arg': False}

def build(f):
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
    }

def ronda_actual(fixtures):
    """Rondas KO con partido argentino; devuelve la ronda en curso (o la última)."""
    con_arg = {}
    for f in fixtures:
        r = f['league']['round']
        if r not in KO_ORDER:
            continue
        if f['teams']['home']['id'] in ARG or f['teams']['away']['id'] in ARG:
            con_arg.setdefault(r, []).append(f)
    if not con_arg:
        return None, []
    # rondas ordenadas de más avanzada a menos
    rondas = sorted(con_arg, key=lambda r: KO_ORDER.index(r), reverse=True)
    # la más avanzada con algún partido no terminado; si todas terminadas, la más avanzada
    for r in rondas:
        if any(f['fixture']['status']['short'] not in STATUS_FIN for f in con_arg[r]):
            return r, con_arg[r]
    return rondas[0], con_arg[rondas[0]]

def main():
    out = {}
    for nombre, lg in COPAS:
        print('Fetching %s (league=%d)...' % (nombre, lg))
        fx = get(lg)
        ronda, partidos = ronda_actual(fx)
        if not ronda:
            print('  sin partidos argentinos en KO'); out[nombre] = {'ronda': None, 'partidos': []}; continue
        partidos = sorted(partidos, key=lambda f: f['fixture']['date'])
        out[nombre] = {'ronda': RONDA_ES.get(ronda, ronda), 'partidos': [build(f) for f in partidos]}
        print('  ronda: %s (%d partidos argentinos)' % (RONDA_ES.get(ronda, ronda), len(partidos)))
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print('  Guardado:', OUT)

if __name__ == '__main__':
    main()
