#!/usr/bin/env python3
"""Completa los duelos disputados por tipo (terrestres_tot / aereos_tot) en las
fichas ya procesadas de data/partidos/.

FotMob da los duelos terrestres y aéreos como 'ganados/total'; hasta el
2026-10-10 el scraper guardaba solo los ganados, y sin el total no se pueden
mostrar los perdidos de cada tipo (el detalle de jugador de estadisticas.html).
Desde esa fecha el enrich los guarda solo (scrape_fotmob_mundial.duelos_totales);
esto es para las fichas anteriores. Solo AGREGA esos dos campos dentro de
`duelos`: no toca ningún otro dato de la ficha. Idempotente.

    python scripts/backfill_duelos.py                # todas las que falten
    python scripts/backfill_duelos.py aldosivi-sarmiento [otro-id ...]
    python scripts/backfill_duelos.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import fetch_mapas as fm                 # noqa: E402
import scrape_fotmob_mundial as sfm      # noqa: E402
from clubes_map import CLUBES            # noqa: E402

PARTIDOS = ROOT / 'data' / 'partidos'


def _falta(d: dict) -> bool:
    for js in (d.get('jugadores') or {}).values():
        for j in js or []:
            du = j.get('duelos') or {}
            if du and ('terrestres' in du or 'aereos' in du) \
                    and 'terrestres_tot' not in du and 'aereos_tot' not in du:
                return True
    return False


def _mismo(a: str, b: str) -> bool:
    A, B = sfm.normalize(a or '').split(), sfm.normalize(b or '').split()
    return bool(A and B) and (A[-1] in B or B[-1] in A)


def procesar(oid: str, dry: bool = False) -> str:
    f = PARTIDOS / f'{oid}.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    if not _falta(d):
        return 'skip'
    p = d.get('partido') or {}
    ls, vs = p.get('local'), p.get('visitante')
    fid_l = (CLUBES.get(ls) or {}).get('fotmob')
    fid_v = (CLUBES.get(vs) or {}).get('fotmob')
    if not (fid_l or fid_v):
        return 'sin fotmob id'
    url = fm.resolver_url(fid_l or fid_v, p.get('fecha') or '')
    if not url:
        return 'sin URL fotmob'
    nd = sfm._next_data_http(url)
    if not nd:
        return 'sin nd'
    # guarda: tiene que ser ESTE partido (la búsqueda es por día y club)
    gen = nd.get('props', {}).get('pageProps', {}).get('general') or {}
    ids = {(gen.get('homeTeam') or {}).get('id'), (gen.get('awayTeam') or {}).get('id')}
    if not {x for x in (fid_l, fid_v) if x} <= ids:
        return 'FotMob devolvió otro partido'
    ps = nd['props']['pageProps']['content'].get('playerStats') or {}
    if not ps:
        return 'sin playerStats'
    slug_de = {fid_l: ls, fid_v: vs}
    for tid in {x.get('teamId') for x in ps.values()} - set(slug_de):
        slug_de[tid] = vs if fid_l else ls          # rival extranjero (copa)
    por_id = {x.get('id'): x for x in ps.values()}

    n = 0
    for slug, js in (d.get('jugadores') or {}).items():
        for j in js or []:
            du = j.get('duelos')
            if not du or 'terrestres_tot' in du or 'aereos_tot' in du:
                continue
            x = por_id.get(j.get('id'))
            if x is None or not _mismo(x.get('name'), j.get('nombre')):
                x = next((y for y in ps.values() if slug_de.get(y.get('teamId')) == slug
                          and str(y.get('shirtNumber') or '') == str(j.get('num') or '')
                          and _mismo(y.get('name'), j.get('nombre'))), None)
            if x is None:
                continue
            tot = sfm.duelos_totales(x.get('stats', []))
            if tot:
                du.update(tot)
                n += 1
    if not n:
        return 'sin coincidencias'
    if not dry:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    return f'ok ({n} jugadores)'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', nargs='*')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--pausa', type=float, default=0.3)
    args = ap.parse_args()
    ids = args.ids or sorted(x.stem for x in PARTIDOS.glob('*.json')
                             if x.stem not in ('index', 'standings'))
    res = {}
    for oid in ids:
        try:
            d = json.loads((PARTIDOS / f'{oid}.json').read_text(encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(d, dict) or not _falta(d):
            continue
        p = d.get('partido') or {}
        if not ((CLUBES.get(p.get('local')) or {}).get('fotmob')
                or (CLUBES.get(p.get('visitante')) or {}).get('fotmob')):
            continue                                 # Mundial: fuera de alcance
        try:
            r = procesar(oid, args.dry_run)
        except Exception as e:  # noqa: BLE001
            r = f'error ({e})'
        res[oid] = r
        print(f'{oid}: {r}', flush=True)
        time.sleep(args.pausa)
    ok = sum(1 for r in res.values() if r.startswith('ok'))
    print(f'\n{ok}/{len(res)} fichas completadas')
    return 0


if __name__ == '__main__':
    sys.exit(main())
