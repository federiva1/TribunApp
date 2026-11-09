"""Placa de los cruces de playoffs del torneo local (octavos, cuartos, semis, final).

Misma estética que las placas de la fecha (social_fecha): logo, torneo en celeste,
título grande y una tarjeta por cruce con escudos, nombres y la posición de cada
uno en su zona. Las tarjetas van en el orden del cuadro y de a pares: los dos
cruces de cada par se enfrentan en la instancia siguiente.

De dónde salen los cruces:
  - si liga.json ya trae los partidos de esa instancia (campo `fase`, ver
    fetch_liga_fixtures.fecha_y_fase), de ahí, con día y hora;
  - si no, y es octavos, se arman con la tabla final de api-sports con el formato
    del torneo (el mismo PL_OCTAVOS del cuadro de index.html).

Uso:
  python scripts/social_cruces.py                       # octavos
  python scripts/social_cruces.py --sub "21 Y 22 DE NOVIEMBRE"
  python scripts/social_cruces.py --fase cuartos

Sale en data/social/preview/cruces-{fase}.png (gitignored): no publica nada.
"""
import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / 'data' / 'social' / 'preview'
sys.path.insert(0, str(ROOT / 'scripts'))
from social_lineups import NOM, _b64, esc_placa, aplicar_fondo_tribuna  # noqa: E402
from social_resultado import _logo_datauri                             # noqa: E402

AR = timezone(timedelta(hours=-3))
DIAS = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM']
FASES = {'octavos': (17, 'OCTAVOS DE FINAL'), 'cuartos': (18, 'CUARTOS DE FINAL'),
         'semis': (19, 'SEMIFINALES'), 'final': (20, 'FINAL')}
# Formato del torneo (igual que PL_OCTAVOS en index.html): 1A-8B, 4B-5A, 2B-7A, 3A-6B |
# 1B-8A, 4A-5B, 2A-7B, 3B-6A. Cada par de cruces consecutivos se cruza en cuartos.
PL_OCTAVOS = [('A1', 'B8'), ('B4', 'A5'), ('B2', 'A7'), ('A3', 'B6'),
              ('B1', 'A8'), ('A4', 'B5'), ('A2', 'B7'), ('B3', 'A6')]


def _slug_por_id():
    import re
    txt = (ROOT / 'js' / 'clubes.js').read_text(encoding='utf-8')
    m = re.search(r'ESCUDO_MAP\s*=\s*\{(.*?)\}', txt, re.S)
    return {int(k): v for k, v in re.findall(r"(\d+)\s*:\s*'([a-z]+)'", m.group(1))}


def seeds_de_la_tabla():
    """{'A1': slug, ...} con la tabla de api-sports (grupos del Clausura)."""
    from apikey import api_headers
    req = urllib.request.Request('https://v3.football.api-sports.io/standings?league=128&season=2026',
                                 headers=api_headers())
    with urllib.request.urlopen(req, timeout=25) as r:
        groups = json.loads(r.read())['response'][0]['league']['standings']
    sl = _slug_por_id()
    seeds = {}
    for g in groups:
        nombre = (g[0].get('group') or '').lower()
        if 'clausura' not in nombre:
            continue
        zona = 'A' if nombre.rstrip().endswith('a') else 'B'
        for row in g:
            seeds[f"{zona}{row['rank']}"] = sl.get(row['team']['id'])
    return seeds


def cruces_de_liga(num):
    liga = json.loads((ROOT / 'data' / 'fixtures' / 'liga.json').read_text(encoding='utf-8'))
    out = []
    for p in liga:
        if p.get('fecha') != num or not p.get('fase'):
            continue
        ko = datetime.fromisoformat(p['status']['utcTime']).astimezone(AR) if p['status'].get('utcTime') else None
        out.append({'home': p['home']['slug'], 'away': p['away']['slug'], 'ko': ko,
                    'hs': p.get('home_score'), 'as': p.get('away_score')})
    return out


def _html(cruces, titulo, sub):
    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))

    def esc(slug):
        p = esc_placa(slug)
        return f'<img class="esc" src="{_b64(p, "image/png")}">' if slug and p.exists() else '<div class="esc"></div>'

    def seed(s):
        return f'{s[1]}° ZONA {s[0]}' if s else ''

    def tarjeta(c):
        hora = (f"{DIAS[c['ko'].weekday()]} {c['ko'].day} · {c['ko'].strftime('%H:%M')}"
                if c.get('ko') else '')
        return ('<div class="p">%s<div class="cruce">'
                '<div class="eq der"><div class="nm"><span>%s</span><small>%s</small></div>%s</div>'
                '<div class="vs">VS</div>'
                '<div class="eq izq">%s<div class="nm"><span>%s</span><small>%s</small></div></div>'
                '</div></div>') % (
            f'<div class="hora">{hora}</div>' if hora else '',
            NOM.get(c['home'], c['home']).upper(), seed(c.get('sh')), esc(c['home']),
            esc(c['away']), NOM.get(c['away'], c['away']).upper(), seed(c.get('sa')))

    pares = [cruces[i:i + 2] for i in range(0, len(cruces), 2)]
    grupos = ''.join('<div class="par">%s</div>' % ''.join(tarjeta(c) for c in par) for par in pares)

    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{width:760px;height:950px;font-family:'Barlow Condensed',sans-serif;color:#fff;
  position:relative;overflow:hidden;background:#080c17;}
.bg{position:absolute;inset:0;
  background:radial-gradient(120%% 62%% at 50%% 118%%, rgba(56,140,220,.30) 0%%, rgba(20,44,86,.16) 42%%, transparent 70%%),
             radial-gradient(90%% 55%% at 50%% -10%%, rgba(28,58,110,.30), transparent 62%%),
             linear-gradient(180deg,#080c17 0%%,#0a1122 55%%,#070b16 100%%);}
.wrap{position:relative;height:100%%;padding:28px 34px 24px;display:flex;flex-direction:column}
.logo{height:36px;width:auto;align-self:flex-start}
.tit-box{text-align:center;margin:10px 0 14px}
.torneo{font-family:'Bebas Neue';font-size:18px;letter-spacing:5px;color:#38bdf8;margin-bottom:4px}
.tit{font-family:'Bebas Neue';font-size:42px;letter-spacing:8px;line-height:1}
.sub{font-family:'Bebas Neue';font-size:19px;letter-spacing:4px;color:#8b93a7;margin-top:6px}
.lista{flex:1;display:flex;flex-direction:column;justify-content:center;gap:%dpx}
.par{display:flex;flex-direction:column;gap:6px;padding-left:12px;border-left:3px solid rgba(56,189,248,.45)}
.p{position:relative;height:%dpx;border:1px solid rgba(255,255,255,.13);border-radius:14px;
   background:rgba(255,255,255,.035);display:flex;align-items:center;justify-content:center}
.hora{position:absolute;top:6px;right:14px;font-family:'Bebas Neue';font-size:15px;letter-spacing:2px;color:#38bdf8}
.cruce{display:flex;align-items:center;justify-content:center;width:100%%;padding:0 14px}
.eq{display:flex;align-items:center;gap:12px;width:44%%}
.eq.der{justify-content:flex-end;text-align:right}
.eq.izq{justify-content:flex-start;text-align:left}
.nm{display:flex;flex-direction:column;line-height:1}
.nm span{font-family:'Bebas Neue';font-size:%dpx;letter-spacing:2px}
.nm small{font-family:'Bebas Neue';font-size:13px;letter-spacing:2px;color:#38bdf8;margin-top:3px}
.esc{width:%dpx;height:%dpx;object-fit:contain;flex:0 0 auto;filter:drop-shadow(0 4px 10px rgba(0,0,0,.55))}
.vs{font-family:'Bebas Neue';font-size:24px;letter-spacing:2px;color:#5d6479;width:12%%;text-align:center}
.pie{text-align:center;font-family:'Bebas Neue';font-size:18px;letter-spacing:3px;color:#e8edf7;margin-top:10px}
.pie b{color:#38bdf8;font-weight:400}
</style></head><body>
<div class="bg"></div>
<div class="wrap">
  <img class="logo" src="%s">
  <div class="tit-box">
    <div class="torneo">TORNEO CLAUSURA 2026 · PLAYOFFS</div>
    <div class="tit">%s</div>
    %s
  </div>
  <div class="lista">%s</div>
  <div class="pie">ARMÁ TU 11 Y PUNTUÁ A LOS JUGADORES EN <b>TRIBUNAPP.COM.AR</b></div>
</div></body></html>""" % (
        ff, 14 if len(cruces) > 4 else 22, 68 if len(cruces) > 4 else 110,
        25 if len(cruces) > 4 else 32, 48 if len(cruces) > 4 else 72, 48 if len(cruces) > 4 else 72,
        _logo_datauri(), titulo, f'<div class="sub">{sub}</div>' if sub else '', grupos)


def generar(cruces, titulo, sub, path, escala=2):
    from playwright.sync_api import sync_playwright
    import os
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    path.parent.mkdir(parents=True, exist_ok=True)
    html = aplicar_fondo_tribuna(_html(cruces, titulo, sub))
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
    ap.add_argument('--fase', default='octavos', choices=list(FASES))
    ap.add_argument('--sub', default='', help='línea debajo del título (ej. "21 Y 22 DE NOVIEMBRE")')
    ap.add_argument('--escala', type=int, default=2)
    ap.add_argument('--out', default=str(PREVIEW))
    args = ap.parse_args()
    num, titulo = FASES[args.fase]

    cruces = cruces_de_liga(num)
    seeds = {}
    if args.fase == 'octavos':
        seeds = seeds_de_la_tabla()
        if not cruces:      # todavía no están en liga.json: se arman con la tabla
            cruces = [{'home': seeds[a], 'away': seeds[b]} for a, b in PL_OCTAVOS]
        else:               # mismo orden que el cuadro
            orden = {seeds[a]: i for i, (a, _) in enumerate(PL_OCTAVOS)}
            orden.update({seeds[b]: i for i, (_, b) in enumerate(PL_OCTAVOS)})
            cruces.sort(key=lambda c: orden.get(c['home'], orden.get(c['away'], 99)))
    if not cruces:
        print(f'No hay cruces de {args.fase} en liga.json todavía')
        return 1
    pos = {v: k for k, v in seeds.items()}
    for c in cruces:
        c['sh'], c['sa'] = pos.get(c['home']), pos.get(c['away'])
        print(f"  {c['home']} ({c['sh'] or '-'}) vs {c['away']} ({c['sa'] or '-'})"
              + (f"  {c['ko']:%a %d %H:%M}" if c.get('ko') else ''))
    sufijo = '' if args.escala == 2 else f'-x{args.escala}'
    print('imagen:', generar(cruces, titulo, args.sub.upper(), Path(args.out) / f'cruces-{args.fase}{sufijo}.png',
                             escala=args.escala))
    return 0


if __name__ == '__main__':
    sys.exit(main())
