"""Placa promocional con los partidos del día (liga + copas).

Misma estética que la placa de FINAL DEL PARTIDO: logo arriba, torneo/fecha en
celeste, título grande y una tarjeta por partido con escudos, nombres y hora.

Uso:
  python scripts/social_fecha.py                    # partidos de hoy (hora AR)
  python scripts/social_fecha.py --date 2026-08-16
  python scripts/social_fecha.py --titulo "LA FECHA CONTINÚA"

Sale en data/social/preview/fecha-{YYYY-MM-DD}.png y no toca ningún estado:
es una placa a demanda, no la genera ningún workflow.
"""
import argparse
import re
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / 'data' / 'social' / 'preview'

sys.path.insert(0, str(ROOT / 'scripts'))
from social_lineups import NOM, _b64, esc_placa, aplicar_fondo_tribuna  # noqa: E402
from social_resultado import _logo_datauri, ESTADIO_ICO   # noqa: E402
from clubes_map import ALIAS                           # noqa: E402

# alias/slug -> slug, para resolver lo que llega por --solo
SLUG_POR_ALIAS = {a: sl for sl, a in ALIAS.items()}

AR = timezone(timedelta(hours=-3))
DIAS = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO']
MESES = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO',
         'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']


def partidos_del_dia(fecha):
    """Todos los partidos nuestros cuyo kickoff cae ese día en hora argentina."""
    out = []
    liga = json.loads((ROOT / 'data' / 'fixtures' / 'liga.json').read_text(encoding='utf-8'))
    for p in liga:
        st = p.get('status') or {}
        if not st.get('utcTime'):
            continue
        ko = datetime.fromisoformat(st['utcTime']).astimezone(AR)
        if ko.strftime('%Y-%m-%d') != fecha:
            continue
        out.append({'ko': ko, 'fecha_num': p.get('fecha'), 'comp': 'liga',
                    'home': p['home']['slug'], 'away': p['away']['slug'],
                    'home_name': p['home']['name'], 'away_name': p['away']['name'],
                    'hs': p.get('home_score'), 'as': p.get('away_score')})
    try:
        copas = json.loads((ROOT / 'data' / 'fixtures' / 'copas.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        copas = {}
    for key in ('libertadores', 'sudamericana'):
        todos = [p for p in (((copas.get(key) or {}).get('partidos')) or []) if p.get('utcTime')]
        for p in todos:
            ko = datetime.fromisoformat(p['utcTime']).astimezone(AR)
            if ko.strftime('%Y-%m-%d') != fecha:
                continue
            # Ida o vuelta: se deduce de la otra pata de la misma serie (mismos
            # dos clubes en la misma copa). Si no está la otra, no se etiqueta.
            par = {p['home']['name'], p['away']['name']}
            otros = [q for q in todos if q is not p and {q['home']['name'], q['away']['name']} == par]
            pata = None
            if otros:
                pata = 'IDA' if all(q['utcTime'] > p['utcTime'] for q in otros) else 'VUELTA'
            out.append({'ko': ko, 'fecha_num': None, 'comp': key,
                        'ronda': p.get('ronda'), 'pata': pata,
                        'home': p['home'].get('slug'), 'away': p['away'].get('slug'),
                        'home_name': p['home']['name'], 'away_name': p['away']['name'],
                        'home_logo': p['home'].get('logo'), 'away_logo': p['away'].get('logo')})
    out.sort(key=lambda m: m['ko'])
    return out


def partidos_de_la_fecha(num):
    """Todos los partidos de liga de la fecha N (número de ronda), por kickoff."""
    liga = json.loads((ROOT / 'data' / 'fixtures' / 'liga.json').read_text(encoding='utf-8'))
    out = []
    for p in liga:
        st = p.get('status') or {}
        if p.get('fecha') != num or not st.get('utcTime'):
            continue
        out.append({'ko': datetime.fromisoformat(st['utcTime']).astimezone(AR), 'fecha_num': num,
                    'comp': 'liga', 'home': p['home']['slug'], 'away': p['away']['slug'],
                    'home_name': p['home']['name'], 'away_name': p['away']['name']})
    out.sort(key=lambda m: m['ko'])
    return out


def filtrar(partidos, cruces):
    """Deja solo los cruces pedidos (--solo). Cada uno es 'local-visitante' con
    slug o alias ('instituto-boca'), en el orden que quiera: el cruce se compara
    como par, así que no hay que acordarse de quién es local."""
    def slug(x):
        x = (x or '').strip().lower().replace(' ', '')
        return SLUG_POR_ALIAS.get(x, x)

    pedidos, faltan = [], []
    for c in cruces:
        partes = [x for x in c.split('-') if x]
        if len(partes) != 2:
            faltan.append((c, 'no tiene forma local-visitante'))
            continue
        pedidos.append((c, frozenset(slug(x) for x in partes)))

    out = []
    for c, par in pedidos:
        m = next((m for m in partidos if {m['home'], m['away']} == set(par)), None)
        if m:
            out.append(m)
        else:
            faltan.append((c, 'no hay partido de ese cruce ese día'))
    for c, por_que in faltan:
        print(f'  OJO: {c} -> {por_que}')
    return out, [c for c, _ in faltan]


def _copa_esc(logo_url):
    """Rival de copa sin slug: escudos/copa/{id}.png (lo baja fetch_escudos_copa)."""
    m = re.search(r'/(\d+)\.png', logo_url or '')
    p = ROOT / 'escudos' / 'copa' / f'{m.group(1)}.png' if m else None
    return p if (p and p.exists()) else None


def _nombre(slug, fallback):
    return (NOM.get(slug) or fallback or '').upper()


def _torneo_label(m):
    """'TORNEO LOCAL · FECHA 8' o 'COPA LIBERTADORES · CUARTOS DE FINAL · IDA'."""
    if m.get('fecha_num'):
        return f"TORNEO LOCAL · FECHA {m['fecha_num']}"
    base = {'libertadores': 'COPA LIBERTADORES',
            'sudamericana': 'COPA SUDAMERICANA'}.get(m['comp'], 'TORNEO LOCAL')
    partes = [base] + [x.upper() for x in (m.get('ronda'), m.get('pata')) if x]
    return ' · '.join(partes)


def _html_uno(m, fecha, titulo):
    """Placa de UN partido: escudos grandes centrados + hora, en vez de la
    tarjeta chica de la lista (con un solo cruce quedaba flotando en el vacío)."""
    d = datetime.strptime(fecha, '%Y-%m-%d')
    sub = f'{DIAS[d.weekday()]} {d.day} DE {MESES[d.month - 1]}'
    torneo = _torneo_label(m)

    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))

    def esc(slug, logo=None):
        p = esc_placa(slug)
        if slug and p.exists():
            return f'<img class="esc" src="{_b64(p, "image/png")}">'
        cp = _copa_esc(logo)
        return (f'<img class="esc" src="{_b64(cp, "image/png")}">'
                if cp else '<div class="esc"></div>')

    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{width:760px;height:950px;font-family:'Barlow Condensed',sans-serif;color:#fff;
  position:relative;overflow:hidden;background:#080c17;}
.bg{position:absolute;inset:0;
  background:radial-gradient(120%% 62%% at 50%% 118%%, rgba(56,140,220,.30) 0%%, rgba(20,44,86,.16) 42%%, transparent 70%%),
             radial-gradient(90%% 55%% at 50%% -10%%, rgba(28,58,110,.30), transparent 62%%),
             linear-gradient(180deg,#080c17 0%%,#0a1122 55%%,#070b16 100%%);}
.glow{position:absolute;left:0;right:0;bottom:0;height:38%%;
  background:repeating-linear-gradient(90deg, rgba(120,180,255,.05) 0 3px, transparent 3px 9px);
  -webkit-mask-image:linear-gradient(0deg,rgba(0,0,0,.85),transparent);}
.wrap{position:relative;height:100%%;padding:30px 34px 26px;display:flex;flex-direction:column}
.logo{height:38px;width:auto;align-self:flex-start}
.tit-box{text-align:center;margin:26px 0 0}
.torneo{font-family:'Bebas Neue';font-size:19px;letter-spacing:5px;color:#38bdf8;margin-bottom:5px}
.tit{font-family:'Bebas Neue';font-size:44px;letter-spacing:9px;line-height:1}
.sub{font-family:'Bebas Neue';font-size:20px;letter-spacing:4px;color:#8b93a7;margin-top:7px}
.hero{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:34px}
.cruce{display:flex;align-items:center;justify-content:center;gap:48px}
.eq{display:flex;flex-direction:column;align-items:center;gap:18px;width:250px}
.esc{width:170px;height:170px;object-fit:contain;
     filter:drop-shadow(0 10px 26px rgba(0,0,0,.6))}
.eq span{font-family:'Bebas Neue';font-size:34px;letter-spacing:3px;text-align:center}
.vs{font-family:'Bebas Neue';font-size:40px;letter-spacing:3px;color:#5d6479}
.hora{font-family:'Bebas Neue';font-size:56px;letter-spacing:6px;color:#38bdf8}
.pie{text-align:center;font-family:'Bebas Neue';font-size:19px;letter-spacing:3px;color:#e8edf7;margin-top:6px}
.pie b{color:#38bdf8;font-weight:400}
</style></head><body>
<div class="bg"></div><div class="glow"></div>
<div class="wrap">
  <img class="logo" src="%s">
  <div class="tit-box">
    <div class="torneo">%s</div>
    <div class="tit">%s</div>
    <div class="sub">%s</div>
  </div>
  <div class="hero">
    <div class="cruce">
      <div class="eq">%s<span>%s</span></div>
      <div class="vs">VS</div>
      <div class="eq">%s<span>%s</span></div>
    </div>
    <div class="hora">%s HS</div>
  </div>
  <div class="pie">SEGUILOS Y PUNTUÁ A LOS JUGADORES EN <b>TRIBUNAPP.COM.AR</b></div>
</div></body></html>""" % (
        ff, _logo_datauri(), torneo, titulo, sub,
        esc(m['home'], m.get('home_logo')), _nombre(m['home'], m['home_name']),
        esc(m['away'], m.get('away_logo')), _nombre(m['away'], m['away_name']),
        m['ko'].strftime('%H:%M'))


RESULTADOS = False   # --resultados: marcador en lugar de "VS" y "FINAL" en lugar de la hora


def _html(partidos, fecha, titulo):
    d = datetime.strptime(fecha, '%Y-%m-%d')
    sub = f'{DIAS[d.weekday()]} {d.day} DE {MESES[d.month - 1]}'
    nums = {m['fecha_num'] for m in partidos if m['fecha_num']}
    torneo = f'TORNEO LOCAL · FECHA {sorted(nums)[0]}' if len(nums) == 1 else 'TORNEO LOCAL'

    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))

    def esc(slug, logo=None):
        p = esc_placa(slug)
        if slug and p.exists():
            return f'<img class="esc" src="{_b64(p, "image/png")}">'
        cp = _copa_esc(logo)
        return (f'<img class="esc" src="{_b64(cp, "image/png")}">'
                if cp else '<div class="esc"></div>')

    # con muchos partidos las tarjetas se achican para que entren todas; con
    # dos o tres se agrandan, si no quedan flotando en el medio de la placa.
    n = max(1, len(partidos))
    if n <= 2:
        alto, escala = 210, 1.35
    elif n == 3:
        alto, escala = 165, 1.15
    else:
        alto = 132 if n == 4 else (118 if n == 5 else 102)
        escala = 1.0 if n == 4 else (0.92 if n == 5 else 0.82)

    def _medio(m):
        if RESULTADOS and m.get('hs') is not None and m.get('as') is not None:
            return '<div class="vs res">%s - %s</div>' % (m['hs'], m['as'])
        return '<div class="vs">VS</div>'

    filas = ''.join(
        '<div class="p"><div class="hora">%s</div><div class="cruce">'
        '<div class="eq der"><span>%s</span>%s</div>'
        '%s'
        '<div class="eq izq">%s<span>%s</span></div>'
        '</div></div>'
        % ('FINAL' if RESULTADOS else m['ko'].strftime('%H:%M'),
           _nombre(m['home'], m['home_name']), esc(m['home'], m.get('home_logo')),
           _medio(m),
           esc(m['away'], m.get('away_logo')), _nombre(m['away'], m['away_name']))
        for m in partidos)

    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{width:760px;height:950px;font-family:'Barlow Condensed',sans-serif;color:#fff;
  position:relative;overflow:hidden;background:#080c17;}
.bg{position:absolute;inset:0;
  background:radial-gradient(120%% 62%% at 50%% 118%%, rgba(56,140,220,.30) 0%%, rgba(20,44,86,.16) 42%%, transparent 70%%),
             radial-gradient(90%% 55%% at 50%% -10%%, rgba(28,58,110,.30), transparent 62%%),
             linear-gradient(180deg,#080c17 0%%,#0a1122 55%%,#070b16 100%%);}
.glow{position:absolute;left:0;right:0;bottom:0;height:38%%;
  background:repeating-linear-gradient(90deg, rgba(120,180,255,.05) 0 3px, transparent 3px 9px);
  -webkit-mask-image:linear-gradient(0deg,rgba(0,0,0,.85),transparent);}
.wrap{position:relative;height:100%%;padding:30px 34px 26px;display:flex;flex-direction:column}
.logo{height:38px;width:auto;align-self:flex-start}
.tit-box{text-align:center;margin:26px 0 20px}
.torneo{font-family:'Bebas Neue';font-size:19px;letter-spacing:5px;color:#38bdf8;margin-bottom:5px}
.tit{font-family:'Bebas Neue';font-size:44px;letter-spacing:9px;line-height:1}
.sub{font-family:'Bebas Neue';font-size:20px;letter-spacing:4px;color:#8b93a7;margin-top:7px}
.lista{flex:1;display:flex;flex-direction:column;justify-content:center;gap:%dpx}
.p{position:relative;height:%dpx;border:1px solid rgba(255,255,255,.13);border-radius:16px;
   background:rgba(255,255,255,.035);display:flex;align-items:center;justify-content:center}
.hora{position:absolute;top:10px;right:18px;font-family:'Bebas Neue';font-size:%dpx;
      letter-spacing:2px;color:#38bdf8}
.cruce{display:flex;align-items:center;justify-content:center;width:100%%;padding:0 18px}
.eq{display:flex;align-items:center;gap:14px;width:44%%}
.eq.der{justify-content:flex-end}
.eq.izq{justify-content:flex-start}
.eq span{font-family:'Bebas Neue';font-size:%dpx;letter-spacing:2.5px}
.esc{width:%dpx;height:%dpx;object-fit:contain;flex:0 0 auto;
     filter:drop-shadow(0 5px 14px rgba(0,0,0,.55))}
.vs{font-family:'Bebas Neue';font-size:%dpx;letter-spacing:2px;color:#5d6479;width:12%%;text-align:center}
.vs.res{color:#fff;font-size:%dpx;letter-spacing:3px;width:auto;white-space:nowrap;padding:0 12px}
.pie{text-align:center;font-family:'Bebas Neue';font-size:19px;letter-spacing:3px;color:#e8edf7;margin-top:6px}
.pie b{color:#38bdf8;font-weight:400}
</style></head><body>
<div class="bg"></div><div class="glow"></div>
<div class="wrap">
  <img class="logo" src="%s">
  <div class="tit-box">
    <div class="torneo">%s</div>
    <div class="tit">%s</div>
    <div class="sub">%s</div>
  </div>
  <div class="lista">%s</div>
  <div class="pie">SEGUILOS Y PUNTUÁ A LOS JUGADORES EN <b>TRIBUNAPP.COM.AR</b></div>
</div></body></html>""" % (
        ff,
        int(16 * escala), alto, int(21 * escala), int(25 * escala),
        int(62 * escala), int(62 * escala), int(17 * escala), int(46 * escala),
        _logo_datauri(), torneo, titulo, sub, filas)


def _html_columnas(partidos, titulo):
    """Placa apaisada 1280x720 con una columna por día (todos los partidos de una fecha)."""
    dias = []
    for m in partidos:
        if m['ko'].date() not in dias:
            dias.append(m['ko'].date())
    nums = {m['fecha_num'] for m in partidos if m['fecha_num']}
    torneo = f'TORNEO LOCAL · FECHA {sorted(nums)[0]}' if len(nums) == 1 else 'TORNEO LOCAL'

    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))

    def esc(slug):
        p = esc_placa(slug)
        return f'<img class="esc" src="{_b64(p, "image/png")}">' if (slug and p.exists()) else '<div class="esc"></div>'

    # alto de tarjeta según la columna con más partidos (entra todo en 720 px)
    maxn = max(sum(1 for m in partidos if m['ko'].date() == d) for d in dias)
    gap = 10
    alto = min(124, int((470 - (maxn - 1) * gap) / maxn))

    cols = ''
    for d in dias:
        ms = [m for m in partidos if m['ko'].date() == d]
        tarjetas = ''.join(
            '<div class="p"><div class="eq">%s<span>%s</span></div>'
            '<div class="mid"><div class="hora">%s</div><div class="vs">VS</div></div>'
            '<div class="eq">%s<span>%s</span></div></div>'
            % (esc(m['home']), _nombre(m['home'], m['home_name']), m['ko'].strftime('%H:%M'),
               esc(m['away']), _nombre(m['away'], m['away_name']))
            for m in ms)
        cols += ('<div class="col"><div class="dia">%s</div><div class="fec">%d DE %s</div>'
                 '<div class="cards">%s</div></div>'
                 % (DIAS[d.weekday()], d.day, MESES[d.month - 1], tarjetas))

    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{width:1280px;height:720px;font-family:'Barlow Condensed',sans-serif;color:#fff;
  position:relative;overflow:hidden;background:#080c17;}
.bg{position:absolute;inset:0;
  background:radial-gradient(120%% 70%% at 50%% 122%%, rgba(56,140,220,.30) 0%%, rgba(20,44,86,.16) 42%%, transparent 70%%),
             radial-gradient(90%% 60%% at 50%% -12%%, rgba(28,58,110,.30), transparent 62%%),
             linear-gradient(180deg,#080c17 0%%,#0a1122 55%%,#070b16 100%%);}
.glow{position:absolute;left:0;right:0;bottom:0;height:34%%;
  background:repeating-linear-gradient(90deg, rgba(120,180,255,.05) 0 3px, transparent 3px 9px);
  -webkit-mask-image:linear-gradient(0deg,rgba(0,0,0,.85),transparent);}
.wrap{position:relative;height:100%%;padding:24px 44px 18px;display:flex;flex-direction:column}
.logo{position:absolute;left:44px;top:24px;height:38px;width:auto}
.tit-box{text-align:center;margin:0 0 16px}
.torneo{font-family:'Bebas Neue';font-size:19px;letter-spacing:5px;color:#38bdf8;margin-bottom:3px}
.tit{font-family:'Bebas Neue';font-size:42px;letter-spacing:9px;line-height:1}
.cols{flex:1;display:flex;gap:18px;min-height:0}
.col{flex:1;display:flex;flex-direction:column;min-width:0}
.dia{font-family:'Bebas Neue';font-size:30px;letter-spacing:6px;text-align:center;line-height:1}
.fec{font-family:'Bebas Neue';font-size:15px;letter-spacing:3px;text-align:center;color:#8b93a7;
     margin:4px 0 9px;padding-bottom:9px;border-bottom:2px solid rgba(56,189,248,.55)}
.cards{display:flex;flex-direction:column;gap:%dpx}
.p{height:%dpx;border:1px solid rgba(255,255,255,.13);border-radius:14px;
   background:rgba(255,255,255,.035);display:flex;align-items:center;padding:0 8px}
.eq{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;min-width:0}
.eq span{font-family:'Bebas Neue';font-size:15px;letter-spacing:1.4px;line-height:1.02;text-align:center}
.esc{width:50px;height:50px;object-fit:contain;flex:0 0 auto;filter:drop-shadow(0 4px 10px rgba(0,0,0,.55))}
.mid{width:62px;text-align:center;flex:0 0 auto}
.hora{font-family:'Bebas Neue';font-size:25px;letter-spacing:1.5px;color:#38bdf8;line-height:1}
.vs{font-family:'Bebas Neue';font-size:13px;letter-spacing:2px;color:#5d6479;margin-top:3px}
.pie{text-align:center;font-family:'Bebas Neue';font-size:18px;letter-spacing:3px;color:#e8edf7;margin-top:12px}
.pie b{color:#38bdf8;font-weight:400}
</style></head><body>
<div class="bg"></div><div class="glow"></div>
<div class="wrap">
  <img class="logo" src="%s">
  <div class="tit-box"><div class="torneo">%s</div><div class="tit">%s</div></div>
  <div class="cols">%s</div>
  <div class="pie">SEGUILOS Y PUNTUÁ A LOS JUGADORES EN <b>TRIBUNAPP.COM.AR</b></div>
</div></body></html>""" % (ff, gap, alto, _logo_datauri(), torneo, titulo, cols)


def generar_columnas(partidos, titulo, outdir, nombre, escala=3):
    """Placa apaisada 16:9: escala 3 = 3840x2160 (4K)."""
    from playwright.sync_api import sync_playwright
    import os
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    Path(outdir).mkdir(parents=True, exist_ok=True)
    path = Path(outdir) / nombre
    html = aplicar_fondo_tribuna(_html_columnas(partidos, titulo))
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 1280, 'height': 720}, device_scale_factor=escala)
        pg.set_content(html)
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(path))
        b.close()
    return path


def generar(partidos, fecha, titulo, outdir, nombre=None, escala=2):
    from playwright.sync_api import sync_playwright
    import os
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    Path(outdir).mkdir(parents=True, exist_ok=True)
    path = Path(outdir) / (nombre or f'fecha-{fecha}.png')
    html = (_html_uno(partidos[0], fecha, titulo) if len(partidos) == 1
            else _html(partidos, fecha, titulo))
    html = aplicar_fondo_tribuna(html)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 760, 'height': 950}, device_scale_factor=escala)
        pg.set_content(html)
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(path))
        b.close()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (hora argentina). Default: hoy')
    ap.add_argument('--titulo', default='PARTIDOS DE HOY')
    ap.add_argument('--out', default=str(PREVIEW))
    ap.add_argument('--cada-uno', action='store_true',
                    help='una placa por partido (layout de escudos grandes) en vez de la lista del dia')
    ap.add_argument('--solo', nargs='+', metavar='LOCAL-VISITANTE',
                    help='solo estos cruces, por slug o alias (ej: instituto-boca racing-belgrano). '
                         'Implica --cada-uno.')
    ap.add_argument('--dias', nargs='+', metavar='YYYY-MM-DD',
                    help='placa apaisada 16:9 con los partidos de estos días, una columna por día (ej. hoy y mañana)')
    ap.add_argument('--resultados', action='store_true',
                    help='placa de resultados: marcador en lugar de VS y FINAL en lugar de la hora')
    ap.add_argument('--escala', type=int, default=2,
                    help='factor de resolucion: 2 = 1520x1900 (default), 4 = ultra HD 3040x3800')
    ap.add_argument('--fecha-num', type=int, metavar='N',
                    help='placa apaisada 16:9 con TODOS los partidos de la fecha N, una columna por dia '
                         '(--escala 3 = 3840x2160 4K; default 3 en este modo)')
    args = ap.parse_args()
    global RESULTADOS
    RESULTADOS = args.resultados
    sufijo = '' if args.escala == 2 else f'-x{args.escala}'

    if args.dias:
        partidos = [m for d in args.dias for m in partidos_del_dia(d)]
        if not partidos:
            print(f'No hay partidos nuestros en {args.dias}')
            return 1
        for m in partidos:
            print(f"  {m['ko'].strftime('%a %d/%m %H:%M')}  {m['home']} vs {m['away']}  ({m['comp']})")
        esc = args.escala if args.escala != 2 else 3
        titulo = args.titulo.upper() if args.titulo != 'PARTIDOS DE HOY' else 'PARTIDOS DE HOY Y MAÑANA'
        print('imagen:', generar_columnas(partidos, titulo, args.out,
                                           f"dias-{'_'.join(args.dias)}-columnas-x{esc}.png", escala=esc))
        return 0

    if args.fecha_num:
        partidos = partidos_de_la_fecha(args.fecha_num)
        if not partidos:
            print(f'No hay partidos de la fecha {args.fecha_num}')
            return 1
        for m in partidos:
            print(f"  {m['ko'].strftime('%a %d/%m %H:%M')}  {m['home']} vs {m['away']}")
        esc = args.escala if args.escala != 2 else 3
        titulo = args.titulo.upper() if args.titulo != 'PARTIDOS DE HOY' else 'PARTIDOS DE LA FECHA'
        print('imagen:', generar_columnas(partidos, titulo, args.out,
                                           f'fecha-{args.fecha_num}-columnas-x{esc}.png', escala=esc))
        return 0

    fecha = args.date or datetime.now(AR).strftime('%Y-%m-%d')
    partidos = partidos_del_dia(fecha)
    if not partidos:
        print(f'No hay partidos nuestros el {fecha}')
        return 1
    sin_resolver = []
    if args.solo:
        partidos, sin_resolver = filtrar(partidos, args.solo)
        if not partidos:
            print(f'Ninguno de los cruces pedidos juega el {fecha}')
            return 1
    for m in partidos:
        print(f"  {m['ko'].strftime('%H:%M')}  {m['home']} vs {m['away']}  ({m['comp']})")
    if args.cada_uno or args.solo:
        for m in partidos:
            print('imagen:', generar([m], fecha, args.titulo.upper(), args.out,
                                    nombre=f"fecha-{fecha}-{m['home']}-{m['away']}{sufijo}.png",
                                    escala=args.escala))
        return 1 if sin_resolver else 0
    print('imagen:', generar(partidos, fecha, args.titulo.upper(), args.out,
                            nombre=f'fecha-{fecha}{sufijo}.png', escala=args.escala))
    return 0


if __name__ == '__main__':
    sys.exit(main())
