"""Batch: procesa TODOS los partidos FT de la Liga Profesional → data/partidos/.

Para cada partido finalizado:
  1. Base (lineup/eventos/top_stats) desde api-sports  → fetch_mundial_match.process_fixture
  2. Resuelve la URL de FotMob (por fotmob_id del club, vía clubes_map)
  3. Enriquece jugadores (top/ataque/defensa/duelos) desde FotMob → scrape_fotmob_mundial

Idempotente: saltea los que ya tienen stats de FotMob (salvo --force).

Uso:
    python scripts/fetch_liga_partidos.py                 # FT de Clausura no procesados
    python scripts/fetch_liga_partidos.py --force         # reprocesa también los hechos
    python scripts/fetch_liga_partidos.py --torneo apertura
    python scripts/fetch_liga_partidos.py --torneo all
    python scripts/fetch_liga_partidos.py --date 2026-07-26
    python scripts/fetch_liga_partidos.py --limit 3       # solo los primeros N (probar)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import fetch_mundial_match as fmm       # noqa: E402
import scrape_fotmob_mundial as sfm     # noqa: E402
from clubes_map import CLUBES           # noqa: E402

SEASON = 2026
FINISHED = ('FT', 'AET', 'PEN')

# Copa: NADA de recorrido histórico. Solo se cargan partidos de esta fecha en
# adelante (octavos y siguientes); la fase de grupos ya jugada NO se backfillea.
# Overridable con --desde.
COPA_DESDE = '2026-08-01'

# Clubes argentinos vivos en la copa (octavos). Doble filtro con COPA_DESDE:
# solo estos clubes y solo de la fecha de corte en adelante. Los eliminados no
# aparecen con sección de copa. Actualizar si cambia el set de clasificados.
COPA_CLUBS = {
    # Libertadores — octavos
    'rosariocentral', 'independienterivadavia', 'clubatleticoplatense', 'estudiantes',
    # Sudamericana — octavos
    'bocajuniors', 'tigre', 'riverplate',
}

# Competiciones soportadas → league id de api-sports + label + si es copa.
# En copa solo se procesan los partidos que involucran a un club argentino
# (el rival extranjero se resuelve por nombre y la URL de FotMob por el fotmob_id
# del club argentino).
COMPS = {
    'liga':         {'league': 128, 'label': None,                       'copa': False},
    'libertadores': {'league': 13,  'label': 'Copa Libertadores 2026',   'copa': True},
    'sudamericana': {'league': 11,  'label': 'Copa Sudamericana 2026',    'copa': True},
}


def resolve_fotmob_url(fotmob_id: int, date_str: str):
    """Baja la página de fixtures del equipo en FotMob y devuelve la URL del
    partido de esa fecha (o None)."""
    d = sfm._next_data_http(f'https://www.fotmob.com/teams/{fotmob_id}/fixtures')
    if not d:
        return None
    try:
        fx = d['props']['pageProps']['fallback'][f'team-{fotmob_id}']['fixtures']
    except Exception:
        return None
    fixtures = fx.get('allFixtures', {}).get('fixtures', fx) if isinstance(fx, dict) else fx
    for m in fixtures or []:
        utc = (m.get('status') or {}).get('utcTime', '') or m.get('utcTime', '')
        if date_str in str(utc):
            page = m.get('pageUrl', '')
            if page:
                return f'https://www.fotmob.com{page}'
    return None


def already_enriched(out_id: str) -> bool:
    f = fmm.PARTIDOS_DIR / f'{out_id}.json'
    if not f.exists():
        return False
    try:
        d = json.loads(f.read_text(encoding='utf-8'))
    except Exception:
        return False
    jugs = [j for jj in d.get('jugadores', {}).values() for j in jj if j.get('tipo') != 'dt']
    return any(j.get('top') is not None for j in jugs)


def competicion_de(round_str: str) -> str:
    r = (round_str or '').lower()
    if 'clausura' in r:
        return 'Clausura 2026'
    if 'apertura' in r:
        return 'Apertura 2026'
    return round_str or 'Liga Profesional 2026'


def _norm_nombre(s):
    import unicodedata
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return ' '.join(s.split())


def completar_nums_desde_plantel(payload):
    """api-sports no trae el dorsal de los suplentes en el lineup (quedan num='');
    se completa desde data/planteles/{slug}.json matcheando por nombre. Así los
    'Ingresaron' de la ficha/Formaciones no quedan con el chip sin número."""
    for slug, js in (payload.get('jugadores') or {}).items():
        pth = ROOT / 'data' / 'planteles' / f'{slug}.json'
        if not pth.exists():
            continue
        by = {}
        for p in json.loads(pth.read_text(encoding='utf-8')):
            if str(p.get('num') or '').strip():
                by[_norm_nombre(p['name'])] = str(p['num'])
        for j in js:
            if j.get('tipo') == 'dt' or str(j.get('num') or '').strip():
                continue
            k = _norm_nombre(j.get('nombre'))
            n = by.get(k)
            if not n:
                toks = k.split()
                c = [v for nm, v in by.items() if toks and toks[-1] in nm.split()]
                if len(c) != 1:
                    c = [v for nm, v in by.items()
                         if len(toks) > 1 and toks[0] in nm.split() and toks[-1] in nm.split()]
                n = c[0] if len(c) == 1 else None
            if n:
                j['num'] = n
    return payload


def _top_stats_incompletas(ts) -> bool:
    """¿Las stats globales parecen un snapshot de los primeros minutos?
    En 90' reales los pases precisos suman cientos; el snapshot con lag de
    api-sports trae un puñado (caso real: "2 (67%) | 7 (88%)")."""
    if not ts:
        return True
    # Sin xG no se puede calcular la tabla xG del torneo, y FotMob siempre lo
    # trae (caso real: IndRiv-Racing F7, api-sports mandó las stats sin xG).
    if not any(s.get('label') == 'xG' for s in ts):
        return True
    for s in ts:
        if s.get('label') == 'Pases precisos':
            total = 0
            for lado in ('local', 'visitante'):
                m = re.match(r'\s*(\d+)', str(s.get(lado) or ''))
                total += int(m.group(1)) if m else 0
            return total < 150
    return True   # sin entrada de pases: api-sports mandó statistics vacío/parcial


def _faltan_titulares(payload, slugs) -> bool:
    """¿Algún equipo se quedó sin XI? Pasa cuando api-sports nunca publica
    /fixtures/lineups (caso real: IndRiv-Racing F7 — el payload quedó con los 4
    suplentes que asomaron por los eventos de cambio y ningún titular)."""
    for slug in slugs:
        js = (payload.get('jugadores') or {}).get(slug) or []
        if len([j for j in js if j.get('tipo') == 'titular']) < 11:
            return True
    return False


def reconstruir_jugadores_desde_fotmob(nd, payload, ls, vs) -> bool:
    """Arma los planteles del partido desde el lineup de FotMob.

    Sin el lineup de api-sports el JSON queda sin jugadores, y de ahí salen el
    gate de puntajes, la placa y las stats individuales. FotMob tiene el XI, el
    banco y los minutos, así que se reconstruye con él (misma regla de siempre:
    hueco de api-sports ⇒ lo tapa FotMob). Devuelve True si reconstruyó algo.
    """
    content = ((nd.get('props') or {}).get('pageProps') or {}).get('content') or {}
    lu = content.get('lineup') or {}
    if not lu:
        return False
    home_id = sfm.fotmob_home_id(nd)
    fid_loc = (CLUBES.get(ls) or {}).get('fotmob')
    fid_vis = (CLUBES.get(vs) or {}).get('fotmob')
    if home_id not in (fid_loc, fid_vis):
        return False                      # orientación no confiable: no tocar

    # stats por jugador (minutos/goles/asistencias) indexadas por id de FotMob
    ps = content.get('playerStats') or {}
    flat_by_id = {}
    for p in ps.values():
        if p.get('id') is not None:
            flat_by_id[p['id']] = (sfm.flatten_stats(p.get('stats', [])),
                                   p.get('isGoalkeeper', False))

    goles = payload.get('partido', {})
    hecho = False
    for side in ('homeTeam', 'awayTeam'):
        t = lu.get(side) or {}
        if not t.get('starters'):
            continue
        es_local = (t.get('id') == fid_loc) if fid_loc else (t.get('id') != fid_vis)
        slug = ls if es_local else vs
        recibidos = goles.get('goles_visitante' if es_local else 'goles_local') or 0

        def armar(p, tipo):
            flat, is_gk = flat_by_id.get(p.get('id'), ({}, False))
            mins = sfm.to_int(flat.get('Minutes played'))
            if tipo == 'suplente' and not mins:
                return None               # suplentes que no ingresaron: fuera
            h = p.get('horizontalLayout') or {}
            pos = ({'x': round(h['x'] * 100, 1), 'y': round(h['y'] * 100, 1)}
                   if tipo == 'titular' and h.get('x') is not None and h.get('y') is not None
                   else None)
            j = {
                'nombre': p.get('name') or '', 'id': p.get('id'), 'tipo': tipo,
                'portero': bool(is_gk), 'mvp': False,
                'num': str(p.get('shirtNumber') or ''),
                'min': mins, 'goles': sfm.to_int(flat.get('Goals')) or 0,
                'asist': sfm.to_int(flat.get('Assists')) or 0,
                'top': None, 'ataque': None, 'defensa': None, 'duelos': None,
                'portero_stats': ({'paradas': None, 'goles_contra': recibidos,
                                   'goles_evitados': None} if is_gk else None),
            }
            if pos:
                j['pos'] = pos
            return j

        jugs = [j for j in (armar(p, 'titular') for p in t['starters']) if j]
        jugs += [j for j in (armar(p, 'suplente') for p in (t.get('subs') or [])) if j]
        coach = t.get('coach') or {}
        nombre_dt = coach.get('name') if isinstance(coach, dict) else None
        if isinstance(coach, list) and coach:
            nombre_dt = (coach[0] or {}).get('name')
        if nombre_dt:
            jugs.append({'nombre': nombre_dt, 'id': None, 'tipo': 'dt', 'portero': False,
                         'mvp': False, 'num': '', 'min': None, 'goles': 0, 'asist': 0,
                         'top': None, 'ataque': None, 'defensa': None, 'duelos': None,
                         'portero_stats': None})
        if len([j for j in jugs if j['tipo'] == 'titular']) >= 11:
            payload.setdefault('jugadores', {})[slug] = jugs
            payload.setdefault('partido', {}).setdefault('formacion', {})[slug] = \
                t.get('formation') or ''
            hecho = True
    return hecho


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='Reprocesar aunque ya tenga stats FotMob')
    ap.add_argument('--date', default=None, help='Solo el/los partido(s) de esta fecha YYYY-MM-DD')
    ap.add_argument('--torneo', default='clausura', help='(liga) clausura | apertura | all')
    ap.add_argument('--competicion', default='liga',
                    help='liga | libertadores | sudamericana | copas | all')
    ap.add_argument('--desde', default=COPA_DESDE,
                    help=f'(copa) fecha mínima YYYY-MM-DD; no carga partidos anteriores (default {COPA_DESDE})')
    ap.add_argument('--limit', type=int, default=0, help='Procesar solo los primeros N (probar)')
    args = ap.parse_args()

    if args.competicion == 'all':
        comps = list(COMPS.keys())
    elif args.competicion == 'copas':
        comps = ['libertadores', 'sudamericana']
    else:
        comps = [args.competicion]

    todo = []
    for cname in comps:
        cfg = COMPS[cname]
        print(f'GET fixtures {cname} (league={cfg["league"]}) season={SEASON}...')
        data = fmm.api_get(f'fixtures?league={cfg["league"]}&season={SEASON}')
        fixtures = data.get('response', [])
        for f in fixtures:
            if f['fixture']['status']['short'] not in FINISHED:
                continue
            rnd = f['league'].get('round', '') or ''
            # En liga se filtra por torneo (clausura/apertura); en copa no aplica.
            if not cfg['copa'] and args.torneo != 'all' and args.torneo not in rnd.lower():
                continue
            date = f['fixture']['date'][:10]
            if args.date and date != args.date:
                continue
            # Copa: solo de --desde en adelante (no backfillear fase de grupos vieja).
            if cfg['copa'] and args.desde and date < args.desde:
                continue
            home, away = f['teams']['home'], f['teams']['away']
            ls = fmm.team_slug(home['id'], home['name'])
            vs = fmm.team_slug(away['id'], away['name'])
            # En copa: solo partidos de los clubes vivos en la copa (whitelist).
            if cfg['copa'] and not (ls in COPA_CLUBS or vs in COPA_CLUBS):
                continue
            comp_label = cfg['label'] if cfg['copa'] else competicion_de(rnd)
            todo.append({
                'fid': f['fixture']['id'], 'oid': f'{ls}-{vs}', 'ls': ls, 'vs': vs,
                'comp': comp_label, 'date': date,
            })

    todo.sort(key=lambda m: m['date'])
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(todo)} partidos FT objetivo ({args.competicion})\n')

    ok = skip = err = nourl = 0
    for i, m in enumerate(todo, 1):
        tag = f"[{i}/{len(todo)}] {m['oid']} ({m['date']})"
        if not args.force and already_enriched(m['oid']):
            skip += 1
            print(f'{tag}  -> skip (ya procesado)')
            continue
        print(tag)
        try:
            # 1. Base api-sports (lineup/eventos/top_stats) + index.json
            fmm.process_fixture(m['fid'], m['oid'], m['ls'], m['vs'], m['comp'])

            # 2. URL FotMob — por fotmob_id del local; fallback al visitante
            url = None
            for slug in (m['ls'], m['vs']):
                fid = (CLUBES.get(slug) or {}).get('fotmob')
                if fid:
                    url = resolve_fotmob_url(fid, m['date'])
                    if url:
                        break
            if not url:
                nourl += 1
                print('   sin URL FotMob (queda con base api-sports, sin stats individuales)')
                ok += 1
                continue

            # 3. Enriquecer jugadores desde FotMob
            out_file = fmm.PARTIDOS_DIR / f"{m['oid']}.json"
            payload = json.loads(out_file.read_text(encoding='utf-8'))
            nd = sfm._fetch_next_data(url)

            # 3b. Si api-sports nunca publicó los lineups, el payload viene sin
            #     XI (de ahí salen puntajes, placa y stats individuales): se
            #     reconstruyen los planteles desde el lineup de FotMob ANTES de
            #     enriquecer, así el enrich tiene a quién pegarle las stats.
            if _faltan_titulares(payload, (m['ls'], m['vs'])):
                if reconstruir_jugadores_desde_fotmob(nd, payload, m['ls'], m['vs']):
                    print('   planteles reconstruidos con FotMob (api-sports no dio lineups)')

            payload = sfm._enrich_payload_from_nd(nd, payload)

            # 4. Fallback de top_stats: api-sports a veces sirve las estadísticas
            #    congeladas en los primeros minutos aunque el partido esté FT
            #    (pasó con ERC-San Lorenzo F6: "2 vs 7 pases precisos"). Si las
            #    stats parecen de un partido a medio jugar, se reconstruyen desde
            #    las stats de equipo de FotMob que vienen en el mismo nd.
            if _top_stats_incompletas(payload.get('top_stats')):
                home_id = str(sfm.fotmob_home_id(nd) or '')
                fid_loc = str((CLUBES.get(m['ls']) or {}).get('fotmob') or '')
                fid_vis = str((CLUBES.get(m['vs']) or {}).get('fotmob') or '')
                if home_id in (fid_loc, fid_vis):
                    ts = sfm.team_stats_from_nd(nd, home_es_local=(home_id == fid_loc))
                    if ts:
                        payload['top_stats'] = ts
                        print('   top_stats reemplazadas con FotMob (api-sports venía incompleto)')

            completar_nums_desde_plantel(payload)
            out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'   enriquecido ({url.split("#")[0]})')
            ok += 1
        except Exception as e:
            err += 1
            print(f'   ERROR: {e}')
        time.sleep(1.5)

    print(f'\nOK {ok} · skip {skip} · sin-URL {nourl} · error {err}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
