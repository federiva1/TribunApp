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
                    'home_name': p['home']['name'], 'away_name': p['away']['name']})
    try:
        copas = json.loads((ROOT / 'data' / 'fixtures' / 'copas.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        copas = {}
    for key in ('libertadores', 'sudamericana'):
        for p in ((copas.get(key) or {}).get('partidos')) or []:
            if not p.get('utcTime'):
                continue
            ko = datetime.fromisoformat(p['utcTime']).astimezone(AR)
            if ko.strftime('%Y-%m-%d') != fecha:
                continue
            out.append({'ko': ko, 'fecha_num': None, 'comp': key,
                        'home': p['home'].get('slug'), 'away': p['away'].get('slug'),
                        'home_name': p['home']['name'], 'away_name': p['away']['name'],
                        'home_logo': p['home'].get('logo'), 'away_logo': p['away'].get('logo')})
    out.sort(key=lambda m: m['ko'])
    return out


def _copa_esc(logo_url):
    """Rival de copa sin slug: escudos/copa/{id}.png (lo baja fetch_escudos_copa)."""
    m = re.search(r'/(\d+)\.png', logo_url or '')
    p = ROOT / 'escudos' / 'copa' / f'{m.group(1)}.png' if m else None
    return p if (p and p.exists()) else None


def _nombre(slug, fallback):
    return (NOM.get(slug) or fallback or '').upper()


def _html_uno(m, fecha, titulo):
    """Placa de UN partido: escudos grandes centrados + hora, en vez de la
    tarjeta chica de la lista (con un solo cruce quedaba flotando en el vacío)."""
    d = datetime.strptime(fecha, '%Y-%m-%d')
    sub = f'{DIAS[d.weekday()]} {d.day} DE {MESES[d.month - 1]}'
    torneo = (f"TORNEO LOCAL · FECHA {m['fecha_num']}" if m.get('fecha_num')
              else {'libertadores': 'COPA LIBERTADORES',
                    'sudamericana': 'COPA SUDAMERICANA'}.get(m['comp'], 'TORNEO LOCAL'))

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

    filas = ''.join(
        '<div class="p"><div class="hora">%s</div><div class="cruce">'
        '<div class="eq der"><span>%s</span>%s</div>'
        '<div class="vs">VS</div>'
        '<div class="eq izq">%s<span>%s</span></div>'
        '</div></div>'
        % (m['ko'].strftime('%H:%M'),
           _nombre(m['home'], m['home_name']), esc(m['home'], m.get('home_logo')),
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
        int(62 * escala), int(62 * escala), int(17 * escala),
        _logo_datauri(), torneo, titulo, sub, filas)


def generar(partidos, fecha, titulo, outdir):
    from playwright.sync_api import sync_playwright
    import os
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    Path(outdir).mkdir(parents=True, exist_ok=True)
    path = Path(outdir) / f'fecha-{fecha}.png'
    html = (_html_uno(partidos[0], fecha, titulo) if len(partidos) == 1
            else _html(partidos, fecha, titulo))
    html = aplicar_fondo_tribuna(html)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 760, 'height': 950}, device_scale_factor=2)
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
    args = ap.parse_args()

    fecha = args.date or datetime.now(AR).strftime('%Y-%m-%d')
    partidos = partidos_del_dia(fecha)
    if not partidos:
        print(f'No hay partidos nuestros el {fecha}')
        return 1
    for m in partidos:
        print(f"  {m['ko'].strftime('%H:%M')}  {m['home']} vs {m['away']}  ({m['comp']})")
    print('imagen:', generar(partidos, fecha, args.titulo.upper(), args.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
