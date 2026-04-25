"""
Cierra los puntajes de los clubes cuyo partido terminó hace más de 48 horas.
Lee data/estado.json, setea puntajesOpen: false para esos clubes.

Uso:
    python scripts/close_puntajes.py
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ESTADO_PATH = Path(__file__).parent.parent / 'data' / 'estado.json'
CUTOFF_HOURS = 48


def main():
    with open(ESTADO_PATH, encoding='utf-8') as f:
        estado = json.load(f)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=CUTOFF_HOURS)
    changed = False

    for slug, entry in estado.items():
        if not entry.get('puntajesOpen'):
            continue
        match_date_str = entry.get('matchDate', '')
        if not match_date_str:
            continue
        try:
            # matchDate es YYYY-MM-DD; asumimos que el partido fue a mediodia UTC
            match_dt = datetime.fromisoformat(match_date_str).replace(
                hour=12, tzinfo=timezone.utc
            )
        except ValueError:
            continue
        if match_dt < cutoff:
            entry['puntajesOpen'] = False
            changed = True
            print(f'{slug}: cerrado (matchDate={match_date_str})')

    if changed:
        with open(ESTADO_PATH, 'w', encoding='utf-8') as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        print('Estado actualizado.')
    else:
        print('Sin cambios.')


if __name__ == '__main__':
    main()
