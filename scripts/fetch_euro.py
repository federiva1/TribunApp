"""Datos de EUROTRIBUNAPP (prototipo, rama eurotribunapp): las 5 grandes ligas de Europa desde FotMob.

Por cada liga baja la página de la liga (mismo __NEXT_DATA__ que el resto de los scrapers,
`scrape_fotmob_mundial._next_data_http`) y escribe:

    data/euro/{liga_id}.json   nombre, país, temporada, tabla, última fecha jugada y próxima fecha
    data/euro/clubes/{id}.json un archivo por club de la tabla: posición, próximo partido,
                               últimos 5 resultados y plantel por puesto + DT
    data/euro/fixture/{liga_id}.json  el fixture completo de la liga (todas las rondas) para euro-fixture.html
    data/euro/index.json       resumen de las ligas (líder, fecha) + partidos destacados

"Última fecha" = la ronda más reciente con TODOS sus partidos terminados; "próxima fecha" =
los partidos no jugados de la ronda siguiente (utcTime en UTC, el front los pasa a hora AR).
Un club que falla no corta el resto: queda sin archivo y la página lo muestra sin plantel.

    python scripts/fetch_euro.py              # las 5 ligas + la Champions + todos los clubes (~115 pedidos)
    python scripts/fetch_euro.py --sin-clubes # solo ligas, fixtures e index
    python scripts/fetch_euro.py --faltantes  # ligas e index + solo los clubes que todavía no tienen archivo
    python scripts/fetch_euro.py 47           # una liga (y sus clubes)

La Champions League (id 42) va primera: su tabla es la fase de liga (36 equipos) y sus clubes que no
juegan en las 5 ligas (Benfica, PSV, etc.) quedan con la Champions como "liga".
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scrape_fotmob_mundial as sfm

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'euro'

LIGAS = [
    {'id': 42, 'slug': 'champions-league', 'nombre': 'Champions League', 'pais': 'Europa', 'color': '#1d4ed8'},
    {'id': 47, 'slug': 'premier-league', 'nombre': 'Premier League', 'pais': 'Inglaterra', 'color': '#7b2cbf'},
    {'id': 87, 'slug': 'laliga', 'nombre': 'LaLiga', 'pais': 'España', 'color': '#ff4b44'},
    {'id': 55, 'slug': 'serie-a', 'nombre': 'Serie A', 'pais': 'Italia', 'color': '#1e88e5'},
    {'id': 54, 'slug': '1-bundesliga', 'nombre': 'Bundesliga', 'pais': 'Alemania', 'color': '#e53935'},
    {'id': 53, 'slug': 'ligue-1', 'nombre': 'Ligue 1', 'pais': 'Francia', 'color': '#1565c0'},
]
# Rondas que no son un número (eliminatorias de la Champions), en orden cronológico
RONDAS_KO = {'1/32': 100, '1/16': 101, 'playoff': 101, '1/8': 102, '1/4': 103, '1/2': 104, 'final': 105}
PUESTOS = ('keepers', 'defenders', 'midfielders', 'attackers')


def _goles(score):
    try:
        a, b = (int(x) for x in (score or '').split('-'))
        return a, b
    except ValueError:
        return None, None


def _partido(m):
    st = m.get('status') or {}
    gl, gv = _goles(st.get('scoreStr'))
    return {
        'id': str(m.get('id')),
        'local': {'id': int(m['home']['id']), 'nombre': m['home'].get('shortName') or m['home']['name']},
        'visitante': {'id': int(m['away']['id']), 'nombre': m['away'].get('shortName') or m['away']['name']},
        'utcTime': st.get('utcTime'),
        'terminado': bool(st.get('finished')),
        'cancelado': bool(st.get('cancelled')),
        'goles_local': gl, 'goles_visitante': gv,
    }


def _tabla(pp):
    tb = (pp.get('table') or [{}])[0].get('data') or {}
    filas = (tb.get('table') or {}).get('all')
    if not filas and tb.get('tables'):                 # ligas con grupos: primera tabla
        filas = (tb['tables'][0].get('table') or {}).get('all')
    out = []
    for r in filas or []:
        out.append({
            'pos': r.get('idx'), 'id': r['id'], 'nombre': r['name'], 'corto': r.get('shortName') or r['name'],
            'pj': r.get('played'), 'g': r.get('wins'), 'e': r.get('draws'), 'p': r.get('losses'),
            'goles': r.get('scoresStr'), 'dg': r.get('goalConDiff'), 'pts': r.get('pts'),
            'color': r.get('qualColor'),
        })
    return out


def _leyenda(pp):
    """Colores de clasificación (Champions, Europa League, descenso...) que trae FotMob."""
    tb = (pp.get('table') or [{}])[0].get('data') or {}
    leg = tb.get('legend') or []
    return [{'titulo': x.get('title'), 'color': x.get('color')} for x in leg if x.get('color')]


def _orden_ronda(r):
    return int(r) if r.isdigit() else RONDAS_KO.get(r.lower(), 999)


def _fechas(pp):
    """(última, próxima, todas): rondas con todos sus partidos, ordenadas cronológicamente."""
    partidos = (pp.get('fixtures') or {}).get('allMatches') or []
    rondas = {}
    for m in partidos:
        rondas.setdefault(str(m.get('round')), []).append(m)
    orden = sorted(rondas, key=_orden_ronda)
    terminada = lambda r: all((x.get('status') or {}).get('finished') or (x.get('status') or {}).get('cancelled')
                              for x in rondas[r])
    # Última = la ronda MÁS ALTA con todo jugado (un partido postergado de una fecha vieja no
    # la "reabre"); próxima = la primera ronda posterior con partidos sin jugar.
    hechas = [r for r in orden if terminada(r)]
    ultima = hechas[-1] if hechas else None
    desde = orden.index(ultima) + 1 if ultima else 0
    proxima = next((r for r in orden[desde:] if not terminada(r)), None)
    ordena = lambda r: sorted(rondas[r], key=lambda x: (x.get('status') or {}).get('utcTime') or '')
    arma = lambda r: ({'ronda': r, 'partidos': [_partido(x) for x in ordena(r)]} if r else None)
    todas = [{'ronda': r, 'partidos': [_partido(x) for x in ordena(r)]} for r in orden]
    return arma(ultima), arma(proxima), todas


def liga(meta):
    d = sfm._next_data_http(f"https://www.fotmob.com/leagues/{meta['id']}/overview/{meta['slug']}")
    if not d:
        raise RuntimeError('FotMob no respondió')
    pp = d['props']['pageProps']
    det = pp.get('details') or {}
    ultima, proxima, todas = _fechas(pp)
    L = {
        'id': meta['id'], 'nombre': meta['nombre'], 'pais': meta['pais'], 'color': meta['color'],
        'temporada': det.get('selectedSeason') or det.get('latestSeason'),
        'tabla': _tabla(pp), 'leyenda': _leyenda(pp),
        'ultima_fecha': ultima, 'proxima_fecha': proxima,
    }
    F = {'id': meta['id'], 'nombre': meta['nombre'], 'temporada': L['temporada'],
         'ultima': ultima and ultima['ronda'], 'proxima': proxima and proxima['ronda'], 'rondas': todas}
    return L, F


def club(cid, liga_meta, fila):
    d = sfm._next_data_http(f'https://www.fotmob.com/teams/{cid}/squad/x')
    if not d:
        raise RuntimeError('FotMob no respondió')
    t = d['props']['pageProps']['fallback'][f'team-{cid}']
    ov = t.get('overview') or {}
    det = t.get('details') or {}
    plantel = {k: [] for k in PUESTOS}
    dt = None
    for g in (t.get('squad') or {}).get('squad') or []:
        tit = g.get('title')
        for m in g.get('members') or []:
            if tit == 'coach':
                dt = m.get('name')
            elif tit in plantel:
                plantel[tit].append({'num': m.get('shirtNumber'), 'nombre': m.get('name'),
                                     'puesto': (m.get('positionIdsDesc') or '').split(',')[0] or None})
    for k in plantel:
        plantel[k].sort(key=lambda j: (j['num'] is None, j['num'] or 0))
    nm = ov.get('nextMatch') or None
    proximo = None
    if nm:
        proximo = {'local': {'id': nm['home']['id'], 'nombre': nm['home']['name']},
                   'visitante': {'id': nm['away']['id'], 'nombre': nm['away']['name']},
                   'utcTime': (nm.get('status') or {}).get('utcTime'),
                   'torneo': (nm.get('tournament') or {}).get('name')}
    forma = []
    for f in (ov.get('teamForm') or [])[-5:]:
        tt = f.get('tooltipText') or {}
        local = tt.get('homeTeamId') == cid
        forma.append({'r': f.get('resultString'), 'marcador': f.get('score'),
                      'rival': tt.get('awayTeam') if local else tt.get('homeTeam'),
                      'rival_id': tt.get('awayTeamId') if local else tt.get('homeTeamId'),
                      'local': local, 'utcTime': (f.get('date') or {}).get('utcTime')})
    colores = ov.get('teamColors') or {}
    return {
        'id': cid, 'nombre': det.get('name') or fila['nombre'], 'corto': det.get('shortName') or fila['corto'],
        'liga': {'id': liga_meta['id'], 'nombre': liga_meta['nombre']},
        'pos': fila['pos'], 'pts': fila['pts'], 'pj': fila['pj'],
        'color': colores.get('lightMode') or colores.get('darkMode'),
        'dt': dt, 'proximo': proximo, 'forma': forma, 'plantel': plantel,
    }


def destacados(ligas):
    """Uno por liga: el partido de la próxima fecha entre los equipos mejor ubicados (menor suma de posiciones)."""
    cand = []
    for L in ligas:
        pos = {f['id']: f['pos'] for f in L['tabla']}
        for p in (L.get('proxima_fecha') or {}).get('partidos') or []:
            a, b = pos.get(p['local']['id'], 99), pos.get(p['visitante']['id'], 99)
            cand.append((a + b, L['id'], p))
    cand.sort(key=lambda x: x[0])
    out, usadas = [], set()
    for _, lid, p in cand:                    # el mejor de cada liga, para que haya variedad
        if lid in usadas:
            continue
        usadas.add(lid)
        out.append(dict(p, liga=lid))
    return sorted(out, key=lambda p: p['utcTime'] or '')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    sin_clubes = '--sin-clubes' in sys.argv
    metas = [m for m in LIGAS if not args or str(m['id']) in args]
    faltantes = '--faltantes' in sys.argv
    (OUT / 'clubes').mkdir(parents=True, exist_ok=True)
    (OUT / 'fixture').mkdir(parents=True, exist_ok=True)
    ok = err = 0
    tablas = {}
    for meta in metas:
        L, F = liga(meta)
        tablas[meta['id']] = L
        (OUT / f"{meta['id']}.json").write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding='utf-8')
        (OUT / 'fixture' / f"{meta['id']}.json").write_text(json.dumps(F, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        u, p = L['ultima_fecha'], L['proxima_fecha']
        print(f"{meta['nombre']:16s} {len(L['tabla'])} equipos · última fecha {u and u['ronda']} · próxima {p and p['ronda']}")
    if not sin_clubes:
        # Las ligas primero y la Champions al final: un club que juega las dos queda con su liga local
        hechos = set()
        for meta in sorted(metas, key=lambda m: m['id'] == 42):
            for fila in tablas[meta['id']]['tabla']:
                f = OUT / 'clubes' / f"{fila['id']}.json"
                if fila['id'] in hechos or (faltantes and f.exists()):
                    continue
                hechos.add(fila['id'])
                try:
                    c = club(fila['id'], meta, fila)
                    f.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding='utf-8')
                    ok += 1
                except Exception as e:
                    err += 1
                    print(f"   ! {fila['nombre']} ({fila['id']}): {e}")
                time.sleep(0.6)
    ligas = []
    for meta in LIGAS:
        f = OUT / f"{meta['id']}.json"
        if f.exists():
            ligas.append(json.loads(f.read_text(encoding='utf-8')))
    idx = {
        'ligas': [{'id': L['id'], 'nombre': L['nombre'], 'pais': L['pais'], 'color': L['color'],
                   'temporada': L['temporada'],
                   'fecha': (L.get('proxima_fecha') or L.get('ultima_fecha') or {}).get('ronda'),
                   'lider': L['tabla'][0] if L['tabla'] else None} for L in ligas],
        'destacados': destacados(ligas),
        'actualizado': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    (OUT / 'index.json').write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding='utf-8')
    if not sin_clubes:
        print(f'Clubes: {ok} ok, {err} con error')


if __name__ == '__main__':
    main()
