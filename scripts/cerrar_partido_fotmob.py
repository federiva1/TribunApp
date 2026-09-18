#!/usr/bin/env python3
"""Cierra un partido de liga usando SOLO FotMob (sin api-sports).

El camino normal (fetch_liga_partidos) arma la base con api-sports y después
enriquece con FotMob. Este script hace todo con FotMob y `liga.json` — sirve
cuando api-sports no está disponible (sin key, caído, o su agregado atrasado) y
como respaldo del pipeline. Escribe lo mismo que el pipeline:

  data/partidos/{local}-{visitante}.json   (payload completo)
  data/partidos/index.json                 (entrada del partido)
  data/fixtures/liga.json                  (resultado + estado FT)

Después conviene correr scripts/build_tabla_xg.py.

    python scripts/cerrar_partido_fotmob.py                    # todos los FT sin archivo
    python scripts/cerrar_partido_fotmob.py --fecha 7          # solo esa fecha
    python scripts/cerrar_partido_fotmob.py --api-id 1493096   # un partido puntual
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import fetch_liga_partidos as flp        # noqa: E402
import fetch_mapas as fm                 # noqa: E402
import scrape_fotmob_mundial as sfm      # noqa: E402
from clubes_map import CLUBES            # noqa: E402

LIGA = ROOT / 'data' / 'fixtures' / 'liga.json'
PARTIDOS = ROOT / 'data' / 'partidos'
AR = timezone(timedelta(hours=-3))


def competicion_de(round_str: str) -> str:
    r = (round_str or '').lower()
    if 'clausura' in r:
        return 'Clausura 2026'
    if 'apertura' in r:
        return 'Apertura 2026'
    return round_str or 'Liga Profesional 2026'


def _nd_del_partido(m):
    """__NEXT_DATA__ de FotMob para un partido de liga.json (busca por fecha UTC
    del kickoff y también el día siguiente: un 21:15 AR cae al otro día en UTC)."""
    ls, vs = m['home']['slug'], m['away']['slug']
    fid = (CLUBES.get(ls) or {}).get('fotmob') or (CLUBES.get(vs) or {}).get('fotmob')
    if not fid:
        return None, None
    utc = (m.get('status') or {}).get('utcTime') or ''
    dias = {utc[:10]}
    try:
        d = datetime.fromisoformat(utc.replace('Z', '+00:00'))
        dias.add((d + timedelta(days=1)).strftime('%Y-%m-%d'))
        dias.add((d - timedelta(days=1)).strftime('%Y-%m-%d'))
    except Exception:
        pass
    for dia in sorted(dias):
        url = fm.resolver_url(fid, dia)
        if url:
            return sfm._next_data_http(url), url
    return None, None


def _goles_detalle(nd, home_es_local):
    """matchFacts.events → goles_detalle {local:[...], visitante:[...]}.
    Excluye la tanda de penales (isPenaltyShootoutEvent)."""
    pp = nd['props']['pageProps']
    ev = ((pp.get('content') or {}).get('matchFacts') or {}).get('events', {}).get('events', [])
    out = {'local': [], 'visitante': []}
    for e in ev:
        if e.get('type') != 'Goal' or e.get('isPenaltyShootoutEvent'):
            continue
        # isHome es respecto del "home" de FotMob, que puede no ser nuestro local
        es_local = bool(e.get('isHome')) == bool(home_es_local)
        entrada = {'min': e.get('time'), 'jugador': e.get('nameStr') or '', 'asist': None}
        txt = e.get('assistStr') or ''
        m = re.search(r'assist by (.+)$', txt, re.I)
        if m:
            entrada['asist'] = m.group(1).strip()
        # En un gol en contra, el `isHome` de FotMob ya apunta al equipo que se
        # queda el gol (no al del jugador que lo hizo), así que NO se invierte:
        # queda del lado que suma, con el nombre del que lo convirtió.
        if e.get('ownGoal'):
            entrada['en_contra'] = True
        out['local' if es_local else 'visitante'].append(entrada)
    return out


def cerrar(m, forzar=False) -> str:
    ls, vs = m['home']['slug'], m['away']['slug']
    oid = f'{ls}-{vs}'
    out_file = PARTIDOS / f'{oid}.json'
    if out_file.exists() and not forzar:
        return 'skip'

    nd, url = _nd_del_partido(m)
    if not nd:
        return 'sin FotMob'
    pp = nd['props']['pageProps']
    content = pp.get('content') or {}
    if not (content.get('lineup') or {}).get('homeTeam', {}).get('starters'):
        return 'sin lineup'

    fid_loc = (CLUBES.get(ls) or {}).get('fotmob')
    home_id = sfm.fotmob_home_id(nd)
    home_es_local = (home_id == fid_loc)

    # marcador: del header de FotMob ("1 - 0"), orientado a nuestro local
    st = (pp.get('header') or {}).get('status') or {}
    score = str(st.get('scoreStr') or '')
    mm = re.match(r'\s*(\d+)\s*-\s*(\d+)', score)
    if not mm:
        return 'sin marcador'
    a, b = int(mm.group(1)), int(mm.group(2))
    gl, gv = (a, b) if home_es_local else (b, a)

    info = (content.get('matchFacts') or {}).get('infoBox') or {}
    estadio = ((info.get('Stadium') or {}).get('name')
               if isinstance(info.get('Stadium'), dict) else info.get('Stadium')) or ''
    ciudad = ((info.get('Stadium') or {}).get('city')
              if isinstance(info.get('Stadium'), dict) else '') or ''
    # FotMob manda la ciudad con la provincia pegada y CORTADA a mitad de palabra
    # ("Florencio Varela, Provincia de B"): queda solo la ciudad.
    ciudad = ciudad.split(',')[0].strip()
    if ciudad and ciudad not in estadio:
        estadio = f'{estadio}, {ciudad}' if estadio else ciudad

    payload = {
        'partido': {
            'local': ls, 'visitante': vs,
            'local_nombre': m['home'].get('name') or '', 'visitante_nombre': m['away'].get('name') or '',
            'goles_local': gl, 'goles_visitante': gv,
            'fecha': ((m.get('status') or {}).get('utcTime') or '')[:10],
            'fecha_num': m.get('fecha'), 'ronda': None,
            'estadio': estadio, 'competicion': competicion_de(m.get('round') or ''),
            'api_id': str(m.get('api_id') or ''),
            'goles_detalle': _goles_detalle(nd, home_es_local),
            'formacion': {},
        },
        'top_stats': [],
        'jugadores': {ls: [], vs: []},
    }
    # OJO: la fecha del payload es el día UTC del kickoff (utcTime[:10]) — la
    # MISMA convención que el resto del corpus y que los fixtures por club de
    # api-sports; contra ese string matchean Supabase y la web. NO convertir a
    # hora argentina aunque parezca lo natural.
    if not flp.reconstruir_jugadores_desde_fotmob(nd, payload, ls, vs):
        return 'no se pudo reconstruir el XI'
    payload = sfm._enrich_payload_from_nd(nd, payload)

    ts = sfm.team_stats_from_nd(nd, home_es_local=home_es_local)
    if ts:
        payload['top_stats'] = ts
        payload['top_stats_fuente'] = 'fotmob'
    flp.completar_nums_desde_plantel(payload)

    PARTIDOS.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    # index.json
    idx_file = PARTIDOS / 'index.json'
    idx = json.loads(idx_file.read_text(encoding='utf-8')) if idx_file.exists() else []
    idx = [e for e in idx if e.get('id') != oid]
    p = payload['partido']
    idx.append({'id': oid, 'local': ls, 'visitante': vs,
                'local_nombre': p['local_nombre'], 'visitante_nombre': p['visitante_nombre'],
                'fecha': p['fecha'], 'fecha_num': p['fecha_num'], 'ronda': None,
                'goles_local': gl, 'goles_visitante': gv,
                'competicion': p['competicion'], 'estadio': p['estadio']})
    idx.sort(key=lambda e: (e.get('fecha') or '', e.get('id') or ''))
    idx_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')

    # liga.json: resultado + FT
    liga = json.loads(LIGA.read_text(encoding='utf-8'))
    for x in liga:
        if str(x.get('api_id')) == str(m.get('api_id')):
            x['home_score'], x['away_score'] = gl, gv
            x['winner'] = ls if gl > gv else (vs if gv > gl else None)
            x['status'].update({'started': True, 'finished': True, 'short': 'FT', 'elapsed': 90})
    LIGA.write_text(json.dumps(liga, ensure_ascii=False, indent=2), encoding='utf-8')
    return f'ok {gl}-{gv}'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--fecha', type=int, help='solo esa fecha del torneo')
    ap.add_argument('--api-id', help='un partido puntual')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()

    liga = json.loads(LIGA.read_text(encoding='utf-8'))
    objetivo = []
    for m in liga:
        if args.api_id and str(m.get('api_id')) != str(args.api_id):
            continue
        if args.fecha and m.get('fecha') != args.fecha:
            continue
        if not m['home'].get('slug') or not m['away'].get('slug'):
            continue
        oid = f"{m['home']['slug']}-{m['away']['slug']}"
        ya = (PARTIDOS / f'{oid}.json').exists()
        # candidato: o ya está FT en liga.json, o el kickoff pasó hace >100 min
        st = m.get('status') or {}
        if not st.get('finished'):
            try:
                ko = datetime.fromisoformat((st.get('utcTime') or '').replace('Z', '+00:00'))
                if (datetime.now(timezone.utc) - ko).total_seconds() < 100 * 60:
                    continue
            except Exception:
                continue
        if ya and not args.force:
            continue
        objetivo.append(m)

    if not objetivo:
        print('nada para cerrar')
        return 0
    for m in objetivo:
        oid = f"{m['home']['slug']}-{m['away']['slug']}"
        print(f'{oid}: {cerrar(m, args.force)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
