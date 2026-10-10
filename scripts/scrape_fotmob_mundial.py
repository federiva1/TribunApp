"""Enriquece data/partidos/{id}.json con stats individuales por jugador desde FotMob.

Paso 1: fetch_mundial_match.py  (API -> lineup + match stats)
Paso 2: este script             (FotMob -> top/ataque/defensa/duelos por jugador)

Uso:
    python scripts/scrape_fotmob_mundial.py ^
        --url "https://www.fotmob.com/matches/south-africa-vs-mexico/1einvt#4667751" ^
        --id mexico-southafrica

    # Guardar raw + no abrir browser de nuevo en proximas corridas:
    python scripts/scrape_fotmob_mundial.py --url "..." --id mexico-southafrica --save-raw
    python scripts/scrape_fotmob_mundial.py --url "" --id mexico-southafrica --from-raw

    # Browser visible para debug:
    python scripts/scrape_fotmob_mundial.py --url "..." --id mexico-southafrica --headed

Estructura FotMob __NEXT_DATA__:
  props.pageProps.general.homeTeam/awayTeam  {id, name}
  props.pageProps.content.playerStats        {pid: {name, teamId, isGoalkeeper, stats:[{title,stats:{label:{stat:{value}}}}]}}

Stats por jugador que extraemos:
  top:     tiros_totales, disparos_puerta, oport_creadas, grandes_oport, acc_defensivas, pases_precisos
  ataque:  toques, toques_area, regates, pases_ultimo_tercio, perdida_balon
  defensa: acc_defensivas, entradas, interceptaciones, recuperaciones, despejes, bloqueos, regateado
  duelos:  ganados, perdidos, terrestres, aereos, faltas, faltas_recibidas
  portero_stats: paradas, goles_evitados  (goles_contra ya viene del API)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

# Playwright es opcional: el camino primario es HTTP (urllib), que funciona detrás
# del proxy del entorno cloud y en GitHub Actions donde FotMob bloquea el browser.
# Playwright queda como fallback (útil en la compu local).
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT         = Path(__file__).resolve().parent.parent
PARTIDOS_DIR = ROOT / 'data' / 'partidos'
RAW_DIR      = ROOT / 'scripts' / '_fotmob_raw'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

TOP_MAP = {
    'Total shots':            'tiros_totales',
    'Shots on target':        'disparos_puerta',
    'Chances created':        'oport_creadas',
    'Big chances created':    'grandes_oport',
    'Defensive actions':      'acc_defensivas',
    'Accurate passes':        'pases_precisos',
}
ATAQUE_MAP = {
    'Touches':                        'toques',
    'Touches in opposition box':      'toques_area',
    'Successful dribbles':            'regates',
    'Passes into final third':        'pases_ultimo_tercio',
    'Key passes':                     'pases_ultimo_tercio',
    'Accurate long balls':            'tiros_largos',
    'Dispossessed':                   'perdida_balon',
}
DEFENSA_MAP = {
    'Defensive actions':              'acc_defensivas',
    'Tackles':                        'entradas',
    'Interceptions':                  'interceptaciones',
    'Recoveries':                     'recuperaciones',
    'Clearances':                     'despejes',
    'Blocked shots':                  'bloqueos',
    'Dribbled past':                  'regateado',
}
DUELOS_MAP = {
    'Duels won':                      'ganados',
    'Duels lost':                     'perdidos',
    'Ground duels won':               'terrestres',
    'Aerial duels won':               'aereos',
    'Fouls committed':                'faltas',
    'Was fouled':                     'faltas_recibidas',
}
GK_MAP = {
    'Saves':           'paradas',
    'Goals prevented': 'goles_evitados',
}


def to_int(v):
    if v in (None, ''):
        return None
    try:
        return int(float(str(v)))
    except Exception:
        return None


def to_num(v):
    if v in (None, ''):
        return None
    try:
        f = float(str(v))
        return int(f) if f == int(f) else round(f, 2)
    except Exception:
        return None


def flatten_stats(sections: list) -> dict:
    flat = {}
    for sec in (sections or []):
        for label, data in (sec.get('stats') or {}).items():
            if label == 'Shotmap':
                continue
            val = (data or {}).get('stat', {}).get('value') if isinstance(data, dict) else None
            if label not in flat:
                flat[label] = val
    return flat


def build_section(flat: dict, field_map: dict) -> dict | None:
    result = {}
    for fotmob_label, field in field_map.items():
        val = flat.get(fotmob_label)
        if val is None:
            continue
        result[field] = to_num(val)
    return result if result else None


def normalize(s: str) -> str:
    """Minusculas, sin diacriticos (cualquier idioma), sin puntos.

    api-sports da diacriticos completos ('Matej Kovar' con hacek/acute) y FotMob
    versiones parcialmente despojadas; stripear TODO combining mark uniforma ambos.
    """
    if not s:
        return ''
    s = s.lower().strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('.', '')


def _tokset(norm: str) -> frozenset:
    """Conjunto de tokens (separa por espacio y guion). Ignora orden apellido/nombre."""
    return frozenset(t for t in norm.replace('-', ' ').split() if t)


def enrich_players(players: list, ps_by_name: dict) -> list:
    """Agrega top/ataque/defensa/duelos/portero_stats a la lista de jugadores."""
    # Construir indice normalizado
    norm_index: dict[str, tuple[str, dict]] = {}
    tokset_index: dict[frozenset, tuple[str, dict]] = {}
    fm_list: list[tuple[frozenset, str, dict]] = []
    for fm_name, fm_data in ps_by_name.items():
        norm = normalize(fm_name)
        norm_index[norm] = (fm_name, fm_data)
        # Tambien indexar solo el apellido (ultima palabra)
        parts = norm.split()
        if parts:
            apellido = parts[-1]
            if apellido not in norm_index:
                norm_index[apellido] = (fm_name, fm_data)
        # Indice por conjunto de tokens (ignora orden — nombres asiaticos van invertidos
        # en api-sports "Kim Seung-gyu" vs FotMob "Seung-Gyu Kim")
        toks = _tokset(norm)
        if toks:
            tokset_index.setdefault(toks, (fm_name, fm_data))
            fm_list.append((toks, fm_name, fm_data))

    # Una entrada FotMob no puede asignarse a dos jugadores distintos: si el
    # apellido colisiona (ej. dos "Gueye" / "Ndiaye" en la misma seleccion) el
    # match por apellido/solapamiento copiaba las MISMAS stats a ambos y producia
    # duplicados. Reservar cada FotMob una sola vez evita ese caso.
    used_fm: set[str] = set()

    for p in players:
        nombre = p.get('nombre', '')
        norm_nombre = normalize(nombre)

        # 1. Exacto normalizado
        match = norm_index.get(norm_nombre)

        if not match:
            # 2. Apellido normalizado (api-sports da "R. Jimenez" -> apellido "jimenez")
            parts = norm_nombre.split()
            apellido = parts[-1] if parts else ''
            cand = norm_index.get(apellido)
            # Solo aceptar el match por apellido si ese FotMob aun no fue usado
            # (si ya esta tomado, el apellido es ambiguo -> no arriesgar).
            if cand and cand[0] not in used_fm:
                match = cand

        if not match:
            # 3. Conjunto de tokens exacto (orden-independiente)
            match = tokset_index.get(_tokset(norm_nombre))

        if not match:
            # 4. Mejor solapamiento de tokens (>=2 en comun y ganador unico)
            mine = _tokset(norm_nombre)
            scored = sorted(
                ((len(mine & toks), fm_name, fm_data) for toks, fm_name, fm_data in fm_list),
                key=lambda t: t[0], reverse=True)
            if scored and scored[0][0] >= 2 and (len(scored) == 1 or scored[1][0] < scored[0][0]):
                match = (scored[0][1], scored[0][2])

        if not match:
            continue

        fm_name, pd = match

        # Si esta entrada FotMob ya fue asignada a otro jugador, no duplicar stats.
        if fm_name in used_fm:
            continue
        used_fm.add(fm_name)

        flat = flatten_stats(pd.get('stats', []))
        is_gk = pd.get('isGoalkeeper', False)

        p['top']     = build_section(flat, TOP_MAP)
        p['ataque']  = build_section(flat, ATAQUE_MAP)
        p['defensa'] = build_section(flat, DEFENSA_MAP)
        p['duelos']  = build_section(flat, DUELOS_MAP)

        if is_gk:
            saves = to_int(flat.get('Saves'))
            gev   = to_num(flat.get('Goals prevented'))
            existing_gk = p.get('portero_stats') or {}
            p['portero_stats'] = {
                'paradas':        saves,
                'goles_contra':   existing_gk.get('goles_contra'),
                'goles_evitados': gev,
            }

        # NO sobreescribir el nombre con el de FotMob: los nombres de api-sports
        # (lineup del Mundial) son completos y autoritativos. El overwrite por
        # match difuso renombraba mal cuando el apellido colisionaba (ej. Pape
        # Gueye -> "Idrissa Gana Gueye"), generando duplicados.

        # xG individual (para recalculo si es necesario)
        xg = to_num(flat.get('Expected goals (xG)'))
        if xg is not None:
            p['_xg'] = xg

    return players


# ── stats de EQUIPO desde FotMob (fallback de top_stats) ─────────────────────
# api-sports a veces sirve /fixtures/statistics con un snapshot de los primeros
# minutos aunque el partido esté FT (lag largo). FotMob trae las stats de equipo
# completas en el mismo __NEXT_DATA__ del que ya sacamos los playerStats, así que
# se puede reconstruir top_stats (mismo schema de data/partidos) sin otra fuente.
# (key FotMob, label nuestro, tipo) — mismos labels que fetch_mundial_match.STAT_MAP.
FOTMOB_TOP_STATS = [
    ('BallPossesion',   'Posesion',             'posesion'),
    ('expected_goals',  'xG',                   'numero'),
    ('total_shots',     'Tiros totales',        'numero'),
    ('ShotsOnTarget',   'Tiros al arco',        'numero'),
    ('touches_opp_box', 'Toques en area rival', 'numero'),
    ('corners',         'Corners',              'numero'),
    ('fouls',           'Faltas',               'numero'),
    ('yellow_cards',    'Tarjetas amarillas',   'numero'),
    ('red_cards',       'Tarjetas rojas',       'numero'),
]


def _team_stats_flat(nd: dict) -> dict:
    """{key: [home, away]} con las stats de equipo del partido (Periods → All)."""
    content = ((nd.get('props') or {}).get('pageProps') or {}).get('content') or {}
    per = ((content.get('stats') or {}).get('Periods') or {}).get('All') or {}
    flat = {}
    for grupo in per.get('stats') or []:
        for s in grupo.get('stats') or []:
            k, v = s.get('key'), s.get('stats')
            if k and k not in flat and isinstance(v, list) and len(v) == 2:
                flat[k] = v
    return flat


def fotmob_home_id(nd: dict):
    """FotMob id del equipo que FotMob considera local (para orientar los arrays)."""
    g = ((nd.get('props') or {}).get('pageProps') or {}).get('general') or {}
    return (g.get('homeTeam') or {}).get('id')


def fotmob_away_id(nd: dict):
    """FotMob id del visitante. Junto con fotmob_home_id permite orientar los
    arrays reconociendo UNO solo de los dos equipos (en copa el rival extranjero
    no está en clubes_map)."""
    g = ((nd.get('props') or {}).get('pageProps') or {}).get('general') or {}
    return (g.get('awayTeam') or {}).get('id')


def fotmob_match_date(nd: dict) -> str:
    """Día UTC del partido según FotMob ('YYYY-MM-DD'), para confirmar que la
    página resuelta es la del partido que estamos procesando."""
    g = ((nd.get('props') or {}).get('pageProps') or {}).get('general') or {}
    return str(g.get('matchTimeUTCDate') or '')[:10]


def venue_from_nd(nd: dict) -> str:
    """'Estadio, Ciudad' desde FotMob. api-sports a veces no trae el nombre del
    estadio y hasta erra la ciudad (caso real: Fluminense-Platense en el Maracaná
    figuraba como 'Buenos Aires')."""
    c = ((nd.get('props') or {}).get('pageProps') or {}).get('content') or {}
    st = ((c.get('matchFacts') or {}).get('infoBox') or {}).get('Stadium') or {}
    nombre = (st.get('name') or '').strip()
    ciudad = (st.get('city') or '').split(',')[0].strip()
    return ', '.join(x for x in (nombre, ciudad) if x)


def team_stats_from_nd(nd: dict, home_es_local: bool = True) -> list | None:
    """top_stats (schema data/partidos) desde las stats de equipo de FotMob.
    home_es_local: si el home de FotMob coincide con nuestro `local` (chequear
    con fotmob_home_id contra el fotmob_id del club)."""
    flat = _team_stats_flat(nd)
    if not flat:
        return None
    i_loc, i_vis = (0, 1) if home_es_local else (1, 0)

    def num(x):
        if x in (None, ''):
            return None
        try:
            f = float(str(x))
            return round(f, 2) if '.' in str(x) else int(f)
        except (TypeError, ValueError):
            return None

    out = []
    for key, label, tipo in FOTMOB_TOP_STATS:
        if key not in flat:
            continue
        l, v = num(flat[key][i_loc]), num(flat[key][i_vis])
        if l is None and v is None:
            continue
        out.append({'label': label, 'local': l, 'visitante': v,
                    'tipo': tipo, 'local_val': l, 'visitante_val': v})

    ap = flat.get('accurate_passes')   # formato "229 (71%)"
    if ap:
        def parse(s):
            m = re.match(r'\s*(\d+)\s*\((\d+)%\)', str(s))
            return (int(m.group(1)), int(m.group(2))) if m else (None, None)
        (ln, lp), (vn, vp) = parse(ap[i_loc]), parse(ap[i_vis])
        if ln is not None and vn is not None:
            out.append({'label': 'Pases precisos',
                        'local': f'{ln} ({lp}%)', 'visitante': f'{vn} ({vp}%)',
                        'tipo': 'texto', 'local_val': lp, 'visitante_val': vp})
    return out or None


def _next_data_http(url: str) -> dict | None:
    """Descarga la página y extrae el JSON de <script id="__NEXT_DATA__">.
    FotMob hace SSR, así que playerStats/fixtures vienen embebidos en el HTML —
    no hace falta browser. Usa el proxy del entorno vía las env vars HTTPS_PROXY.
    Devuelve None si falla (para que el caller caiga a Playwright)."""
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


def _next_data_browser(url: str, headed: bool = False) -> dict:
    """Fallback con Playwright (para la compu local donde el browser sí llega)."""
    if sync_playwright is None:
        raise RuntimeError('playwright no instalado y el camino HTTP falló')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed, slow_mo=80)
        ctx = browser.new_context(user_agent=UA, locale='es-AR',
                                  viewport={'width': 1280, 'height': 900},
                                  ignore_https_errors=True)
        page = ctx.new_page()
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        print('Esperando FotMob...')
        time.sleep(8)
        nd = page.evaluate('() => window.__NEXT_DATA__')
        if not nd:
            page.wait_for_load_state('networkidle', timeout=30000)
            nd = page.evaluate('() => window.__NEXT_DATA__')
        browser.close()
    if not nd:
        raise RuntimeError('Sin __NEXT_DATA__')
    return nd


def resolve_fotmob_url(stats_id: str, date_str: str, local_slug: str) -> str:
    """Busca la URL de FotMob del partido usando la página de fixtures del equipo local."""
    plantel_file = ROOT / 'data' / 'planteles' / f'{local_slug}.json'
    if not plantel_file.exists():
        raise FileNotFoundError(f'No existe data/planteles/{local_slug}.json')
    fotmob_id = json.loads(plantel_file.read_text(encoding='utf-8')).get('fotmob_id')
    if not fotmob_id:
        raise ValueError(f'fotmob_id no encontrado para {local_slug}')

    print(f'  Buscando URL FotMob (team={fotmob_id}, fecha={date_str})...')
    fixtures_url = f'https://www.fotmob.com/teams/{fotmob_id}/fixtures'
    d = _next_data_http(fixtures_url)        # camino primario: HTTP (proxy)
    if d is None:                            # fallback: browser
        d = _next_data_browser(fixtures_url)

    fx = d['props']['pageProps']['fallback'][f'team-{fotmob_id}']['fixtures']
    fixtures = fx.get('allFixtures', {}).get('fixtures', fx) if isinstance(fx, dict) else fx
    for m in fixtures:
        utc = (m.get('status') or {}).get('utcTime', '') or m.get('utcTime', '')
        if date_str in str(utc):
            page_url = m.get('pageUrl', '')
            if page_url:
                return f'https://www.fotmob.com{page_url}'
    raise RuntimeError(f'No se encontró partido en FotMob para {local_slug} en {date_str}')


def auto_mode(headed: bool = False) -> int:
    """Procesa todos los partidos FT en mundial.json que ya tienen data/partidos/{stats_id}.json
    pero les faltan stats individuales (top/ataque/defensa/duelos todos None)."""
    mundial_file = ROOT / 'data' / 'fixtures' / 'mundial.json'
    ms = json.loads(mundial_file.read_text(encoding='utf-8'))
    pending = []
    for m in ms:
        st = m.get('status', {}) or {}
        if not st.get('finished'):
            continue
        sid = m.get('stats_id')
        if not sid:
            continue
        out_file = PARTIDOS_DIR / f'{sid}.json'
        if not out_file.exists():
            continue
        # Verificar si ya tiene stats de FotMob (cualquier jugador con top != None)
        d = json.loads(out_file.read_text(encoding='utf-8'))
        all_jugs = [j for jugs in d.get('jugadores', {}).values() for j in jugs if j.get('tipo') != 'dt']
        if any(j.get('top') is not None for j in all_jugs):
            continue  # ya tiene FotMob stats
        utc = st.get('utcTime', '')
        date_str = utc[:10] if utc else ''
        local_slug = m.get('home', {}).get('slug', '')
        pending.append((sid, date_str, local_slug))

    if not pending:
        print('auto: nada que procesar (todos los FT ya tienen stats FotMob)')
        return 0

    errors = []
    for sid, date_str, local_slug in pending:
        try:
            url = resolve_fotmob_url(sid, date_str, local_slug)
            print(f'  URL resuelta: {url}')
            # Reutilizar el flujo normal pasando la URL
            import sys
            sys.argv = ['scrape_fotmob_mundial.py', '--url', url, '--id', sid]
            if headed:
                sys.argv.append('--headed')
        except Exception as e:
            print(f'  ERROR resolviendo URL para {sid}: {e}')
            errors.append(sid)
            continue
        # Procesar inline
        out_file = PARTIDOS_DIR / f'{sid}.json'
        payload = json.loads(out_file.read_text(encoding='utf-8'))
        try:
            nd = _fetch_next_data(url, headed)
            enriched = _enrich_payload_from_nd(nd, payload)
            out_file.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'  Enriquecido: data/partidos/{sid}.json')
        except Exception as e:
            print(f'  ERROR procesando FotMob para {sid}: {e}')
            errors.append(sid)

    if errors:
        print(f'Errores en: {errors}')
        return 1
    return 0


def _fetch_next_data(url: str, headed: bool = False) -> dict:
    """Retorna __NEXT_DATA__ del partido. Primario: HTTP (urllib/proxy);
    fallback: Playwright (compu local)."""
    nd = _next_data_http(url)
    if nd is not None:
        return nd
    return _next_data_browser(url, headed)


def _lineup_por_equipo(content: dict, local_slug: str, visitante_slug: str,
                       local_team_id) -> dict:
    """Formación real + posición de cada titular, del `lineup` de FotMob.

    `horizontalLayout` viene normalizado 0..1 sobre la cancha APAISADA y con el
    arquero a la izquierda, que es exactamente la orientación de la placa para
    compartir → se guarda como % sin transformar.

    Devuelve {slug: {'formacion': '4-3-3',
                     'pos':     {nombre_normalizado: {x, y}},
                     'por_num': {dorsal: {x, y}}}}.
    """
    lu = content.get('lineup') or {}
    out: dict = {}
    for side in ('homeTeam', 'awayTeam'):
        t = lu.get(side) or {}
        if not t.get('starters'):
            continue
        slug = local_slug if t.get('id') == local_team_id else visitante_slug
        pos, por_num = {}, {}
        for p in t['starters']:
            h = p.get('horizontalLayout') or {}
            if h.get('x') is None or h.get('y') is None:
                continue
            xy = {'x': round(h['x'] * 100, 1), 'y': round(h['y'] * 100, 1)}
            pos[normalize(p.get('name') or '')] = xy
            num = str(p.get('shirtNumber') or '').strip()
            if num:
                por_num[num] = xy
        if pos:
            out[slug] = {'formacion': t.get('formation') or '',
                         'pos': pos, 'por_num': por_num}
    return out


def _aplicar_lineup(payload: dict, lineups: dict) -> None:
    """Escribe formación (en `partido`) y `pos` por titular (en cada jugador).

    El match es por DORSAL (único dentro de un XI y estable entre las dos fuentes),
    con fallback por nombre normalizado y por apellido. Hace falta el fallback
    porque api-sports a veces abrevia ("D. Fernandez") y porque en los apellidos
    compuestos cada fuente elige una parte distinta ("Hernán López Muñoz").
    Los que no matchean quedan sin `pos` y el frontend cae al layout por líneas.
    """
    formaciones = {}
    for slug, info in lineups.items():
        formaciones[slug] = info['formacion']
        por_num = info.get('por_num') or {}
        por_apellido = {}
        for n, xy in info['pos'].items():
            for tok in n.split():
                por_apellido.setdefault(tok, []).append(xy)
        for j in payload['jugadores'].get(slug, []):
            if j.get('tipo') != 'titular':
                continue
            xy = por_num.get(str(j.get('num') or '').strip())
            if xy is None:
                n = normalize(j.get('nombre') or '')
                xy = info['pos'].get(n)
                if xy is None:
                    # Cualquier token del nombre que identifique a un solo titular
                    # (los apellidos compuestos no coinciden token a token).
                    cand = [c for tok in n.split() for c in por_apellido.get(tok, [])]
                    unicos = [dict(t) for t in {tuple(sorted(c.items())) for c in cand}]
                    xy = unicos[0] if len(unicos) == 1 else None
            if xy:
                j['pos'] = xy
    if formaciones:
        payload['partido']['formacion'] = formaciones


def _enrich_payload_from_nd(nd: dict, payload: dict) -> dict:
    """Extrae playerStats del __NEXT_DATA__ de FotMob y enriquece el payload del
    partido (top/ataque/defensa/duelos, MVP, xG). Devuelve el payload modificado.
    Lo usan tanto main() (--url) como auto_mode() (--auto)."""
    content = nd['props']['pageProps']['content']
    gen     = nd['props']['pageProps'].get('general', {})

    home_id = gen.get('homeTeam', {}).get('id')
    away_id = gen.get('awayTeam', {}).get('id')

    ps_raw = content.get('playerStats', {}) or {}
    ps_by_team: dict = {}
    for _pid, p in ps_raw.items():
        tid = p.get('teamId')
        ps_by_team.setdefault(tid, {})
        ps_by_team[tid][(p.get('name') or '').strip()] = p

    local_slug     = payload['partido']['local']
    visitante_slug = payload['partido']['visitante']

    _sys = sys
    _sys.path.insert(0, str(ROOT / 'scripts'))
    from fetch_mundial_match import name_to_slug

    # Mapeo local/visitante: para clubes de Liga usamos el fotmob_id (robusto, no
    # depende de la grafía del nombre — ej. "Newell's"); para el Mundial, por nombre.
    local_fotmob = None
    try:
        from clubes_map import CLUBES
        local_fotmob = (CLUBES.get(local_slug) or {}).get('fotmob')
    except Exception:
        local_fotmob = None

    if local_fotmob and local_fotmob in (home_id, away_id):
        if local_fotmob == home_id:
            local_team_id, visitante_team_id = home_id, away_id
        else:
            local_team_id, visitante_team_id = away_id, home_id
    else:
        fotmob_home_slug = name_to_slug(gen.get('homeTeam', {}).get('name') or '')
        if fotmob_home_slug == local_slug:
            local_team_id, visitante_team_id = home_id, away_id
        else:
            local_team_id, visitante_team_id = away_id, home_id

    ps_local     = ps_by_team.get(local_team_id, {})
    ps_visitante = ps_by_team.get(visitante_team_id, {})
    print(f'FotMob players: {local_slug}={len(ps_local)}  {visitante_slug}={len(ps_visitante)}')

    # MVP — FotMob da name como string o dict {firstName,lastName,fullName}
    potm = content.get('matchFacts', {}).get('playerOfTheMatch', {}) or {}
    mvp_name_raw = potm.get('name') or ''
    mvp_fotmob_name = (mvp_name_raw.get('fullName') or '').strip() \
        if isinstance(mvp_name_raw, dict) else str(mvp_name_raw).strip()
    mvp_id = potm.get('id')

    payload['jugadores'][local_slug]     = enrich_players(payload['jugadores'].get(local_slug, []),     ps_local)
    payload['jugadores'][visitante_slug] = enrich_players(payload['jugadores'].get(visitante_slug, []), ps_visitante)

    # Formación real + posición de cada titular en la cancha (para la placa).
    try:
        lineups = _lineup_por_equipo(content, local_slug, visitante_slug, local_team_id)
        if lineups:
            _aplicar_lineup(payload, lineups)
            print('Formación: ' + ', '.join(f'{s}={i["formacion"]}' for s, i in lineups.items()))
        else:
            print('Formación: FotMob no trajo lineup (se usa el layout por líneas)')
    except Exception as e:
        print(f'Formación: no se pudo extraer ({e})')

    # El id del POTM es de FotMob (≠ id api-sports), así que el match es por nombre.
    # api-sports suele abreviar ("L. Messi") y no matchea el tokset exacto con
    # "Lionel Messi" → fallback: mismo apellido + (primer token igual o inicial).
    mp = normalize(mvp_fotmob_name).split() if mvp_fotmob_name else []
    mvp_tokset = _tokset(normalize(mvp_fotmob_name)) if mvp_fotmob_name else frozenset()

    def _es_mvp(nombre):
        if not mvp_fotmob_name:
            return False
        ntok = _tokset(normalize(nombre))
        if ntok == mvp_tokset:
            return True
        np = normalize(nombre).split()
        if np and mp and np[-1] == mp[-1]:                       # mismo apellido
            if np[0] == mp[0] or (len(np[0]) == 1 and mp[0].startswith(np[0])):
                return True                                       # "l" ~ "lionel"
        return False

    for slug in (local_slug, visitante_slug):
        for p in payload['jugadores'].get(slug, []):
            if (mvp_id is not None and p.get('id') == mvp_id) or _es_mvp(p['nombre']):
                p['mvp'] = True

    def sum_xg(players):
        vals = [p.get('_xg') for p in players if p.get('_xg') is not None and (p.get('min') or 0) > 0]
        return round(sum(vals), 2) if vals else None

    local_xg     = sum_xg(payload['jugadores'].get(local_slug, []))
    visitante_xg = sum_xg(payload['jugadores'].get(visitante_slug, []))
    for s in payload.get('top_stats', []):
        if s['label'] == 'xG' and s.get('local') is None:
            if local_xg is not None:     s['local'] = local_xg;     s['local_val'] = local_xg
            if visitante_xg is not None: s['visitante'] = visitante_xg; s['visitante_val'] = visitante_xg

    for slug in (local_slug, visitante_slug):
        for p in payload['jugadores'].get(slug, []):
            p.pop('_xg', None)

    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--url',      default='', help='URL del partido en FotMob')
    ap.add_argument('--id',       default='', help='ID del partido (e.g. mexico-southafrica)')
    ap.add_argument('--auto',     action='store_true', help='Procesar todos los FT sin stats FotMob')
    ap.add_argument('--headed',   action='store_true')
    ap.add_argument('--save-raw', action='store_true')
    ap.add_argument('--from-raw', action='store_true', help='Leer desde scripts/_fotmob_raw/{id}.json')
    args = ap.parse_args()

    if args.auto:
        return auto_mode(headed=args.headed)

    if not args.id:
        ap.error('--id requerido (o usa --auto)')

    out_file = PARTIDOS_DIR / f'{args.id}.json'
    if not out_file.exists():
        print(f'ERROR: {out_file} no existe. Corre primero fetch_mundial_match.py')
        return 1

    payload = json.loads(out_file.read_text(encoding='utf-8'))

    # ── Obtener __NEXT_DATA__ ──────────────────────────────────────────────
    nd = None

    if args.from_raw:
        raw_file = RAW_DIR / f'{args.id}.json'
        if not raw_file.exists():
            print(f'ERROR: no existe {raw_file}')
            return 1
        nd = json.loads(raw_file.read_text(encoding='utf-8'))
        print(f'Leyendo raw: {raw_file.name}')
    else:
        # Si no se pasa --url, intentar resolverla automáticamente desde mundial.json
        url = args.url
        if not url:
            try:
                ms = json.loads((ROOT / 'data' / 'fixtures' / 'mundial.json').read_text(encoding='utf-8'))
                match = next((m for m in ms if m.get('stats_id') == args.id), None)
                if match:
                    date_str = (match.get('status') or {}).get('utcTime', '')[:10]
                    local_slug = match.get('home', {}).get('slug', '')
                    url = resolve_fotmob_url(args.id, date_str, local_slug)
            except Exception as e:
                print(f'No se pudo resolver URL automáticamente: {e}')
        if not url:
            print('ERROR: --url requerido (o usa --from-raw)')
            return 1
        print(f'Navegando: {url}')
        nd = _fetch_next_data(url, args.headed)

        if nd and args.save_raw:
            RAW_DIR.mkdir(exist_ok=True)
            (RAW_DIR / f'{args.id}.json').write_text(
                json.dumps(nd, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'Raw guardado: scripts/_fotmob_raw/{args.id}.json')

    if nd is None:
        print('ERROR: sin __NEXT_DATA__')
        return 1

    payload = _enrich_payload_from_nd(nd, payload)
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Enriquecido: data/partidos/{args.id}.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
