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
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright no instalado. Corre: pip install playwright && playwright install chromium")
    sys.exit(1)

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
    """Minusculas, sin tildes, sin puntos."""
    s = s.lower().strip()
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ü','u'),('ñ','n')]:
        s = s.replace(a, b)
    return s.replace('.', '')


def enrich_players(players: list, ps_by_name: dict) -> list:
    """Agrega top/ataque/defensa/duelos/portero_stats a la lista de jugadores."""
    # Construir indice normalizado
    norm_index: dict[str, tuple[str, dict]] = {}
    for fm_name, fm_data in ps_by_name.items():
        norm = normalize(fm_name)
        norm_index[norm] = (fm_name, fm_data)
        # Tambien indexar solo el apellido (ultima palabra)
        parts = norm.split()
        if parts:
            apellido = parts[-1]
            if apellido not in norm_index:
                norm_index[apellido] = (fm_name, fm_data)

    for p in players:
        nombre = p.get('nombre', '')
        norm_nombre = normalize(nombre)

        # 1. Exacto normalizado
        match = norm_index.get(norm_nombre)

        if not match:
            # 2. Apellido normalizado (api-sports da "R. Jimenez" -> apellido "jimenez")
            parts = norm_nombre.split()
            apellido = parts[-1] if parts else ''
            match = norm_index.get(apellido)

        if not match:
            continue

        fm_name, pd = match

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

        # Nombre completo desde FotMob (mejor que la abreviatura de api-sports)
        fm_name = pd.get('name', '').strip()
        if fm_name and len(fm_name) > len(nombre):
            p['nombre'] = fm_name

        # xG individual (para recalculo si es necesario)
        xg = to_num(flat.get('Expected goals (xG)'))
        if xg is not None:
            p['_xg'] = xg

    return players


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--url',      default='', help='URL del partido en FotMob')
    ap.add_argument('--id',       required=True, help='ID del partido (e.g. mexico-southafrica)')
    ap.add_argument('--headed',   action='store_true')
    ap.add_argument('--save-raw', action='store_true')
    ap.add_argument('--from-raw', action='store_true', help='Leer desde scripts/_fotmob_raw/{id}.json')
    args = ap.parse_args()

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
        if not args.url:
            print('ERROR: --url requerido (o usa --from-raw)')
            return 1
        print(f'Navegando: {args.url}')
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not args.headed, slow_mo=80)
            ctx = browser.new_context(user_agent=UA, locale='es-AR',
                                      viewport={'width': 1280, 'height': 900})
            page = ctx.new_page()
            page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
            print('Esperando FotMob...')
            time.sleep(8)
            nd = page.evaluate('() => window.__NEXT_DATA__')
            if not nd:
                page.wait_for_load_state('networkidle', timeout=30000)
                nd = page.evaluate('() => window.__NEXT_DATA__')
            browser.close()

        if nd and args.save_raw:
            RAW_DIR.mkdir(exist_ok=True)
            (RAW_DIR / f'{args.id}.json').write_text(
                json.dumps(nd, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'Raw guardado: scripts/_fotmob_raw/{args.id}.json')

    if not nd:
        print('ERROR: sin __NEXT_DATA__')
        return 1

    # ── Extraer playerStats agrupados por equipo ───────────────────────────
    content = nd['props']['pageProps']['content']
    gen     = nd['props']['pageProps'].get('general', {})

    home_id = gen.get('homeTeam', {}).get('id')
    away_id = gen.get('awayTeam', {}).get('id')

    ps_raw = content.get('playerStats', {}) or {}

    # Agrupar por teamId -> {nombre: player_data}
    ps_by_team: dict[int, dict[str, dict]] = {}
    for pid_str, p in ps_raw.items():
        tid = p.get('teamId')
        if tid not in ps_by_team:
            ps_by_team[tid] = {}
        name = (p.get('name') or '').strip()
        ps_by_team[tid][name] = p

    # Determinar qué teamId FotMob corresponde a local/visitante
    local_slug    = payload['partido']['local']
    visitante_slug = payload['partido']['visitante']

    # Heuristica: home de FotMob = primer equipo de la URL
    # Pero lo mas seguro es verificar por nombre del equipo
    home_name = (gen.get('homeTeam', {}).get('name') or '').lower()

    import sys as _sys
    _sys.path.insert(0, str(ROOT / 'scripts'))
    from fetch_mundial_match import name_to_slug
    fotmob_home_slug = name_to_slug(gen.get('homeTeam', {}).get('name') or '')
    fotmob_away_slug = name_to_slug(gen.get('awayTeam', {}).get('name') or '')

    if fotmob_home_slug == local_slug:
        local_team_id    = home_id
        visitante_team_id = away_id
    else:
        local_team_id    = away_id
        visitante_team_id = home_id

    ps_local    = ps_by_team.get(local_team_id, {})
    ps_visitante = ps_by_team.get(visitante_team_id, {})

    print(f'FotMob players: {local_slug}={len(ps_local)}  {visitante_slug}={len(ps_visitante)}')

    # ── MVP ────────────────────────────────────────────────────────────────
    potm = content.get('matchFacts', {}).get('playerOfTheMatch', {}) or {}
    mvp_name_raw = potm.get('name') or ''
    mvp_fotmob_name = (mvp_name_raw if isinstance(mvp_name_raw, str) else '').strip()

    # ── Enriquecer jugadores ──────────────────────────────────────────────
    payload['jugadores'][local_slug]     = enrich_players(payload['jugadores'].get(local_slug, []),     ps_local)
    payload['jugadores'][visitante_slug] = enrich_players(payload['jugadores'].get(visitante_slug, []), ps_visitante)

    # Marcar MVP
    for slug in (local_slug, visitante_slug):
        for p in payload['jugadores'].get(slug, []):
            if mvp_fotmob_name and p['nombre'] == mvp_fotmob_name:
                p['mvp'] = True

    # Recalcular xG del partido si vino null de api-sports
    def sum_xg(players):
        vals = [p.get('_xg') for p in players if p.get('_xg') is not None and (p.get('min') or 0) > 0]
        return round(sum(vals), 2) if vals else None

    local_xg    = sum_xg(payload['jugadores'].get(local_slug, []))
    visitante_xg = sum_xg(payload['jugadores'].get(visitante_slug, []))

    for s in payload.get('top_stats', []):
        if s['label'] == 'xG' and s.get('local') is None:
            if local_xg is not None:    s['local'] = local_xg; s['local_val'] = local_xg
            if visitante_xg is not None: s['visitante'] = visitante_xg; s['visitante_val'] = visitante_xg

    # Limpiar _xg interno
    for slug in (local_slug, visitante_slug):
        for p in payload['jugadores'].get(slug, []):
            p.pop('_xg', None)

    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Enriquecido: data/partidos/{args.id}.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
