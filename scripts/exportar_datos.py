#!/usr/bin/env python3
"""Exporta a CSV todo lo que TribunApp tiene de partidos, equipos y jugadores.

Pensado para llevarse los datos a otra herramienta de analisis: una fila por
partido, una por jugador-partido, una por gol y una por jugador de plantel, mas
un README con el esquema y las trampas conocidas de los datos.

    python scripts/exportar_datos.py                  # -> export/
    python scripts/exportar_datos.py --out C:\\ruta    # otra carpeta
    python scripts/exportar_datos.py --zip            # ademas arma el .zip
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass

PARTIDOS = ROOT / 'data' / 'partidos'
PLANTELES = ROOT / 'data' / 'planteles'
FIXTURES = ROOT / 'data' / 'fixtures'

# Etiquetas de top_stats -> nombre de columna. El orden fija las columnas del CSV.
TOP_STATS = {
    'Posesion': 'posesion', 'xG': 'xg', 'Tiros totales': 'tiros',
    'Tiros al arco': 'tiros_al_arco', 'Toques en area rival': 'toques_area_rival',
    'Corners': 'corners', 'Faltas': 'faltas',
    'Tarjetas amarillas': 'amarillas', 'Tarjetas rojas': 'rojas',
    'Pases precisos': 'pases_precisos',
}
# Bloques de stats individuales. Se aplanan como bloque_campo.
BLOQUES = {
    'top': ['tiros_totales', 'disparos_puerta', 'oport_creadas', 'grandes_oport',
            'acc_defensivas', 'pases_precisos'],
    'ataque': ['toques', 'toques_area', 'regates', 'pases_ultimo_tercio',
               'tiros_largos', 'perdida_balon'],
    'defensa': ['acc_defensivas', 'entradas', 'interceptaciones', 'recuperaciones',
                'despejes', 'bloqueos', 'regateado'],
    'duelos': ['ganados', 'perdidos', 'terrestres', 'aereos', 'faltas', 'faltas_recibidas'],
    'portero_stats': ['paradas', 'goles_contra', 'goles_evitados'],
}


def cargar_partidos():
    for f in sorted(PARTIDOS.glob('*.json')):
        if f.name in ('index.json', 'standings.json'):
            continue
        try:
            yield f.stem, json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            print(f'  (ilegible {f.name}: {e})')


def escribir(path, columnas, filas):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=columnas, extrasaction='ignore')
        w.writeheader()
        w.writerows(filas)
    print(f'  {path.name:<22} {len(filas):>6} filas')


def exportar(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    partidos, jugadores, goles = [], [], []

    for mid, d in cargar_partidos():
        p = d.get('partido') or {}
        base = {
            'partido_id': mid, 'fecha': p.get('fecha'), 'fecha_num': p.get('fecha_num'),
            'competicion': p.get('competicion'), 'ronda': p.get('ronda'),
            'estadio': p.get('estadio'), 'api_id': p.get('api_id'),
            'local': p.get('local'), 'visitante': p.get('visitante'),
            'goles_local': p.get('goles_local'), 'goles_visitante': p.get('goles_visitante'),
            'penales': json.dumps(p.get('penales'), ensure_ascii=False) if p.get('penales') else '',
            'formacion_local': (p.get('formacion') or {}).get(p.get('local'), ''),
            'formacion_visitante': (p.get('formacion') or {}).get(p.get('visitante'), ''),
        }
        for s in d.get('top_stats') or []:
            col = TOP_STATS.get(s.get('label'))
            if col:
                base[f'{col}_local'] = s.get('local_val', s.get('local'))
                base[f'{col}_visitante'] = s.get('visitante_val', s.get('visitante'))
        partidos.append(base)

        for lado in ('local', 'visitante'):
            slug = p.get(lado)
            for g in (p.get('goles_detalle') or {}).get(lado, []) or []:
                if not isinstance(g, dict):
                    g = {'jugador': g}
                # 'en_contra' marca el gol en contra: suma al marcador de este lado
                # pero NO al contador de goles del jugador, que es del otro equipo.
                goles.append({'partido_id': mid, 'fecha': p.get('fecha'), 'club': slug,
                              'condicion': lado, 'minuto': g.get('min'),
                              'jugador': g.get('jugador'), 'asistencia': g.get('asist') or '',
                              'en_contra': bool(g.get('en_contra'))})

        for slug, js in (d.get('jugadores') or {}).items():
            rival = p.get('visitante') if slug == p.get('local') else p.get('local')
            for j in js:
                fila = {
                    'partido_id': mid, 'fecha': p.get('fecha'), 'fecha_num': p.get('fecha_num'),
                    'competicion': p.get('competicion'), 'club': slug, 'rival': rival,
                    'condicion': 'local' if slug == p.get('local') else 'visitante',
                    'jugador': j.get('nombre'), 'jugador_id': j.get('id'),
                    'num': j.get('num'), 'tipo': j.get('tipo'),
                    'portero': j.get('portero'), 'mvp': j.get('mvp'),
                    'min': j.get('min'), 'goles': j.get('goles'), 'asist': j.get('asist'),
                    'amarilla': j.get('amarilla'), 'roja': j.get('roja'),
                    'pos_x': (j.get('pos') or {}).get('x'), 'pos_y': (j.get('pos') or {}).get('y'),
                }
                for bloque, campos in BLOQUES.items():
                    val = j.get(bloque) or {}
                    pref = 'gk' if bloque == 'portero_stats' else bloque
                    for c in campos:
                        fila[f'{pref}_{c}'] = val.get(c) if isinstance(val, dict) else None
                jugadores.append(fila)

    col_part = (['partido_id', 'fecha', 'fecha_num', 'competicion', 'ronda', 'estadio', 'api_id',
                 'local', 'visitante', 'goles_local', 'goles_visitante', 'penales',
                 'formacion_local', 'formacion_visitante']
                + [f'{c}_{l}' for c in TOP_STATS.values() for l in ('local', 'visitante')])
    col_jug = (['partido_id', 'fecha', 'fecha_num', 'competicion', 'club', 'rival', 'condicion',
                'jugador', 'jugador_id', 'num', 'tipo', 'portero', 'mvp', 'min', 'goles', 'asist',
                'amarilla', 'roja', 'pos_x', 'pos_y']
               + [f"{'gk' if b == 'portero_stats' else b}_{c}" for b, cs in BLOQUES.items() for c in cs])

    partidos.sort(key=lambda r: (r['fecha'] or '', r['partido_id']))
    jugadores.sort(key=lambda r: (r['fecha'] or '', r['partido_id'], r['club'], r['jugador'] or ''))
    goles.sort(key=lambda r: (r['fecha'] or '', r['partido_id']))
    escribir(out / 'partidos.csv', col_part, partidos)
    escribir(out / 'jugadores.csv', col_jug, jugadores)
    escribir(out / 'goles.csv', ['partido_id', 'fecha', 'club', 'condicion', 'minuto',
                                 'jugador', 'asistencia', 'en_contra'], goles)

    # planteles
    pl = []
    for f in sorted(PLANTELES.glob('*.json')):
        for j in json.loads(f.read_text(encoding='utf-8')):
            pl.append({'club': f.stem, 'num': j.get('num'), 'jugador': j.get('name'),
                       'fotmob_id': j.get('fid'), 'nacionalidad': j.get('nationality'),
                       'posicion': j.get('position')})
    escribir(out / 'planteles.csv', ['club', 'num', 'jugador', 'fotmob_id', 'nacionalidad', 'posicion'], pl)

    # fixture completo (incluye los no jugados)
    fx = []
    f = FIXTURES / 'liga.json'
    if f.is_file():
        for m in json.loads(f.read_text(encoding='utf-8')):
            st = m.get('status') or {}
            fx.append({'api_id': m.get('api_id'), 'fecha_num': m.get('fecha'),
                       'utc': st.get('utcTime'), 'local': (m.get('home') or {}).get('slug'),
                       'visitante': (m.get('away') or {}).get('slug'),
                       'goles_local': m.get('home_score'), 'goles_visitante': m.get('away_score'),
                       'estado': st.get('short'), 'finalizado': st.get('finished'),
                       'ganador': m.get('winner')})
        fx.sort(key=lambda r: r['utc'] or '')
        escribir(out / 'fixture.csv', ['api_id', 'fecha_num', 'utc', 'local', 'visitante',
                                       'goles_local', 'goles_visitante', 'estado', 'finalizado', 'ganador'], fx)
    return partidos, jugadores, goles, pl, fx


def readme(out: Path, partidos, jugadores, goles, pl, fx):
    fechas = [r['fecha'] for r in partidos if r['fecha']]
    txt = f"""# TribunApp — export de datos

Snapshot generado con `scripts/exportar_datos.py`.
Cubre **{len(partidos)} partidos** ({min(fechas)} a {max(fechas)}), **{len(jugadores)} filas
jugador-partido**, {len(goles)} goles y {len(pl)} jugadores de plantel.

## Archivos

| archivo | grano | filas |
|---|---|---|
| `partidos.csv` | un partido | {len(partidos)} |
| `jugadores.csv` | un jugador en un partido | {len(jugadores)} |
| `goles.csv` | un gol | {len(goles)} |
| `planteles.csv` | un jugador de un plantel | {len(pl)} |
| `fixture.csv` | un partido del torneo, jugado o no | {len(fx)} |

Se cruzan por `partido_id` (partidos/jugadores/goles), por `club` + `jugador`
(planteles) y por `api_id` (fixture ↔ partidos).

## Origen de los datos

Dos fuentes, y **conviene no mezclarlas en un mismo numero**:

- **api-sports** aporta el resultado, el equipo que jugo, los goles y los minutos.
- **FotMob** aporta las estadisticas individuales (los bloques `top_`, `ataque_`,
  `defensa_`, `duelos_`, `gk_`) y las de equipo de `partidos.csv`.

## Trampas conocidas (importante)

1. **`fecha` vs `fecha_num`.** `fecha` es el dia (`YYYY-MM-DD`); `fecha_num` es el
   numero de jornada. **El numero no es cronologico**: una postergacion hace que la
   fecha 2 se juegue despues de la 3. Para ordenar en el tiempo usar siempre `fecha`.
2. **Cobertura de las stats individuales: ~89%.** Los partidos mas viejos y algunos
   de copa no tienen los bloques de FotMob; ahi las columnas van vacias. Vacio
   significa *no hay dato*, no cero.
3. **`num` puede repetirse dentro de un club** (dos jugadores con el mismo dorsal es
   real) y puede estar vacio en juveniles recien subidos. Para identificar a un
   jugador conviene `jugador_id` (id de FotMob) antes que el dorsal o el nombre.
4. **El nombre no es una clave.** Hay homonimos dentro del mismo plantel (tres Perez
   en Racing, dos Fernandez en Central). Cruzar por apellido solo produce errores.
5. **`xG` falta en 6 partidos** y en varios se reconstruye sumando el xG individual,
   porque api-sports no lo da de forma consistente para la liga argentina.
6. **`competicion`** mezcla Clausura 2026 con Copa Libertadores y Sudamericana.
   Filtrar si se quiere analizar solo el torneo local.
7. **`tipo`** es `titular`, `suplente` o `dt`. Las filas con `tipo = dt` son el
   entrenador: no tienen stats y hay que excluirlas de cualquier promedio.
8. **Solo entran los suplentes que ingresaron**; el resto del banco no se registra.
9. **`pos_x` / `pos_y`** son la posicion en la cancha normalizada 0-100 (solo
   titulares, ~64% de las filas).

## Como contar goles

Usar **`goles.csv`**, que es la fuente completa: 260 goles, todos con minuto.
La columna `goles` de `jugadores.csv` da 251 y **no cuadra a proposito**:

- **8 goles en contra** (`en_contra = True`) suman al marcador del rival pero no
  al contador del que la mando adentro. Correcto, pero hay que tenerlo en cuenta.
- **1 gol sin acreditar**: el de Breno Bidon en `corinthians-rosariocentral`
  (Sudamericana, 21/8). A los equipos extranjeros de copa no se les sincronizan
  los contadores individuales, asi que el gol figura en `goles.csv` y en el
  marcador, pero no en la fila del jugador.

251 + 8 + 1 = 260. Para goleadores, agrupar `goles.csv` por `jugador` filtrando
`en_contra = False`.

## Lo que NO esta aca

Los votos de la gente (formaciones y puntajes) viven en Supabase, no en estos
archivos. Se pueden exportar aparte si hacen falta.
"""
    (out / 'README.md').write_text(txt, encoding='utf-8')
    print(f'  {"README.md":<22} {len(txt.splitlines()):>6} lineas')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'export'))
    ap.add_argument('--zip', action='store_true')
    a = ap.parse_args()
    out = Path(a.out)
    print(f'Exportando a {out}')
    datos = exportar(out)
    readme(out, *datos)
    if a.zip:
        z = out.parent / f'{out.name}.zip'
        with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out.iterdir()):
                zf.write(f, f.name)
        print(f'\nzip: {z} ({z.stat().st_size/1e6:.1f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
