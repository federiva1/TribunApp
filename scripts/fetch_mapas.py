#!/usr/bin/env python3
"""Mapas por jugador (calor + tiros) → data/mapas/{id}.json.

Para el detalle de jugador del tab Formaciones (estadisticas.html). Guardamos
DATOS, no dibujos: las coordenadas de cada acción del jugador y sus tiros. El
mapa de calor lo pinta la página con la estética de TribunApp (js/mapa-calor.js).

De dónde sale: FotMob publica las acciones de cada jugador en un endpoint por
partido (/api/data/heatmap/match/{matchId}/heatmaps, un solo pedido trae a todos)
como círculos SVG listos para su propia plantilla; de ahí se extraen solo los
centros (cx, cy). El shotmap viene en el mismo __NEXT_DATA__ de los playerStats.

    python scripts/fetch_mapas.py                 # partidos sin data/mapas aún
    python scripts/fetch_mapas.py --force         # regenera todos
    python scripts/fetch_mapas.py bocajuniors-lanus [otro-id ...]

Escribe data/mapas/{id}.json:
  { matchId, cancha: [105, 68], jugadores: { slug: { num: {nombre, pid, rating,
    heat: [[x, y], ...], shots: [{x, y, min, xg, tipo, gol, arco}] }}}}
Indexado por dorsal (único dentro de un partido) con el nombre para desambiguar.

Coordenadas en METROS sobre una cancha de 105×68, normalizadas por FotMob: los
dos equipos atacan de izquierda a derecha (x=0 es el arco propio; los arqueros
promedian x≈9). y=0 es la banda izquierda del equipo, igual que j.pos.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import fetch_liga_partidos as flp        # noqa: E402
import scrape_fotmob_mundial as sfm      # noqa: E402
from clubes_map import CLUBES            # noqa: E402

MAPAS = ROOT / 'data' / 'mapas'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

_fixtures_cache: dict = {}


def _http_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


_CIRCULO = re.compile(r'cx="(-?[\d.]+)"\s+cy="(-?[\d.]+)"')


def _puntos(svg: str) -> list:
    """'<circle cx="52.7" cy="34.2" r="7.5"/>...' → [[52.7, 34.2], ...]"""
    return [[round(float(x), 1), round(float(y), 1)] for x, y in _CIRCULO.findall(svg or '')]


def resolver_url(fid, date):
    if fid not in _fixtures_cache:
        _fixtures_cache[fid] = sfm._next_data_http(f'https://www.fotmob.com/teams/{fid}/fixtures')
    d = _fixtures_cache[fid]
    if not d:
        return None
    try:
        fx = d['props']['pageProps']['fallback'][f'team-{fid}']['fixtures']
    except Exception:
        return None
    fixtures = fx.get('allFixtures', {}).get('fixtures', fx) if isinstance(fx, dict) else fx
    for m in fixtures or []:
        utc = (m.get('status') or {}).get('utcTime', '') or m.get('utcTime', '')
        if date in str(utc) and m.get('pageUrl'):
            return 'https://www.fotmob.com' + m['pageUrl']
    return None


def procesar(oid: str, force: bool = False) -> str:
    out = MAPAS / f'{oid}.json'
    if out.exists() and not force:
        return 'skip'
    d = json.loads((ROOT / 'data' / 'partidos' / f'{oid}.json').read_text(encoding='utf-8'))
    p = d.get('partido') or {}
    ls, vs = p.get('local'), p.get('visitante')
    fid = (CLUBES.get(ls) or {}).get('fotmob') or (CLUBES.get(vs) or {}).get('fotmob')
    if not fid:
        return 'sin fotmob id'
    url = resolver_url(fid, p.get('fecha') or '')
    if not url:
        return 'sin URL fotmob'
    m = re.search(r'#(\d+)', url)
    if not m:
        return 'sin match id'
    match_id = int(m.group(1))

    nd = sfm._next_data_http(url)
    if not nd:
        return 'sin nd'
    content = nd['props']['pageProps']['content']
    ps = content.get('playerStats') or {}
    if not ps:
        return 'sin playerStats'

    # teamId FotMob → slug nuestro
    slug_de = {}
    for slug in (ls, vs):
        f = (CLUBES.get(slug) or {}).get('fotmob')
        if f:
            slug_de[f] = slug
    # rival extranjero (copa): el teamId que no matchea es el otro slug
    tids = {pdata.get('teamId') for pdata in ps.values()}
    for tid in tids:
        if tid not in slug_de:
            slug_de[tid] = vs if (CLUBES.get(ls) or {}).get('fotmob') in slug_de else ls

    # heatmaps prerenderizados
    try:
        import urllib.parse
        pub = urllib.parse.quote(f'https://pub.fotmob.com/prod/db/api/heatmap/match/{match_id}', safe='')
        hm = _http_json(f'https://www.fotmob.com/api/data/heatmap/match/{match_id}/heatmaps?heatmapUrl={pub}')
    except Exception as e:
        print(f'   heatmap no disponible ({e})')
        hm = {}
    # Solo los centros de los círculos: la plantilla de dibujo de FotMob no se usa.
    heat_por_pid = {int(k[1:]): _puntos(v) for k, v in (hm.get('players') or {}).items()
                    if k.startswith('p')}

    jugadores: dict = {}
    for pid_s, pdata in ps.items():
        pid = pdata.get('id')
        slug = slug_de.get(pdata.get('teamId'))
        num = str(pdata.get('shirtNumber') or '')
        if not slug or not num:
            continue
        shots = [{
            'x': round(s.get('x') or 0, 1), 'y': round(s.get('y') or 0, 1),
            'min': s.get('min'), 'xg': round(s.get('expectedGoals') or 0, 2),
            'tipo': s.get('eventType') or '', 'gol': s.get('eventType') == 'Goal',
            'arco': bool(s.get('isOnTarget')),
        } for s in (pdata.get('shotmap') or []) if not s.get('isOwnGoal')]
        # el endpoint de heatmaps indexa por optaId (p{optaId}), no por el id FotMob
        try:
            heat = heat_por_pid.get(int(pdata.get('optaId'))) or []
        except (TypeError, ValueError):
            heat = []
        rating = None
        flat = sfm.flatten_stats(pdata.get('stats', []))
        try:
            rating = float(flat.get('FotMob rating'))
        except (TypeError, ValueError):
            pass
        if not shots and not heat:
            continue
        jugadores.setdefault(slug, {})[num] = {
            'nombre': pdata.get('name') or '', 'pid': pid,
            'rating': rating, 'heat': heat, 'shots': shots,
        }

    if not jugadores:
        return 'sin mapas'
    MAPAS.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'matchId': match_id, 'cancha': [105, 68], 'jugadores': jugadores},
                              ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return 'ok'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', nargs='*', help='ids puntuales (default: todos los de liga/copas)')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()

    if args.ids:
        objetivo = args.ids
    else:
        objetivo = []
        for f in sorted((ROOT / 'data' / 'partidos').glob('*.json')):
            if f.name in ('index.json', 'standings.json'):
                continue
            comp = (json.loads(f.read_text(encoding='utf-8')).get('partido') or {}).get('competicion') or ''
            if re.search(r'clausura|apertura|libertadores|sudamericana', comp, re.I):
                objetivo.append(f.stem)

    ok = skip = err = 0
    for oid in objetivo:
        try:
            r = procesar(oid, args.force)
        except Exception as e:
            r = f'ERROR {e}'
        if r == 'ok':
            ok += 1
        elif r == 'skip':
            skip += 1
        else:
            err += 1
            print(f'{oid}: {r}')
        if r != 'skip':
            time.sleep(0.3)
    print(f'ok={ok} skip={skip} sin_mapas/err={err}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
