"""Scraper FotMob — extrae playerStats de los DOS equipos del partido y los
inyecta en data/estadisticas/{slug}[_copa].json (jugadores + jugadoresRival).
Recomputa el xG del equipo y rival sumando el xG individual.

Genérico: funciona para cualquier club + competencia. Resuelve FotMob ID
desde scripts/clubes_map.py y la URL del partido vía la API pública de FotMob.

Uso:
    # AAAJ liga, los 4 partidos hardcodeados (Banfield/IndRiv/AtlTuc/Huracan):
    python scripts/scrape_fotmob_partidos.py

    # Otros clubes — autodescubre el match más reciente jugado (o por --date):
    python scripts/scrape_fotmob_partidos.py --slug clubatleticoplatense --copa libertadores
    python scripts/scrape_fotmob_partidos.py --slug racingclub --copa sudamericana --date 2026-04-29

    # Browser visible y/o solo una fecha:
    python scripts/scrape_fotmob_partidos.py --headed --date 2026-04-06

Dependencias: playwright (ya instalado).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

# Playwright es opcional: el camino principal baja el __NEXT_DATA__ por HTTP
# (urllib), que funciona donde el browser está bloqueado (proxy del entorno /
# IP de GitHub Actions). Playwright queda solo como fallback para la compu local.
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from clubes_map import lookup, estadisticas_path  # noqa: E402

RAW_DIR = ROOT / 'scripts' / '_fotmob_raw'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

# AAAJ liga: 4 partidos hardcodeados (con votos migrados de Formaaajcion).
PARTIDOS_AAAJ = [
    {'date': '2026-04-06', 'rival': 'Banfield',
     'url': 'https://www.fotmob.com/matches/argentinos-juniors-vs-banfield/3d5luq#5102060'},
    {'date': '2026-04-11', 'rival': 'Independiente Rivadavia',
     'url': 'https://www.fotmob.com/matches/argentinos-juniors-vs-independiente-rivadavia/6s3zk25#5102082'},
    {'date': '2026-04-19', 'rival': 'Atletico Tucuman',
     'url': 'https://www.fotmob.com/matches/argentinos-juniors-vs-atletico-tucuman/6s3s6wu#5102090'},
    {'date': '2026-04-28', 'rival': 'Huracan',
     'url': 'https://www.fotmob.com/matches/huracan-vs-argentinos-juniors/3d30gy#5102110'},
]


def to_int(v):
    if v in (None, ''):
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def to_num(v):
    if v in (None, ''):
        return None
    try:
        f = float(v)
        return int(f) if f == int(f) else round(f, 2)
    except (ValueError, TypeError):
        return None


def _player_entry(p: dict) -> dict:
    """Aplana stats de un jugador FotMob al schema TribunApp."""
    flat = {}
    for section in p.get('stats', []):
        for stat_name, stat_obj in (section.get('stats') or {}).items():
            if stat_name == 'Shotmap':
                continue
            stat = (stat_obj or {}).get('stat', {})
            if stat_name not in flat:
                flat[stat_name] = (stat.get('value'), stat.get('total'))

    minutos = to_int(flat.get('Minutes played', (None, None))[0]) or 0
    jugo = minutos > 0

    def f(key):
        return flat.get(key, (None, None))[0]

    def ft(key):
        return flat.get(key, (None, None))[1]

    pases_v, pases_t = flat.get('Accurate passes', (None, None))

    return {
        'nombre':           (p.get('name') or '').strip(),
        'jugo':             jugo,
        'minutos':          minutos if jugo else 0,
        'goles':            to_int(f('Goals')),
        'asistencias':      to_int(f('Assists')),
        'xG':               to_num(f('Expected goals (xG)')),
        'xA':               to_num(f('Expected assists (xA)')),
        'xGxA':             to_num(f('xG + xA')),
        'accDefensivas':    to_int(f('Defensive actions')),
        'disparos':         to_int(f('Shots on target')),
        'toques':           to_int(f('Touches')),
        'pasesAcertados':   to_int(pases_v),
        'pasesIntentados':  to_int(pases_t),
        # --- Set FotMob ampliado (columnas opcionales; la UI muestra las presentes) ---
        'tiros':            to_int(f('Total shots')),
        'grandesOcasiones': to_int(f('Big chances created')),
        'toquesArea':       to_int(f('Touches in opposition box')),
        'regates':          to_int(f('Successful dribbles')),
        'regatesTotal':     to_int(ft('Successful dribbles')),
        'pasesUltimoTercio': to_int(f('Passes into final third')),
        'entradas':         to_int(f('Tackles')),
        'intercepciones':   to_int(f('Interceptions')),
        'recuperaciones':   to_int(f('Recoveries')),
        'despejes':         to_int(f('Clearances')),
        'duelosGanados':    to_int(f('Duels won')),
        'duelosPerdidos':   to_int(f('Duels lost')),
        'faltas':           to_int(f('Fouls committed')),
        'faltasRecibidas':  to_int(f('Was fouled')),
    }


def extract_players(nd: dict, team_id: int) -> tuple[list[dict], list[dict], int]:
    """De __NEXT_DATA__: jugadores del club, jugadores rival, rival_team_id."""
    ps = nd['props']['pageProps']['content']['playerStats']
    own, rival = [], []
    rival_id = None
    for pid, p in ps.items():
        tid = p.get('teamId')
        entry = _player_entry(p)
        if str(tid) == str(team_id):
            own.append(entry)
        else:
            rival.append(entry)
            if rival_id is None and tid is not None:
                rival_id = int(tid)

    sort_key = lambda x: (-1 if x['jugo'] else 0, -(x['minutos'] or 0), x['nombre'])
    own.sort(key=sort_key)
    rival.sort(key=sort_key)
    return own, rival, rival_id


def sum_xg(jugadores: list[dict]) -> float | None:
    vals = [j.get('xG') for j in jugadores if j.get('jugo') and j.get('xG') is not None]
    return round(sum(vals), 2) if vals else None


def _next_data_http(url: str) -> dict | None:
    """Baja el HTML y extrae el JSON de <script id="__NEXT_DATA__">. FotMob hace
    SSR, así que playerStats viene embebido — no hace falta browser. Funciona
    donde Playwright está bloqueado (proxy del entorno / IP de GitHub Actions).
    Devuelve None si falla (para caer al fallback de Playwright)."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode('utf-8', 'replace')
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                      html, re.DOTALL)
        return json.loads(m.group(1)) if m else None
    except Exception:
        return None


def _next_data_browser(url: str, page) -> dict | None:
    """Fallback con Playwright (compu local donde el browser sí llega)."""
    page.goto(url, wait_until='domcontentloaded', timeout=60000)
    time.sleep(6)
    return page.evaluate('() => window.__NEXT_DATA__')


def discover_match_urls(fotmob_id: int, copa: str, date_filter: str | None) -> list[dict]:
    """Llama a la API pública de FotMob, filtra por torneo y devuelve los matches."""
    hdr = {'User-Agent': UA, 'Accept': 'application/json', 'Referer': 'https://www.fotmob.com/'}
    url = f'https://www.fotmob.com/api/data/teams?id={fotmob_id}&ccode3=ARG'
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    all_fx = data.get('fixtures', {}).get('allFixtures', {}).get('fixtures', [])
    out = []
    for m in all_fx:
        d = (m.get('status', {}) or {}).get('utcTime', '')[:10]
        if not d:
            continue
        if date_filter and d != date_filter:
            continue
        # Filtrar solo partidos finalizados
        finished = (m.get('status', {}) or {}).get('finished')
        if not finished and not date_filter:
            continue
        # Filtrar por torneo si copa fue especificado
        tour = (m.get('tournament', {}) or {}).get('name', '').lower()
        if copa == 'libertadores' and 'libertadores' not in tour:
            continue
        if copa == 'sudamericana' and 'sudamericana' not in tour:
            continue
        if copa == '' and ('libertadores' in tour or 'sudamericana' in tour):
            continue
        page = m.get('pageUrl', '')
        if not page:
            continue
        full_url = f'https://www.fotmob.com{page}' if page.startswith('/') else page
        home = m.get('home', {}).get('name', '')
        away = m.get('away', {}).get('name', '')
        out.append({'date': d, 'url': full_url, 'home': home, 'away': away, 'tour': tour})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', default='argentinosjuniors')
    ap.add_argument('--copa', default='', choices=['', 'libertadores', 'sudamericana'])
    ap.add_argument('--headed', action='store_true', help='Browser visible')
    ap.add_argument('--only', default=None,
                    help='Procesar solo el partido de esta fecha (YYYY-MM-DD). '
                         'Para AAAJ liga aplica al PARTIDOS hardcodeado; para otros, '
                         'usa este filtro al descubrir vía FotMob API.')
    ap.add_argument('--date', default=None,
                    help='Alias de --only')
    args = ap.parse_args()

    date_filter = args.only or args.date
    cfg = lookup(args.slug)
    fotmob_id = cfg['fotmob']
    if not fotmob_id:
        print(f'ERROR: no tengo FotMob ID para {args.slug}. Agrégalo a clubes_map.py', file=sys.stderr)
        return 1

    json_file = ROOT / estadisticas_path(args.slug, args.copa)
    RAW_DIR.mkdir(exist_ok=True)

    # Lista de partidos a scrapear
    if args.slug == 'argentinosjuniors' and args.copa == '':
        targets = [p for p in PARTIDOS_AAAJ if not date_filter or p['date'] == date_filter]
    else:
        print(f'Descubriendo URLs vía FotMob API (fotmob_id={fotmob_id}, copa={args.copa or "liga"})...')
        targets = discover_match_urls(fotmob_id, args.copa, date_filter)
        if not targets:
            print('No se encontraron partidos finalizados que coincidan con los filtros.')
            return 1

    # Cargar/inicializar JSON destino
    if json_file.exists():
        payload = json.loads(json_file.read_text(encoding='utf-8'))
    else:
        json_file.parent.mkdir(parents=True, exist_ok=True)
        temporada = 'Apertura 2026' if args.copa == '' else f'Copa {args.copa.title()} 2026'
        payload = {'club': args.slug, 'temporada': temporada, 'partidos': [], 'acumulado': []}

    partidos = payload.get('partidos', [])
    by_date = {p.get('date'): p for p in partidos}

    # Browser lazy: solo se abre si el camino HTTP falla para algún partido.
    _pw = {'pw': None, 'browser': None, 'page': None}

    def get_page():
        if _pw['page'] is not None:
            return _pw['page']
        if sync_playwright is None:
            return None
        _pw['pw'] = sync_playwright().start()
        _pw['browser'] = _pw['pw'].chromium.launch(headless=not args.headed, slow_mo=100)
        ctx = _pw['browser'].new_context(user_agent=UA, locale='es-AR',
                                         viewport={'width': 1280, 'height': 900})
        _pw['page'] = ctx.new_page()
        return _pw['page']

    def close_page():
        try:
            if _pw['browser'] is not None:
                _pw['browser'].close()
            if _pw['pw'] is not None:
                _pw['pw'].stop()
        except Exception:
            pass

    try:
        for i, par in enumerate(targets, 1):
            date = par['date']
            url = par['url']
            print(f'\n[{i}/{len(targets)}] {date}')
            print(f'  {url}')
            try:
                nd = _next_data_http(url)          # camino principal (HTTP)
                if not nd:
                    print('  HTTP sin __NEXT_DATA__ — probando Playwright...')
                    page = get_page()
                    nd = _next_data_browser(url, page) if page is not None else None
                if not nd:
                    print('  ERROR: sin __NEXT_DATA__ (HTTP y Playwright fallaron)')
                    continue
                raw_path = RAW_DIR / f'{args.slug}_{date}.json'
                raw_path.write_text(
                    json.dumps(nd, ensure_ascii=False, indent=2),
                    encoding='utf-8',
                )
                own, rival_jug, rival_id = extract_players(nd, fotmob_id)
                jugaron_own = sum(1 for j in own if j['jugo'])
                jugaron_rival = sum(1 for j in rival_jug if j['jugo'])
                print(f'  {cfg["nombre"]}: {len(own)} jugadores ({jugaron_own} jugaron)')
                print(f'  Rival (id={rival_id}): {len(rival_jug)} jugadores ({jugaron_rival} jugaron)')

                target = by_date.get(date)
                if not target:
                    target = {'date': date}
                    partidos.append(target)
                    by_date[date] = target

                target['jugadores'] = own
                target['jugadoresRival'] = rival_jug

                if 'stats_partido' in target:
                    sp = target['stats_partido']
                    new_eq_xg = sum_xg(own)
                    new_rv_xg = sum_xg(rival_jug)
                    if new_eq_xg is not None:
                        sp['equipo']['xG'] = new_eq_xg
                    if new_rv_xg is not None:
                        sp['rival']['xG'] = new_rv_xg
                    print(f'  xG: {cfg["nombre"]}={new_eq_xg} rival={new_rv_xg}')

                print('  -> partido actualizado en JSON')
            except Exception as e:
                print(f'  ERROR: {e}')
            time.sleep(1)
    finally:
        close_page()

    partidos.sort(key=lambda p: (p.get('date') or '', p.get('fecha') or 0))
    payload['partidos'] = partidos
    json_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f'\nOK escrito a {json_file.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
