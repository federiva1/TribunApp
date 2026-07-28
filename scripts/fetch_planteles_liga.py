"""Baja/actualiza los planteles de los 30 clubes de la Liga Profesional desde FotMob.

Escribe data/planteles/{slug}.json con el slug del app (sin guiones), como lista de
jugadores {num, name, fid, nationality, position}. Los jugadores SIN número quedan
afuera (se listan al reportar). Reutiliza fetch_squad + EQUIPOS de scraper_planteles.py
(que ya tiene los 30 FotMob IDs).

Uso:
    python scripts/fetch_planteles_liga.py                       # todos los clubes
    python scripts/fetch_planteles_liga.py --dry-run             # no escribe, solo reporta
    python scripts/fetch_planteles_liga.py velezsarsfield racingclub   # solo esos (slug app)
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scraper_planteles as sp

ROOT = Path(__file__).resolve().parent.parent
PLANTELES = ROOT / 'data' / 'planteles'


def app_slug(scraper_slug: str) -> str:
    """velez-sarsfield -> velezsarsfield (el slug que usa el frontend)."""
    return scraper_slug.replace('-', '')


def main() -> int:
    dry = '--dry-run' in sys.argv
    only = {a for a in sys.argv[1:] if not a.startswith('--')}

    escritos = 0
    total_fuera = 0
    for team in sp.EQUIPOS:
        slug = app_slug(team['slug'])
        if only and slug not in only:
            continue
        try:
            players = sp.fetch_squad(team['fid'])
        except Exception as e:
            print(f'  ✗ {slug:26s} ERROR: {e}')
            continue

        con_num = [p for p in players if p.get('num') and str(p['num']).strip()]
        fuera = [p['name'] for p in players if not (p.get('num') and str(p['num']).strip())]
        total_fuera += len(fuera)

        nota = f'  ({len(fuera)} sin número afuera: {", ".join(fuera[:4])}{"…" if len(fuera) > 4 else ""})' if fuera else ''
        prefix = '[dry] ' if dry else '      '
        print(f'{prefix}{slug:26s} {len(con_num):2d} jugadores{nota}')

        if not dry:
            (PLANTELES / f'{slug}.json').write_text(
                json.dumps(con_num, ensure_ascii=False, indent=2), encoding='utf-8')
            escritos += 1
        time.sleep(0.6)  # cortesía con FotMob

    if dry:
        print(f'\n[dry-run] no se escribió nada. Total jugadores sin número: {total_fuera}')
    else:
        print(f'\n{escritos} planteles escritos. Jugadores sin número dejados afuera: {total_fuera}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
