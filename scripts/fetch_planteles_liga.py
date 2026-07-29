"""Baja/actualiza los planteles de los 30 clubes de la Liga Profesional desde FotMob.

Escribe data/planteles/{slug}.json con el slug del app (sin guiones), como lista de
jugadores {num, name, fid, nationality, position}. Reutiliza fetch_squad + EQUIPOS de
scraper_planteles.py (que ya tiene los 30 FotMob IDs).

Flujo: scrapea FotMob → los que quedan sin dorsal se completan con api-sports
(backfill_plantel_nums.fill_blanks) → se escriben TODOS los jugadores. Los que igual
quedan sin número (juveniles/reserva que ninguna fuente tiene) se conservan en blanco.
Los dorsales no cambian durante el torneo: se corre una vez (o ante altas/bajas).

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
import backfill_plantel_nums as backfill
from clubes_map import lookup

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

        # Backfill: FotMob a veces no da el dorsal → lo completamos con api-sports
        # ANTES de escribir. Los que igual quedan sin número se conservan en blanco.
        filled = []
        try:
            filled = backfill.fill_blanks(lookup(slug)['apisports'], players)
        except Exception as e:
            print(f'    (backfill api-sports falló para {slug}: {e})')

        sin_num = [p['name'] for p in players if not str(p.get('num') or '').strip()]
        total_fuera += len(sin_num)

        nota = (f'  (+{len(filled)} de api-sports)' if filled else '')
        if sin_num:
            nota += f'  ({len(sin_num)} en blanco: {", ".join(sin_num[:3])}{"…" if len(sin_num) > 3 else ""})'
        prefix = '[dry] ' if dry else '      '
        print(f'{prefix}{slug:26s} {len(players):2d} jugadores{nota}')

        if not dry:
            (PLANTELES / f'{slug}.json').write_text(
                json.dumps(players, ensure_ascii=False, indent=2), encoding='utf-8')
            escritos += 1
        time.sleep(0.6)  # cortesía con FotMob

    if dry:
        print(f'\n[dry-run] no se escribió nada. Total sin número tras backfill: {total_fuera}')
    else:
        print(f'\n{escritos} planteles escritos. Sin número (en blanco) tras backfill: {total_fuera}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
