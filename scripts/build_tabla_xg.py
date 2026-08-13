"""Genera data/tabla_xg.json — la "tabla moral" del Clausura por zona.

Resultado moral de cada partido = parte entera del xG de cada equipo
(0.98 vs 0.57 → 0-0 empate; 0.98 vs 1.02 → 0-1). El xG sale de los
data/partidos/{id}.json que el pipeline ya genera (top_stats, label "xG").

Sin llamadas a APIs: lee solo archivos locales, así que puede correr en
cualquier workflow después de fetch_liga_partidos. Idempotente.

Uso:
    python scripts/build_tabla_xg.py
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTIDOS = ROOT / 'data' / 'partidos'
OUT = ROOT / 'data' / 'tabla_xg.json'

sys.path.insert(0, str(ROOT / 'scripts'))
from clubes_map import CLUBES  # noqa: E402

# Zonas fijas de la temporada (mismas listas que index.html).
ZONA_A = ['estudiantes', 'bocajuniors', 'velezsarsfield', 'talleres', 'independiente',
          'lanus', 'sanlorenzo', 'union', 'instituto', 'defensayjusticia',
          'gimnasiamendoza', 'clubatleticoplatense', 'centralcordobadesantiago',
          'newellsoldboys', 'deportivoriestra']
ZONA_B = ['independienterivadavia', 'riverplate', 'argentinosjuniors', 'rosariocentral',
          'belgrano', 'gimnasialp', 'huracan', 'racingclub', 'barracascentral',
          'tigre', 'sarmiento', 'banfield', 'atleticotucuman', 'aldosivi',
          'estudiantesderiocuarto']


def main() -> int:
    tabla = {s: dict(pj=0, g=0, e=0, p=0, gf=0, gc=0, pts=0, xgf=0.0, xgc=0.0)
             for s in ZONA_A + ZONA_B}
    fechas = set()
    saltados = []

    for f in sorted(PARTIDOS.glob('*.json')):
        if f.stem in ('index', 'standings'):
            continue
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            continue
        p = d.get('partido') or {}
        if 'clausura' not in (p.get('competicion') or '').lower():
            continue
        xg = next((s for s in d.get('top_stats', [])
                   if (s.get('label') or '').lower() == 'xg'), None)
        if not xg:
            saltados.append(f.stem)
            continue
        try:
            xl = float(xg['local_val'] if xg.get('local_val') is not None else xg['local'])
            xv = float(xg['visitante_val'] if xg.get('visitante_val') is not None else xg['visitante'])
        except (TypeError, ValueError):
            saltados.append(f.stem)
            continue
        gl, gv = math.floor(xl), math.floor(xv)
        if p.get('fecha_num'):
            fechas.add(p['fecha_num'])
        for slug, gf, gc, xf, xc in ((p.get('local'), gl, gv, xl, xv),
                                     (p.get('visitante'), gv, gl, xv, xl)):
            t = tabla.get(slug)
            if t is None:      # slug fuera de las zonas (no debería pasar en liga)
                continue
            t['pj'] += 1
            t['gf'] += gf
            t['gc'] += gc
            t['xgf'] += xf
            t['xgc'] += xc
            if gf > gc:
                t['g'] += 1
                t['pts'] += 3
            elif gf == gc:
                t['e'] += 1
                t['pts'] += 1
            else:
                t['p'] += 1

    def fila(slug):
        t = tabla[slug]
        return {
            'slug': slug,
            'id': (CLUBES.get(slug) or {}).get('apisports'),
            **{k: t[k] for k in ('pj', 'g', 'e', 'p', 'gf', 'gc', 'pts')},
            'dif': t['gf'] - t['gc'],
            'xgf': round(t['xgf'], 2),
            'xgc': round(t['xgc'], 2),
        }

    def zona(slugs):
        # pts → dif moral → GF moral → dif de xG crudo (desempate fino)
        return sorted((fila(s) for s in slugs),
                      key=lambda r: (-r['pts'], -r['dif'], -r['gf'],
                                     -(r['xgf'] - r['xgc'])))

    out = {
        'torneo': 'Clausura 2026',
        'ultima_fecha': max(fechas) if fechas else None,
        'zonaA': zona(ZONA_A),
        'zonaB': zona(ZONA_B),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    pjs = sorted({t['pj'] for t in tabla.values()})
    print(f'Guardado {OUT.name}: hasta la fecha {out["ultima_fecha"]}, PJ={pjs}'
          + (f' · sin xG: {saltados}' if saltados else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
