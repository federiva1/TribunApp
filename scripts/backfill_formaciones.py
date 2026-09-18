"""Agrega la formación real + la posición de cada titular a data/partidos/*.json.

El dato sale del `lineup` de FotMob (`horizontalLayout`, normalizado 0..1 sobre la
cancha apaisada con el arquero a la izquierda). Sirve para que la placa de puntajes
dibuje la formación con la que se jugó de verdad, en vez de agrupar por el puesto
genérico del plantel.

Solo usa FotMob (HTTP), así que NO necesita la API key de api-sports.
Es idempotente: saltea los partidos que ya tienen `partido.formacion`.

Uso:
    python scripts/backfill_formaciones.py --dry-run     # previsualiza
    python scripts/backfill_formaciones.py               # todos los pendientes
    python scripts/backfill_formaciones.py --force       # recalcula también los hechos
    python scripts/backfill_formaciones.py --id deportivoriestra-estudiantes
    python scripts/backfill_formaciones.py --limit 5
"""
import argparse
import json
import sys
import time
from pathlib import Path

# La consola de Windows usa cp1252: sin esto, un print con "→" o "✗" corta el
# script a mitad de camino (pasó al cerrar Est. Río Cuarto - Sarmiento el 4/9).
# En los runners de CI la salida ya es UTF-8, así que allá no cambia nada.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):   # stdout redirigido a algo sin reconfigure
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import scrape_fotmob_mundial as sfm            # noqa: E402
from clubes_map import CLUBES                  # noqa: E402

PARTIDOS = ROOT / 'data' / 'partidos'


def fotmob_url(slug: str, fecha: str):
    """URL del partido en FotMob, buscando por fecha en los fixtures del club."""
    fid = (CLUBES.get(slug) or {}).get('fotmob')
    if not fid:
        return None
    d = sfm._next_data_http(f'https://www.fotmob.com/teams/{fid}/fixtures')
    allf = d['props']['pageProps']['fallback'][f'team-{fid}']['fixtures']['allFixtures']
    fx = allf['fixtures'] if isinstance(allf, dict) else allf
    for f in fx:
        utc = str((f.get('status') or {}).get('utcTime') or '')
        # `fecha` del JSON es el día UTC del partido → basta con comparar el prefijo.
        if utc.startswith(fecha) and f.get('pageUrl'):
            return 'https://www.fotmob.com' + f['pageUrl']
    return None


def procesar(path: Path, dry: bool) -> str:
    data = json.loads(path.read_text(encoding='utf-8'))
    p = data.get('partido') or {}
    local, visitante, fecha = p.get('local'), p.get('visitante'), p.get('fecha')
    if not (local and visitante and fecha):
        return 'sin datos de partido'

    url = fotmob_url(local, fecha) or fotmob_url(visitante, fecha)
    if not url:
        return 'sin URL de FotMob'

    nd = sfm._fetch_next_data(url)
    content = nd['props']['pageProps']['content']
    local_fotmob = (CLUBES.get(local) or {}).get('fotmob')

    lineups = sfm._lineup_por_equipo(content, local, visitante, local_fotmob)
    if not lineups:
        return 'FotMob no trae lineup'

    sfm._aplicar_lineup(data, lineups)
    con_pos = {s: sum(1 for j in data['jugadores'].get(s, []) if j.get('pos'))
               for s in lineups}
    if not dry:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    detalle = ', '.join(f'{s} {i["formacion"]} ({con_pos.get(s, 0)}/11)'
                        for s, i in lineups.items())
    return 'ok: ' + detalle


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true', help='recalcula los que ya tienen formación')
    ap.add_argument('--id', help='procesar solo este partido')
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()

    archivos = sorted(f for f in PARTIDOS.glob('*.json')
                      if f.stem not in ('index', 'standings'))
    if args.id:
        archivos = [f for f in archivos if f.stem == args.id]
        if not archivos:
            print(f'No existe data/partidos/{args.id}.json')
            return 1

    ok = skip = err = 0
    for f in archivos:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            print(f'  ✗ {f.stem:44s} ilegible: {e}')
            err += 1
            continue
        if (data.get('partido') or {}).get('formacion') and not args.force:
            skip += 1
            continue
        if args.limit and ok >= args.limit:
            break
        try:
            res = procesar(f, args.dry_run)
        except Exception as e:
            res = f'ERROR: {e}'
        marca = '✓' if res.startswith('ok') else '·'
        print(f'  {marca} {f.stem:44s} {res}')
        if res.startswith('ok'):
            ok += 1
        else:
            err += 1
        time.sleep(1.0)   # cortesía con FotMob

    print(f'\n{"[dry-run] " if args.dry_run else ""}ok {ok} · ya tenían {skip} · sin datos/error {err}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
