"""Datos de EUROTRIBUNAPP (prototipo, rama eurotribunapp): las 5 grandes ligas de Europa desde FotMob.

Por cada liga baja la página de la liga (mismo __NEXT_DATA__ que el resto de los scrapers,
`scrape_fotmob_mundial._next_data_http`) y escribe:

    data/euro/{liga_id}.json   nombre, país, temporada, tabla, última fecha jugada y próxima fecha
    data/euro/clubes/{id}.json un archivo por club de la tabla: posición, próximo partido,
                               últimos 5 resultados y plantel por puesto + DT
    data/euro/fixture/{liga_id}.json  el fixture completo de la liga (todas las rondas) para euro-fixture.html
    data/euro/stats/{liga_id}.json    el detalle de los partidos de la ÚLTIMA fecha (stats de equipo, goles, mejor
                                      jugador, nota y stats de cada jugador) para euro-stats.html y euro-tribunapp.html
    data/euro/index.json       resumen de las ligas (líder, fecha) + partidos destacados

"Última fecha" = la ronda más reciente con TODOS sus partidos terminados; "próxima fecha" =
los partidos no jugados de la ronda siguiente (utcTime en UTC, el front los pasa a hora AR).
Un club que falla no corta el resto: queda sin archivo y la página lo muestra sin plantel.

    python scripts/fetch_euro.py              # las 5 ligas + la Champions + todos los clubes (~115 pedidos)
    python scripts/fetch_euro.py --sin-clubes # solo ligas, fixtures, stats e index
    python scripts/fetch_euro.py --sin-stats  # sin el detalle de los partidos de la última fecha (~70 pedidos)
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
    urls = {str(x['id']): x.get('pageUrl') for x in rondas[ultima]} if ultima else {}
    return arma(ultima), arma(proxima), todas, urls


def liga(meta):
    d = sfm._next_data_http(f"https://www.fotmob.com/leagues/{meta['id']}/overview/{meta['slug']}")
    if not d:
        raise RuntimeError('FotMob no respondió')
    pp = d['props']['pageProps']
    det = pp.get('details') or {}
    ultima, proxima, todas, urls = _fechas(pp)
    L = {
        'id': meta['id'], 'nombre': meta['nombre'], 'pais': meta['pais'], 'color': meta['color'],
        'temporada': det.get('selectedSeason') or det.get('latestSeason'),
        'tabla': _tabla(pp), 'leyenda': _leyenda(pp),
        'ultima_fecha': ultima, 'proxima_fecha': proxima,
    }
    F = {'id': meta['id'], 'nombre': meta['nombre'], 'temporada': L['temporada'],
         'ultima': ultima and ultima['ronda'], 'proxima': proxima and proxima['ronda'], 'rondas': todas}
    return L, F, urls


# ---------------------------------------------------------------- detalle de un partido (última fecha)
# Estadísticas de equipo que se guardan: (key de FotMob, clave nuestra, etiqueta)
STATS_EQUIPO = [
    ('BallPossesion', 'posesion', 'Posesión'), ('expected_goals', 'xg', 'xG'), ('total_shots', 'tiros', 'Tiros'),
    ('ShotsOnTarget', 'tiros_arco', 'Tiros al arco'), ('big_chance', 'grandes', 'Grandes ocasiones'),
    ('accurate_passes', 'pases', 'Pases acertados'), ('corners', 'corners', 'Córners'),
    ('fouls', 'faltas', 'Faltas'), ('yellow_cards', 'amarillas', 'Amarillas'), ('red_cards', 'rojas', 'Rojas'),
]


def _num(v):
    """'526 (88%)' -> 526 · '1.87' -> 1.87 · 58 -> 58."""
    if isinstance(v, (int, float)):
        return v
    try:
        return sfm.to_num(str(v).split('(')[0].strip())
    except Exception:
        return None


def _stats_equipo(c):
    por_key = {}
    for sec in ((c.get('stats') or {}).get('Periods') or {}).get('All', {}).get('stats') or []:
        for it in sec.get('stats') or []:
            st = it.get('stats') or []
            if it.get('key') and len(st) == 2 and st[0] is not None and it['key'] not in por_key:
                por_key[it['key']] = st
    out = []
    for key, k, label in STATS_EQUIPO:
        st = por_key.get(key)
        if not st:
            continue
        e = {'k': k, 'label': label, 'l': _num(st[0]), 'v': _num(st[1])}
        if k == 'pases':                                  # "526 (88%)": acertados y porcentaje
            pct = lambda t: sfm.to_int(str(t).split('(')[1].rstrip('%)')) if '(' in str(t) else None
            e['lp'], e['vp'] = pct(st[0]), pct(st[1])
        out.append(e)
    return out


def _jugadores(c, lado):
    """Titulares + suplentes que jugaron de un equipo (lineup de FotMob + playerStats por id)."""
    team = (c.get('lineup') or {}).get('homeTeam' if lado == 'local' else 'awayTeam') or {}
    ps = c.get('playerStats') or {}
    out = []
    for titular, grupo in ((True, team.get('starters') or []), (False, team.get('subs') or [])):
        for j in grupo:
            perf = j.get('performance') or {}
            flat = sfm.flatten_stats((ps.get(str(j.get('id'))) or {}).get('stats') or [])
            minutos = sfm.to_int(flat.get('Minutes played'))
            nota = perf.get('rating')
            if not titular and not minutos and nota is None:
                continue                                   # suplente que no entró
            out.append({
                'id': j.get('id'), 'nombre': j.get('name'), 'num': sfm.to_int(j.get('shirtNumber')), 'titular': titular,
                'min': minutos, 'nota': round(float(nota), 1) if nota is not None else None,
                'goles': sfm.to_int(flat.get('Goals')) or 0, 'asist': sfm.to_int(flat.get('Assists')) or 0,
                'tiros': sfm.to_int(flat.get('Total shots')), 'xg': sfm.to_num(flat.get('Expected goals (xG)')),
                'pases': sfm.to_int(flat.get('Accurate passes')),
            })
    return out, team.get('formation')


def _goles_partido(c):
    out = []
    for e in ((c.get('matchFacts') or {}).get('events') or {}).get('events') or []:
        if e.get('type') != 'Goal':
            continue
        sm = e.get('shotmapEvent') or {}
        asist = (e.get('assistStr') or '').replace('assist by ', '').strip() or None
        out.append({'min': e.get('time'), 'extra': e.get('overloadTime'), 'equipo': 'local' if e.get('isHome') else 'visitante',
                    'jugador': e.get('nameStr'), 'asist': asist,
                    'penal': sm.get('situation') == 'Penalty', 'autogol': bool(e.get('ownGoal') or sm.get('isOwnGoal'))})
    return out


def detalle(nd, p, ronda):
    c = nd['props']['pageProps']['content']
    jl, fl = _jugadores(c, 'local')
    jv, fv = _jugadores(c, 'visitante')
    mvp = (c.get('matchFacts') or {}).get('playerOfTheMatch') or None
    mvp_out = None
    if mvp:
        nombre = (mvp.get('name') or {})
        mvp_out = {'id': mvp.get('id'), 'nombre': nombre.get('fullName') if isinstance(nombre, dict) else nombre,
                   'equipo': 'local' if mvp.get('teamId') == p['local']['id'] else 'visitante',
                   'nota': _num((mvp.get('rating') or {}).get('num'))}
    return {
        'id': p['id'], 'ronda': ronda, 'utcTime': p['utcTime'], 'local': p['local'], 'visitante': p['visitante'],
        'goles_local': p['goles_local'], 'goles_visitante': p['goles_visitante'],
        'formacion': {'local': fl, 'visitante': fv},
        'stats': _stats_equipo(c), 'goles': _goles_partido(c), 'mvp': mvp_out,
        'jugadores': {'local': jl, 'visitante': jv},
    }


def stats_ultima_fecha(L, urls):
    """Detalle de cada partido terminado de la última fecha de la competición."""
    u = L.get('ultima_fecha')
    res = []
    for p in (u or {}).get('partidos') or []:
        if not p['terminado'] or not urls.get(p['id']):
            continue
        nd = sfm._next_data_http('https://www.fotmob.com' + urls[p['id']])
        if not nd:
            print(f"   ! partido {p['id']} ({p['local']['nombre']}-{p['visitante']['nombre']}): FotMob no respondió")
            continue
        try:
            res.append(detalle(nd, p, u['ronda']))
        except Exception as e:
            print(f"   ! partido {p['id']}: {e}")
        time.sleep(0.5)
    return {'id': L['id'], 'nombre': L['nombre'], 'ronda': u and u['ronda'], 'partidos': res}


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
                plantel[tit].append({'id': m.get('id'), 'num': m.get('shirtNumber'), 'nombre': m.get('name'),
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


def escudos(ids_clubes, ids_ligas):
    """Guarda los escudos y logos en escudos/euro/ (96 px máx.): se sirven desde el propio sitio y se pueden
    dibujar en un canvas (los de FotMob no traen CORS y lo "contaminan"). Solo baja los que faltan."""
    import io
    import urllib.request
    from PIL import Image
    dest = ROOT / 'escudos' / 'euro'
    dest.mkdir(parents=True, exist_ok=True)
    ok = fallan = 0
    pedidos = [(f'{i}.png', f'https://images.fotmob.com/image_resources/logo/teamlogo/{i}.png') for i in sorted(ids_clubes)]
    pedidos += [(f'liga-{i}.png', f'https://images.fotmob.com/image_resources/logo/leaguelogo/{i}.png') for i in sorted(ids_ligas)]
    for nombre, url in pedidos:
        f = dest / nombre
        if f.exists():
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': sfm.UA})
            im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert('RGBA')
            im.thumbnail((96, 96), Image.LANCZOS)
            im.save(f, 'PNG', optimize=True)
            ok += 1
        except Exception as e:
            fallan += 1
            print(f'   ! escudo {nombre}: {e}')
        time.sleep(0.15)
    print(f'Escudos: {ok} nuevos, {fallan} con error')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    sin_clubes = '--sin-clubes' in sys.argv
    metas = [m for m in LIGAS if not args or str(m['id']) in args]
    faltantes = '--faltantes' in sys.argv
    (OUT / 'clubes').mkdir(parents=True, exist_ok=True)
    (OUT / 'fixture').mkdir(parents=True, exist_ok=True)
    (OUT / 'stats').mkdir(parents=True, exist_ok=True)
    ok = err = 0
    tablas = {}
    for meta in metas:
        L, F, urls = liga(meta)
        tablas[meta['id']] = L
        if '--sin-stats' not in sys.argv:
            S = stats_ultima_fecha(L, urls)
            (OUT / 'stats' / f"{meta['id']}.json").write_text(json.dumps(S, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
            print(f"   detalle de {len(S['partidos'])} partidos de la fecha {S['ronda']}")
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
    if '--sin-escudos' not in sys.argv:
        ids = {f['id'] for L in ligas for f in L['tabla']}
        for L in ligas:
            for fx in ((L.get('proxima_fecha') or {}).get('partidos') or []) + ((L.get('ultima_fecha') or {}).get('partidos') or []):
                ids.add(fx['local']['id']); ids.add(fx['visitante']['id'])
        escudos(ids, {m['id'] for m in LIGAS})
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
