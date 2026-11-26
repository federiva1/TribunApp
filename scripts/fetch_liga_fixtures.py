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
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
OUT  = ROOT / 'data' / 'fixtures' / 'liga.json'
LEAGUE, SEASON = 128, 2026

from apikey import get_api_key, api_headers
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
                                 headers=api_headers())
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())

# Playoffs: api-sports los nombra "Clausura - Round of 16", "- Quarter-finals",
# "- Semi-finals", "- Final". Siguen la numeración de las fechas (la fase regular
# tiene 16) para que el frontend los ordene y agrupe igual; `fase` lleva el nombre
# y es lo que excluye a esos partidos de la tabla (js/standings-fix.js).
FASES = (('round of 16', 17, 'Octavos de final'), ('quarter', 18, 'Cuartos de final'),
         ('semi', 19, 'Semifinal'), ('final', 20, 'Final'))


def fecha_y_fase(round_s):
    """'Clausura - 7' -> (7, None); 'Clausura - Round of 16' -> (17, 'Octavos de final')."""
    suf = round_s.split('-', 1)[1].strip() if '-' in round_s else round_s
    if suf.isdigit():
        return int(suf), None
    s = suf.lower()
    for clave, num, nombre in FASES:
        if clave in s:
            return num, nombre
    return None, suf or None


def build(f):
    fix, teams, goals = f['fixture'], f['teams'], f['goals']
    score = f.get('score', {}) or {}
    pen = score.get('penalty') or {}
    round_s = f['league']['round']                 # "Clausura - 7" | "Clausura - Round of 16"
    fecha, fase = fecha_y_fase(round_s)
    short = fix['status']['short']
    started, finished = STATUS_MAP.get(short, (False, False))
    hid, aid = teams['home']['id'], teams['away']['id']
    winner = None
    if teams['home'].get('winner'):   winner = SLUG.get(hid)
    elif teams['away'].get('winner'): winner = SLUG.get(aid)
    return {
        'round':    round_s,
        'fecha':    fecha,
        'fase':     fase,
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

def _resultados_procesados():
    """{api_id: {'local','visitante','gl','gv'}} de los partidos ya procesados.

    data/partidos/{id}.json lo genera fetch_liga_partidos.py desde el endpoint
    POR-ID de api-sports, que marca FT apenas termina el partido. El agregado por
    liga que usa este script tarda bastante más — se lo vio devolviendo "1H 0-0"
    más de 10 minutos después del final, en cuatro fechas seguidas — así que estos
    archivos sirven de respaldo para no quedarse con el estado viejo.
    """
    out = {}
    for f in (ROOT / 'data' / 'partidos').glob('*.json'):
        if f.stem in ('index', 'standings'):
            continue
        try:
            p = json.loads(f.read_text(encoding='utf-8')).get('partido') or {}
        except Exception:
            continue
        api_id = p.get('api_id')
        if api_id is None or p.get('goles_local') is None or p.get('goles_visitante') is None:
            continue
        out[str(api_id)] = {'local': p.get('local'), 'visitante': p.get('visitante'),
                            'gl': p['goles_local'], 'gv': p['goles_visitante']}
    return out


def reparar_estados(entries):
    """Marca FT los partidos que el agregado todavía da en curso pero que ya tienen
    archivo en data/partidos. Devuelve la lista de los reparados.

    Solo corrige hacia "terminado": nunca pisa un partido que la API ya da por
    finalizado ni inventa un resultado donde no hay archivo. Antes de aplicar
    verifica que los slugs de local y visitante coincidan, para que un api_id que
    no cuadre no escriba el resultado en el partido equivocado.
    """
    procesados = _resultados_procesados()
    reparados = []
    for e in entries:
        if e['status']['finished']:
            continue
        r = procesados.get(str(e.get('api_id')))
        if not r:
            continue
        if {r['local'], r['visitante']} != {e['home']['slug'], e['away']['slug']}:
            print(f"  ! api_id {e['api_id']}: slugs no coinciden "
                  f"({r['local']}-{r['visitante']} vs {e['home']['slug']}-{e['away']['slug']}), se saltea")
            continue
        gl, gv = (r['gl'], r['gv']) if r['local'] == e['home']['slug'] else (r['gv'], r['gl'])
        e['home_score'], e['away_score'] = gl, gv
        e['winner'] = None if gl == gv else (e['home']['slug'] if gl > gv else e['away']['slug'])
        e['status'].update({'started': True, 'finished': True, 'short': 'FT', 'elapsed': 90})
        reparados.append(f"{e['home']['slug']} {gl}-{gv} {e['away']['slug']}")
    return reparados


def agregar_manuales(entries):
    """Cruces de playoffs con horario OFICIAL que la API todavía no publicó.

    data/playoffs.json: un partido de una instancia con `local`, `visitante` y `hora`
    (ISO con zona) entra a liga.json como partido sin `api_id` (`manual: true`), así el
    club tiene próximo partido y la formación se abre. Solo si la API no trae ya ese
    cruce en esa instancia: cuando lo publica, gana la API y este se deja de agregar.
    Caso real: Boca–Gimnasia LP (cuartos), que la API publicó días después que los otros 3."""
    try:
        po = json.loads((ROOT / 'data' / 'playoffs.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        return []
    equipos = {}
    for e in entries:
        for lado in ('home', 'away'):
            equipos.setdefault(e[lado]['slug'], {k: e[lado][k] for k in ('name', 'id', 'slug')})
    presentes = {(e['fecha'], e['home']['slug']) for e in entries} | {(e['fecha'], e['away']['slug']) for e in entries}
    ronda_api = {17: 'Round of 16', 18: 'Quarter-finals', 19: 'Semi-finals', 20: 'Final'}
    out = []
    for ins in po.get('instancias') or []:
        for m in ins.get('partidos') or []:
            l, v, hora = m.get('local'), m.get('visitante'), m.get('hora')
            if not (l and v and hora) or l not in equipos or v not in equipos:
                continue
            if (ins['fecha'], l) in presentes or (ins['fecha'], v) in presentes:
                continue
            utc = datetime.fromisoformat(hora).astimezone(timezone.utc).isoformat()
            entries.append({
                'round': f"Clausura - {ronda_api.get(ins['fecha'], ins.get('fase') or '')}",
                'fecha': ins['fecha'], 'fase': ins.get('fase'), 'api_id': '', 'manual': True,
                'home': dict(equipos[l]), 'away': dict(equipos[v]),
                'home_score': None, 'away_score': None, 'home_pen': None, 'away_pen': None, 'winner': None,
                'status': {'utcTime': utc, 'started': False, 'finished': False, 'short': 'NS', 'elapsed': None},
            })
            out.append(f'{l} vs {v} ({hora})')
    return out


def main():
    print(f'Fetching Liga (league={LEAGUE} season={SEASON})...')
    resp = get(f'/fixtures?league={LEAGUE}&season={SEASON}').get('response', [])
    if not resp:
        print('Sin respuesta de la API'); sys.exit(1)
    # Solo Clausura (con sus playoffs, que la API publica como "Round of 16" a secas)
    from clubes_map import ronda_liga
    for f in resp:
        f['league']['round'] = ronda_liga(f['league']['round'])
    clausura = [f for f in resp if f['league']['round'].startswith('Clausura')]
    entries = [build(f) for f in clausura]
    # Horarios confirmados por la AFA que la API todavía no trae (data/horarios_overrides.json)
    import horarios_overrides as ho
    for e in entries:
        h = ho.hora_para(e['home']['slug'], e['away']['slug'], e['status']['utcTime'], e['status']['finished'])
        if h:
            e['status']['utcTime'] = h
            print(f"  Horario a mano: {e['home']['slug']} vs {e['away']['slug']} -> {h}")
    agregados = agregar_manuales(entries)
    for a in agregados:
        print(f'  Partido a mano (data/playoffs.json, la API todavía no lo publica): {a}')
    # El agregado de api-sports se atrasa al terminar un partido: se completa con
    # lo que ya haya en data/partidos (endpoint por-id, que marca FT al instante).
    reparados = reparar_estados(entries)
    if reparados:
        print(f'  Completados desde data/partidos ({len(reparados)}, el agregado los daba en curso):')
        for r in reparados:
            print(f'    · {r}')
    entries.sort(key=lambda e: (e['fecha'] or 0, e['status']['utcTime']))
    OUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'  Guardado: {OUT} ({len(entries)} partidos de Clausura)')
    print('  Estados:', dict(Counter(e['status']['short'] for e in entries)))
    print('  Fechas:', len(set(e['fecha'] for e in entries)))

if __name__ == '__main__':
    main()
