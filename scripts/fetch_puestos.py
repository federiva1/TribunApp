"""Puesto DETALLADO de cada jugador de los 30 planteles, desde FotMob.

Los planteles (data/planteles/{slug}.json) solo traen la línea (keepers/defenders/
midfielders/attackers). "Armá tu plantel" (plantel.html) reparte la cancha en zonas
más finas (laterales, centrales, volante central, internos, enganche, extremos,
centrodelantero), así que necesita el puesto de FotMob (`positionIdsDesc`: "RB",
"CB", "CDM", "CM,CDM,CAM", "LW,RW"...). Se guarda aparte para no tocar los planteles:

    data/planteles_puestos.json = {slug: {fid: "RB", ...}, ...}

Solo el PRIMER puesto de la lista (el principal). Los que FotMob no informa no van;
plantel.html los ubica por la línea del plantel. Un pedido por club (la página de
plantel del equipo, mismo __NEXT_DATA__ que usa el resto de los scrapers).

    python scripts/fetch_puestos.py                 # los 30
    python scripts/fetch_puestos.py argentinosjuniors
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scrape_fotmob_mundial as sfm
from clubes_map import CLUBES

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'planteles_puestos.json'


def puestos_de(slug):
    fid = CLUBES[slug]['fotmob']
    d = sfm._next_data_http(f'https://www.fotmob.com/teams/{fid}/squad')
    if not d:
        raise RuntimeError('FotMob no respondió')
    team = d['props']['pageProps']['fallback'][f'team-{fid}']
    out = {}
    for grupo in team['squad']['squad']:
        for m in grupo.get('members') or []:
            desc = (m.get('positionIdsDesc') or '').split(',')[0].strip()
            if desc and m.get('id'):
                out[str(m['id'])] = desc
    return out


def main():
    slugs = [a for a in sys.argv[1:] if not a.startswith('-')] or list(CLUBES)
    try:
        data = json.loads(OUT.read_text(encoding='utf-8'))
    except FileNotFoundError:
        data = {}
    for i, slug in enumerate(slugs, 1):
        try:
            p = puestos_de(slug)
            data[slug] = p
            print(f'[{i}/{len(slugs)}] {slug:28s} {len(p)} con puesto')
        except Exception as e:
            print(f'[{i}/{len(slugs)}] {slug:28s} ERROR {e}')
        if i < len(slugs):
            time.sleep(1)
    OUT.write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'Guardado {OUT}')


if __name__ == '__main__':
    main()
