"""Baja los escudos de los rivales extranjeros de copa a escudos/copa/{id}.png.

Los clubes argentinos tienen su escudo en escudos/{slug}.png, pero los rivales de
Libertadores/Sudamericana no: en data/fixtures/copas.json vienen sin slug y con una
URL de api-sports. Esa URL no sirve para las placas — html2canvas no puede exportar
un canvas con imágenes de otro dominio — así que el escudo tiene que estar en el repo.

El nombre del archivo es el ID de equipo de api-sports que ya trae la propia URL
(.../teams/124.png → escudos/copa/124.png), así el frontend lo arma sin tablas de
mapeo: le alcanza con el `logo` que ya lee de copas.json.

Idempotente: solo baja los que faltan (--force vuelve a bajar todos). Lo corre
update-fixtures.yml después de regenerar copas.json, así al avanzar de ronda los
rivales nuevos entran solos.

Uso:
  python scripts/fetch_escudos_copa.py
  python scripts/fetch_escudos_copa.py --dry-run
  python scripts/fetch_escudos_copa.py --force
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPAS = ROOT / 'data' / 'fixtures' / 'copas.json'
DESTINO = ROOT / 'escudos' / 'copa'
UA = 'Mozilla/5.0 (X11; Linux x86_64) TribunApp/1.0'


def pendientes():
    """[(team_id, url)] de los rivales sin escudo propio en el repo."""
    try:
        copas = json.loads(COPAS.read_text(encoding='utf-8'))
    except FileNotFoundError:
        print(f'No existe {COPAS}')
        return []
    vistos = {}
    for copa in copas.values():
        for p in (copa or {}).get('partidos') or []:
            for lado in ('home', 'away'):
                eq = p.get(lado) or {}
                url = eq.get('logo')
                if not url or eq.get('slug'):
                    continue                      # argentino: ya tiene escudos/{slug}.png
                m = re.search(r'/(\d+)\.png', url)
                if m:
                    vistos.setdefault(m.group(1), (url, eq.get('name') or ''))
    return [(tid, url, nom) for tid, (url, nom) in sorted(vistos.items())]


def bajar(url, path):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    if len(data) < 200:
        raise ValueError(f'respuesta demasiado chica ({len(data)} bytes)')
    path.write_bytes(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='lista sin descargar')
    ap.add_argument('--force', action='store_true', help='vuelve a bajar los que ya están')
    args = ap.parse_args()

    todos = pendientes()
    if not todos:
        print('No hay rivales de copa con logo en copas.json')
        return 0

    DESTINO.mkdir(parents=True, exist_ok=True)
    nuevos = errores = 0
    for tid, url, nom in todos:
        path = DESTINO / f'{tid}.png'
        if path.exists() and not args.force:
            continue
        if args.dry_run:
            print(f'  bajaría {tid}.png  ({nom})')
            nuevos += 1
            continue
        try:
            size = bajar(url, path)
            print(f'  {tid}.png  {nom}  ({size} bytes)')
            nuevos += 1
        except Exception as e:
            print(f'  ERROR {tid} ({nom}): {e}')
            errores += 1

    print(f'{len(todos)} rivales de copa · {nuevos} descargados · {errores} con error')
    return 1 if errores and not nuevos else 0


if __name__ == '__main__':
    sys.exit(main())
