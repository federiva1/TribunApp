"""Genera/actualiza data/partidos/{id}.json usando la API de api-sports.

Paso 1 (este script): lineup + eventos + stats del partido desde api-sports.
Paso 2 (opcional):    stats individuales por jugador via FotMob scraper.

Uso:
    # Por fixture ID de api-sports (viene de mundial.json -> api_id):
    python scripts/fetch_mundial_match.py --fixture-id 1489369 --id mexico-southafrica

    # Auto: busca todos los partidos FT en mundial.json que aun no tienen data/partidos/{stats_id}.json:
    python scripts/fetch_mundial_match.py --auto

    # Auto + sobrescribir los que ya existen:
    python scripts/fetch_mundial_match.py --auto --force

Dependencias: solo stdlib + requests (o urllib que ya viene).
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
import urllib.request
import urllib.error
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
PARTIDOS_DIR = ROOT / 'data' / 'partidos'
INDEX_FILE   = PARTIDOS_DIR / 'index.json'
MUNDIAL_JSON = ROOT / 'data' / 'fixtures' / 'mundial.json'

from apikey import API_KEY
API_BASE = 'https://v3.football.api-sports.io'

# Mapeo nombre api-sports -> slug (para equipos del Mundial)
# Se completa a medida que jugamos partidos; los que falten se generan automaticamente.
NOMBRE_A_SLUG: dict[str, str] = {
    'Mexico':               'mexico',
    'South Africa':         'southafrica',
    'South Korea':          'southkorea',
    'Czech Republic':       'czechia',
    'Czechia':              'czechia',
    'Bosnia':               'bosniaandherzegovina',
    'Bosnia and Herzegovina': 'bosniaandherzegovina',
    'Bosnia & Herzegovina': 'bosniaandherzegovina',
    'Canada':               'canada',
    'Qatar':                'qatar',
    'Switzerland':          'switzerland',
    'Brazil':               'brazil',
    'Haiti':                'haiti',
    'Morocco':              'morocco',
    'Scotland':             'scotland',
    'USA':                  'usa',
    'United States':        'usa',
    'Paraguay':             'paraguay',
    'Australia':            'australia',
    'Turkey':               'turkiye',
    'Turkiye':              'turkiye',
    'Germany':              'germany',
    'Curacao':              'curacao',
    'Ivory Coast':          'ivorycoast',
    "Cote d'Ivoire":        'ivorycoast',
    'Ecuador':              'ecuador',
    'Netherlands':          'netherlands',
    'Japan':                'japan',
    'Sweden':               'sweden',
    'Tunisia':              'tunisia',
    'Belgium':              'belgium',
    'Egypt':                'egypt',
    'Iran':                 'iran',
    'New Zealand':          'newzealand',
    'Spain':                'spain',
    'Cape Verde':           'capeverde',
    'Cape Verde Islands':   'capeverde',
    'Saudi Arabia':         'saudiarabia',
    'Uruguay':              'uruguay',
    'France':               'france',
    'Iraq':                 'iraq',
    'Norway':               'norway',
    'Senegal':              'senegal',
    'Algeria':              'algeria',
    'Argentina':            'argentina',
    'Austria':              'austria',
    'Jordan':               'jordan',
    'Colombia':             'colombia',
    'DR Congo':             'drcongo',
    'Congo DR':             'drcongo',
    'Portugal':             'portugal',
    'Uzbekistan':           'uzbekistan',
    'Croatia':              'croatia',
    'England':              'england',
    'Ghana':                'ghana',
    'Panama':               'panama',
}


def _strip_accents(s: str) -> str:
    """Saca diacriticos via NFD (Curaçao -> Curacao, Türkiye -> Turkiye)."""
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

# Version normalizada (sin tildes, minusculas) del mapeo, para que el lookup no
# dependa de la normalizacion unicode exacta con la que api-sports manda el nombre.
_NORM_SLUG = {_strip_accents(k).lower(): v for k, v in NOMBRE_A_SLUG.items()}

def name_to_slug(name: str) -> str:
    if name in NOMBRE_A_SLUG:
        return NOMBRE_A_SLUG[name]
    key = _strip_accents(name).lower()
    if key in _NORM_SLUG:
        return _NORM_SLUG[key]
    # Fallback: minusculas sin tildes ni nada que no sea alfanumérico ascii. Sacar
    # las tildes es clave (si no "Curaçao" != "curacao" e invierte local/visitante);
    # y sacar apóstrofes/puntos evita filenames/URLs raros (ej. "O'Higgins").
    return ''.join(c for c in key if c.isascii() and c.isalnum())


# Mapeo api-sports ID -> slug de los clubes argentinos (fuente: js/clubes.js).
# Permite reutilizar este script para partidos de la Liga (no solo Mundial):
# el ID es un identificador estable, a diferencia del nombre.
def _clubes_id_slug() -> dict:
    import re
    src = (ROOT / 'js' / 'clubes.js').read_text(encoding='utf-8')
    return {int(m.group(2)): m.group(1)
            for m in re.finditer(r'^\s{2}([a-z0-9]+):\s*\{[^}]*?\bid:\s*(\d+)',
                                 src, re.MULTILINE | re.DOTALL)}

try:
    ID_SLUG = _clubes_id_slug()
except Exception:
    ID_SLUG = {}

def team_slug(api_id, api_name: str) -> str:
    """Resuelve slug por ID api-sports (clubes argentinos) o por nombre (Mundial)."""
    if api_id in ID_SLUG:
        return ID_SLUG[api_id]
    return name_to_slug(api_name)


def api_get(path: str) -> dict:
    url = f'{API_BASE}/{path}'
    req = urllib.request.Request(url, headers={'x-apisports-key': API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f'  API error {e.code}: {url}')
        raise


def to_int(v):
    if v in (None, ''):
        return None
    try:
        return int(float(str(v).replace('%', '')))
    except Exception:
        return None


# ── Extraccion desde api-sports ───────────────────────────────────────────────

def fetch_match_data(fixture_id: int) -> dict:
    """Llama a los 3 endpoints y retorna datos combinados."""
    print(f'  Fetching fixture {fixture_id}...')
    fix_data = api_get(f'fixtures?id={fixture_id}')
    if not fix_data.get('response'):
        raise ValueError(f'No data for fixture {fixture_id}')
    fix = fix_data['response'][0]

    print(f'  Fetching lineups...')
    lu_data = api_get(f'fixtures/lineups?fixture={fixture_id}')

    print(f'  Fetching events...')
    ev_data = api_get(f'fixtures/events?fixture={fixture_id}')

    print(f'  Fetching stats...')
    st_data = api_get(f'fixtures/statistics?fixture={fixture_id}')

    return {
        'fixture':  fix,
        'lineups':  lu_data.get('response', []),
        'events':   ev_data.get('response', []),
        'stats':    st_data.get('response', []),
    }


def ronda_label(round_str: str):
    """Etiqueta legible de la ronda (para copas). Liga devuelve None (usa fecha_num)."""
    import re as _re
    r = (round_str or '').strip()
    rl = r.lower()
    if 'clausura' in rl or 'apertura' in rl or 'regular season' in rl:
        return None
    m = _re.search(r'(\d+)\s*$', r)
    table = [
        ('group', 'Fase de grupos'),
        ('knockout round play', 'Playoffs'), ('play-off', 'Playoffs'), ('playoff', 'Playoffs'),
        ('round of 32', 'Dieciseisavos'), ('1/16', 'Dieciseisavos'),
        ('round of 16', 'Octavos'), ('1/8', 'Octavos'),
        ('quarter', 'Cuartos'), ('1/4', 'Cuartos'),
        ('semi', 'Semifinal'),
        ('third place', '3er puesto'), ('3rd place', '3er puesto'),
        ('final', 'Final'),
    ]
    for k, v in table:
        if k in rl:
            if v == 'Fase de grupos' and m:
                return f'Fase de grupos · F{m.group(1)}'
            return v
    return r or None


def build_partidos_json(raw: dict, local_slug: str, visitante_slug: str,
                        output_id: str, competicion: str) -> dict:
    fix      = raw['fixture']
    teams    = fix['teams']
    fixture  = fix['fixture']
    goals    = fix['goals']
    score    = fix.get('score', {})

    home_name = teams['home']['name']
    away_name = teams['away']['name']
    home_id   = teams['home']['id']
    away_id   = teams['away']['id']

    # Respetar el orden local/visitante del usuario
    # La API siempre tiene home/away; el usuario define cual es "local" en el JSON
    home_is_local = (team_slug(home_id, home_name) == local_slug)

    local_goals    = goals['home'] if home_is_local else goals['away']
    visitante_goals = goals['away'] if home_is_local else goals['home']
    local_api_id   = home_id if home_is_local else away_id
    visit_api_id   = away_id if home_is_local else home_id
    # Nombre display de api-sports (para rivales extranjeros de copa que no están en NAMES_ES)
    local_nombre     = home_name if home_is_local else away_name
    visitante_nombre = away_name if home_is_local else home_name

    fecha   = fixture.get('date', '')[:10]
    import re as _re
    _round = fix.get('league', {}).get('round', '') or ''
    _rm = _re.search(r'(\d+)\s*$', _round)
    fecha_num = int(_rm.group(1)) if _rm else None   # nº de fecha (ej. "Clausura - 3" -> 3)
    ronda = ronda_label(_round)                       # label de ronda (copas); None en liga
    estadio = fixture.get('venue', {}).get('name') or ''
    ciudad  = fixture.get('venue', {}).get('city') or ''
    if ciudad:
        estadio = f'{estadio}, {ciudad}'

    # ── Eventos: sustituciones + goles + tarjetas ─────────────────────────
    # {player_api_id: {goles, asist, amarilla, roja, minuto_sale}}
    ev_info: dict[int, dict] = {}

    def get_ev(pid):
        if pid not in ev_info:
            ev_info[pid] = {'goles': 0, 'asist': 0, 'amarilla': False, 'roja': False, 'min_sale': None}
        return ev_info[pid]

    subs_in: dict[int, dict] = {}   # {team_api_id: [{player_id, name, min}]}

    goles_local, goles_visitante = [], []

    for ev in raw['events']:
        etype   = ev.get('type', '')
        detail  = ev.get('detail', '')
        minute  = to_int(ev.get('time', {}).get('elapsed'))
        team_id = ev.get('team', {}).get('id')
        player  = ev.get('player', {}) or {}
        assist  = ev.get('assist', {}) or {}
        pid     = player.get('id')
        aid     = assist.get('id')

        if etype == 'Goal':
            if detail == 'Missed Penalty':
                continue  # penal errado: NO es gol
            if not pid:
                continue  # evento gol sin jugador atribuido (glitch api-sports): descartar
            entry = {'min': minute, 'jugador': player.get('name', ''), 'asist': assist.get('name')}
            if detail == 'Own Goal':
                # Gol en contra: api-sports pone en team_id al equipo BENEFICIADO
                # (no al del jugador que lo metió). Suma al marcador de ese equipo,
                # pero NO se le acredita gol al jugador.
                entry['asist'] = None
                entry['en_contra'] = True
            else:
                # Gol normal o penal convertido (detail 'Penalty')
                if pid:
                    get_ev(pid)['goles'] += 1
                if aid:
                    get_ev(aid)['asist'] += 1
            if team_id == (local_api_id if home_is_local else visit_api_id):
                goles_local.append(entry)
            else:
                goles_visitante.append(entry)

        elif etype == 'Card':
            if pid:
                e = get_ev(pid)
                if 'Red' in detail:
                    e['roja'] = True
                else:
                    e['amarilla'] = True

        elif etype == 'subst':
            # player = sale, assist = entra
            out_id   = pid
            in_pid   = aid
            in_name  = assist.get('name', '')
            if out_id:
                get_ev(out_id)['min_sale'] = minute
            if in_pid and team_id is not None:
                if team_id not in subs_in:
                    subs_in[team_id] = []
                subs_in[team_id].append({'id': in_pid, 'name': in_name, 'min_in': minute})

    # ── Lineup ────────────────────────────────────────────────────────────
    lineup_by_team: dict[int, dict] = {}
    for team_lu in raw['lineups']:
        tid = team_lu['team']['id']
        lineup_by_team[tid] = team_lu

    def build_players(team_api_id: int, is_local: bool) -> list[dict]:
        lu   = lineup_by_team.get(team_api_id, {})
        slug = local_slug if is_local else visitante_slug
        result = []

        goles_recibidos = (visitante_goals if is_local else local_goals) or 0

        # Nombre completo por ID desde el lineup (startXI + substitutes). Los
        # eventos de cambio dan el nombre abreviado ("P. Gueye"); el lineup tiene
        # el completo ("Pape Gueye"), necesario para matchear con FotMob.
        full_name_by_id: dict = {}
        for p in lu.get('startXI', []) + lu.get('substitutes', []):
            pl = p.get('player', {})
            if pl.get('id'):
                full_name_by_id[pl['id']] = pl.get('name', '')

        # Titulares
        for p in lu.get('startXI', []):
            pl   = p.get('player', {})
            pid  = pl.get('id')
            name = pl.get('name', '')
            num  = str(pl.get('number') or '')
            pos  = pl.get('pos', '') or ''
            is_gk = pos == 'G'
            ev   = ev_info.get(pid, {})
            min_sale = ev.get('min_sale')
            min_ = min_sale if min_sale else 90

            entry = {
                'nombre':  name,
                'id':      pid,
                'tipo':    'titular',
                'portero': is_gk,
                'mvp':     False,
                'num':     num,
                'min':     min_,
                'goles':   ev.get('goles', 0),
                'asist':   ev.get('asist', 0),
                'amarilla': ev.get('amarilla', False),
                'roja':    ev.get('roja', False),
                'top':     None, 'ataque': None, 'defensa': None,
                'duelos':  None,
                'portero_stats': {'paradas': None, 'goles_contra': goles_recibidos, 'goles_evitados': None} if is_gk else None,
            }
            result.append(entry)

        # Suplentes que ingresaron
        for s in subs_in.get(team_api_id, []):
            entry = {
                'nombre':  full_name_by_id.get(s['id']) or s['name'],
                'id':      s['id'],
                'tipo':    'suplente',
                'portero': False,
                'mvp':     False,
                'num':     '',
                'min':     90 - s['min_in'] if s['min_in'] else None,
                'goles':   ev_info.get(s['id'], {}).get('goles', 0),
                'asist':   ev_info.get(s['id'], {}).get('asist', 0),
                'amarilla': ev_info.get(s['id'], {}).get('amarilla', False),
                'roja':    ev_info.get(s['id'], {}).get('roja', False),
                'top':     None, 'ataque': None, 'defensa': None,
                'duelos':  None, 'portero_stats': None,
            }
            result.append(entry)

        # DT
        coach = lu.get('coach', {})
        if coach:
            result.append({
                'nombre': coach.get('name', ''), 'id': coach.get('id'),
                'tipo': 'dt', 'portero': False, 'mvp': False, 'num': '',
                'min': None, 'goles': 0, 'asist': 0,
                'amarilla': False, 'roja': False,
                'top': None, 'ataque': None, 'defensa': None,
                'duelos': None, 'portero_stats': None,
            })

        # Dedup: api-sports a veces lista al mismo jugador como titular Y suplente
        # (cuando hay cambios tardíos). Conservar solo la entrada titular.
        seen: set[int] = set()
        deduped = []
        for entry in result:
            eid = entry.get('id')
            if eid and eid in seen:
                continue  # duplicado, saltar
            if eid:
                seen.add(eid)
            deduped.append(entry)
        return deduped

    local_jugs    = build_players(local_api_id if home_is_local else visit_api_id, True)
    visitante_jugs = build_players(visit_api_id if home_is_local else local_api_id, False)

    # ── Top stats del partido ──────────────────────────────────────────────
    STAT_MAP = {
        'Ball Possession':   ('Posesion',             'posesion'),
        'expected_goals':    ('xG',                   'numero'),
        'Total Shots':       ('Tiros totales',         'numero'),
        'Shots on Goal':     ('Tiros al arco',         'numero'),
        'Shots insidebox':   ('Toques en area rival',  'numero'),
        'Corner Kicks':      ('Corners',               'numero'),
        'Fouls':             ('Faltas',                'numero'),
        'Yellow Cards':      ('Tarjetas amarillas',    'numero'),
        'Red Cards':         ('Tarjetas rojas',        'numero'),
    }
    # Pases precisos se construye a mano
    pases_map: dict[str, dict] = {}   # team_api_id -> {accurate, total, pct}

    stats_by_team: dict[int, list] = {}
    for ts in raw['stats']:
        tid = ts['team']['id']
        stats_by_team[tid] = ts['statistics']

    def stat_val(tid, key):
        for s in stats_by_team.get(tid, []):
            if s['type'] == key:
                return s['value']
        return None

    local_tid_api   = local_api_id if home_is_local else visit_api_id
    visit_tid_api   = visit_api_id if home_is_local else local_api_id

    top_stats = []
    seen = set()
    for api_key, (label, tipo) in STAT_MAP.items():
        if label in seen:
            continue
        seen.add(label)
        hv = stat_val(local_tid_api, api_key)
        av = stat_val(visit_tid_api, api_key)
        if hv is None and av is None:
            continue
        if tipo == 'posesion':
            h = to_int(hv) or 0
            a = to_int(av) or 0
            top_stats.append({'label': label, 'local': h, 'visitante': a,
                              'tipo': tipo, 'local_val': h, 'visitante_val': a})
        elif api_key == 'expected_goals':
            # xG con decimales
            def safe_xg(v):
                if v in (None, ''): return None
                try: return round(float(str(v)), 2)
                except: return None
            h = safe_xg(hv); a = safe_xg(av)
            top_stats.append({'label': label, 'local': h, 'visitante': a,
                              'tipo': tipo, 'local_val': h, 'visitante_val': a})
        else:
            h = to_int(hv) if hv is not None else 0
            a = to_int(av) if av is not None else 0
            top_stats.append({'label': label, 'local': h, 'visitante': a,
                              'tipo': tipo, 'local_val': h, 'visitante_val': a})

    # Pases precisos como texto "N (X%)"
    hp_acc = to_int(stat_val(local_tid_api, 'Passes accurate'))
    hp_tot = to_int(stat_val(local_tid_api, 'Total passes'))
    ap_acc = to_int(stat_val(visit_tid_api, 'Passes accurate'))
    ap_tot = to_int(stat_val(visit_tid_api, 'Total passes'))
    if hp_acc is not None:
        hp_pct = round(hp_acc / hp_tot * 100) if hp_tot else 0
        ap_pct = round(ap_acc / ap_tot * 100) if ap_tot and ap_acc is not None else 0
        top_stats.append({
            'label': 'Pases precisos',
            'local':     f'{hp_acc} ({hp_pct}%)',
            'visitante': f'{ap_acc} ({ap_pct}%)' if ap_acc is not None else '0 (0%)',
            'tipo': 'texto',
            'local_val': hp_pct, 'visitante_val': ap_pct,
        })

    return {
        'partido': {
            'local':           local_slug,
            'visitante':       visitante_slug,
            'local_nombre':    local_nombre,
            'visitante_nombre': visitante_nombre,
            'goles_local':     local_goals,
            'goles_visitante': visitante_goals,
            'fecha':           fecha,
            'fecha_num':       fecha_num,
            'ronda':           ronda,
            'estadio':         estadio,
            'competicion':     competicion,
            'api_id':          str(fixture.get('id') or ''),
            'goles_detalle':   {'local': goles_local, 'visitante': goles_visitante},
        },
        'top_stats': top_stats,
        'jugadores': {
            local_slug:     local_jugs,
            visitante_slug: visitante_jugs,
        },
    }


def save(payload: dict, output_id: str):
    PARTIDOS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = PARTIDOS_DIR / f'{output_id}.json'

    # Preservar stats individuales (top/ataque/defensa/duelos) si ya existen
    # (puestos por el FotMob scraper en un paso previo/siguiente)
    if out_file.exists():
        try:
            existing = json.loads(out_file.read_text(encoding='utf-8'))
            for slug, players in existing.get('jugadores', {}).items():
                if slug not in payload['jugadores']:
                    continue
                # Indexar por nombre
                existing_by_name = {p['nombre']: p for p in players}
                for p in payload['jugadores'][slug]:
                    ex = existing_by_name.get(p['nombre'])
                    if ex:
                        for field in ('top', 'ataque', 'defensa', 'duelos', 'portero_stats'):
                            if ex.get(field) and p[field] is None:
                                p[field] = ex[field]
        except Exception:
            pass

    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  Escrito: data/partidos/{output_id}.json')

    # Actualizar index.json
    index = []
    if INDEX_FILE.exists():
        try:
            index = json.loads(INDEX_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass

    p = payload['partido']
    entry = {
        'id':              output_id,
        'local':           p['local'],
        'visitante':       p['visitante'],
        'local_nombre':    p.get('local_nombre'),
        'visitante_nombre': p.get('visitante_nombre'),
        'fecha':           p['fecha'],
        'fecha_num':       p.get('fecha_num'),
        'ronda':           p.get('ronda'),
        'goles_local':     p['goles_local'],
        'goles_visitante': p['goles_visitante'],
        'competicion':     p['competicion'],
        'estadio':         p['estadio'],
    }
    index = [e for e in index if e.get('id') != output_id]
    index.append(entry)
    index.sort(key=lambda e: e.get('fecha', ''))
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  index.json actualizado ({len(index)} partidos)')


def process_fixture(fixture_id: int, output_id: str, local_slug: str,
                    visitante_slug: str, competicion: str):
    print(f'\n[{output_id}] fixture_id={fixture_id}  {local_slug} vs {visitante_slug}')
    raw     = fetch_match_data(fixture_id)
    payload = build_partidos_json(raw, local_slug, visitante_slug, output_id, competicion)
    save(payload, output_id)


def auto_mode(force: bool):
    """Procesa todos los partidos FT en mundial.json que tienen api_id.
    Si stats_id es null, lo deriva de {local_slug}-{visitante_slug} y lo guarda en mundial.json."""
    mundial = json.loads(MUNDIAL_JSON.read_text(encoding='utf-8'))
    pending = []
    mundial_changed = False
    for m in mundial:
        if not m.get('status', {}).get('finished'):
            continue
        api_id = m.get('api_id')
        if not api_id:
            continue
        local_slug     = m.get('home', {}).get('slug') or name_to_slug(m.get('home', {}).get('name', ''))
        visitante_slug = m.get('away', {}).get('slug') or name_to_slug(m.get('away', {}).get('name', ''))
        stats_id = m.get('stats_id') or f'{local_slug}-{visitante_slug}'
        # Grabar stats_id derivado si faltaba
        if not m.get('stats_id'):
            m['stats_id'] = stats_id
            mundial_changed = True
        out_file = PARTIDOS_DIR / f'{stats_id}.json'
        if out_file.exists() and not force:
            print(f'  Saltando {stats_id} (ya existe, usa --force para sobreescribir)')
            continue
        pending.append((int(api_id), stats_id, local_slug, visitante_slug))

    if mundial_changed:
        MUNDIAL_JSON.write_text(json.dumps(mundial, ensure_ascii=False, indent=2), encoding='utf-8')
        print('  mundial.json actualizado con stats_id derivados.')

    if not pending:
        print('Nada que procesar.')
        return

    for fixture_id, stats_id, local_slug, visitante_slug in pending:
        try:
            process_fixture(fixture_id, stats_id, local_slug, visitante_slug,
                            'FIFA World Cup 2026')
        except Exception as e:
            print(f'  ERROR en {stats_id}: {e}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixture-id', type=int, help='api-sports fixture ID')
    ap.add_argument('--id',         help='ID de salida (e.g. mexico-southafrica)')
    ap.add_argument('--local',      help='Slug equipo local')
    ap.add_argument('--visitante',  help='Slug equipo visitante')
    ap.add_argument('--competicion', default='FIFA World Cup 2026')
    ap.add_argument('--auto',   action='store_true',
                    help='Procesar todos los FT en mundial.json con stats_id pendiente')
    ap.add_argument('--force',  action='store_true',
                    help='Con --auto: sobreescribir archivos existentes')
    args = ap.parse_args()

    if args.auto:
        auto_mode(args.force)
        return 0

    if not args.fixture_id or not args.id or not args.local or not args.visitante:
        ap.error('Requerido: --fixture-id, --id, --local, --visitante  (o usa --auto)')

    process_fixture(args.fixture_id, args.id, args.local, args.visitante, args.competicion)
    return 0


if __name__ == '__main__':
    sys.exit(main())
