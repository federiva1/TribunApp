"""
fetch_mundial_estado.py
Genera/actualiza data/estado_mundial.json para las 48 selecciones
leyendo data/fixtures/mundial.json.

Para cada equipo determina el partido activo/próximo:
 - Si hay partido EN CURSO → puntajesOpen según update_estado (no se toca aquí)
 - Si hay partido TERMINADO reciente (≤ 48h) → puntajesOpen conservado
 - Si no hay partido aún jugado → puntajesOpen: false, rival y match_date del próximo

Este script NO cambia puntajesOpen de entradas ya existentes con puntajesOpen:true.
Solo agrega entradas faltantes o actualiza rival/match_date cuando cambia el partido.

Uso:
    python scripts/fetch_mundial_estado.py
    python scripts/fetch_mundial_estado.py --force   # sobreescribe puntajesOpen también
"""
import argparse, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT    = Path(__file__).parent.parent
FIX_F   = ROOT / 'data' / 'fixtures' / 'mundial.json'
EST_F   = ROOT / 'data' / 'estado_mundial.json'

LIVE_STATUS = {'1H','HT','2H','ET','BT','P','SUSP'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true',
                        help='Sobreescribir puntajesOpen aunque ya esté true')
    args = parser.parse_args()

    fixtures = json.loads(FIX_F.read_text(encoding='utf-8'))
    estado   = json.loads(EST_F.read_text(encoding='utf-8')) if EST_F.exists() else {}

    now = datetime.now(timezone.utc)

    # Agrupar partidos reales (no amistosos) por slug de equipo
    # Para cada equipo: lista de partidos ordenados por fecha
    por_equipo: dict[str, list] = {}
    for p in fixtures:
        if p.get('round') == 'amistoso':
            continue
        home_slug = p['home'].get('slug') or ''
        away_slug = p['away'].get('slug') or ''
        if not home_slug or not away_slug:
            continue
        for slug, rival_slug in [(home_slug, away_slug), (away_slug, home_slug)]:
            por_equipo.setdefault(slug, []).append({
                'rival':    rival_slug,
                'date':     p['status']['utcTime'][:10],
                'finished': p['status'].get('finished', False),
                'started':  p['status'].get('started', False),
                'short':    p['status'].get('short', 'NS'),
                'utcTime':  p['status']['utcTime'],
            })

    # Ordenar por fecha
    for slug in por_equipo:
        por_equipo[slug].sort(key=lambda x: x['utcTime'])

    nuevos = 0
    actualizados = 0

    for slug, partidos in sorted(por_equipo.items()):
        # Buscar partido activo: en curso > más reciente terminado > próximo no jugado
        en_curso  = next((p for p in partidos if p['short'] in LIVE_STATUS), None)
        terminado = next((p for p in reversed(partidos) if p['finished']), None)
        proximo   = next((p for p in partidos if not p['started'] and not p['finished']), None)

        # Partido relevante: en curso primero, luego el más reciente terminado (≤48h), luego próximo
        activo = None
        if en_curso:
            activo = en_curso
        elif terminado:
            try:
                match_dt = datetime.fromisoformat(terminado['utcTime'].replace('Z','+00:00'))
                if now - match_dt <= timedelta(hours=48):
                    activo = terminado
            except Exception:
                activo = terminado
        if not activo and proximo:
            activo = proximo
        if not activo:
            activo = partidos[-1]  # último de todos como fallback

        rival      = activo['rival']
        match_date = activo['date']
        is_live    = activo['short'] in LIVE_STATUS
        is_fin     = activo['finished']

        entrada_actual = estado.get(slug, {})
        puntajes_open  = entrada_actual.get('puntajesOpen', False)

        # Respetar puntajesOpen existente salvo --force o que haya cambiado el partido
        if args.force:
            puntajes_open = is_live or is_fin

        nueva_entrada = {
            'puntajesOpen': puntajes_open,
            'rival':        rival,
            'match_date':   match_date,
        }

        if slug not in estado:
            nuevos += 1
        elif estado[slug] != nueva_entrada:
            actualizados += 1

        estado[slug] = nueva_entrada

    EST_F.write_text(
        json.dumps(estado, indent=2, ensure_ascii=False, sort_keys=True),
        encoding='utf-8'
    )

    total = len(por_equipo)
    print(f'estado_mundial.json actualizado — {total} equipos ({nuevos} nuevos, {actualizados} actualizados)')
    print(f'  Equipos con puntajesOpen=true: {sum(1 for v in estado.values() if v.get("puntajesOpen"))}')

if __name__ == '__main__':
    main()
