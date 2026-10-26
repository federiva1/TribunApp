"""Placa de la TABLA ANUAL (los primeros N puestos).

Misma estética que las otras placas (logo arriba, torneo en celeste, título
grande, tarjetas y pie). Sale en data/social/preview/tabla-anual.png y no toca
ningún estado: es una placa a demanda, no la genera ningún workflow.

De dónde salen los números
--------------------------
NO se recalcula la tabla acá. Se abre `tablas.html` en el browser y se lee su
`DATA.anual`, que es lo que ve el hincha en la web — misma idea que
`social_xi_cruce.py`, que dibuja la cancha llamando a `fcCanchaHTML`: una sola
lógica para mantener. Eso incluye `sfCorregirConLiga()`, que completa los
partidos FT que /standings todavía no contabilizó.

El browser del entorno en la nube no llega a api-sports, así que el JSON de
/standings se baja con urllib (que sí pasa por el proxy) y se le sirve a la
página interceptando `/api/apisports/**`. La página no hace red hacia afuera.

Uso:
  python scripts/social_tabla.py                 # top 6
  python scripts/social_tabla.py --top 10
  python scripts/social_tabla.py --sub "FECHA 11"
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / 'data' / 'social' / 'preview'

sys.path.insert(0, str(ROOT / 'scripts'))
from social_lineups import NOM, _b64, esc_placa          # noqa: E402
from social_resultado import _logo_datauri               # noqa: E402
from clubes_map import CLUBES                            # noqa: E402
import apikey                                            # noqa: E402

LEAGUE, SEASON = 128, 2026
PUERTO = 3031
# api-sports id -> slug del app (el inverso de clubes_map)
POR_ID = {v['apisports']: k for k, v in CLUBES.items()}


def bajar_standings():
    url = f'https://v3.football.api-sports.io/standings?league={LEAGUE}&season={SEASON}'
    req = urllib.request.Request(url, headers=apikey.api_headers())
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode('utf-8')


def leer_anual(standings_json):
    """Abre tablas.html en el browser y devuelve su DATA.anual, ya corregida."""
    from playwright.sync_api import sync_playwright
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PUERTO)],
                           cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={'width': 1200, 'height': 1000})
            pg.route('**/api/apisports/**', lambda route: route.fulfill(
                status=200, content_type='application/json', body=standings_json))
            pg.goto(f'http://localhost:{PUERTO}/tablas.html', wait_until='domcontentloaded')
            # DATA se declara con `let`, así que NO cuelga de window.
            pg.wait_for_function(
                "()=>typeof DATA!=='undefined' && DATA && DATA.anual && DATA.anual.length",
                timeout=60000)
            out = pg.evaluate("""()=>DATA.anual.map(r=>({
                id:r.team.id, nombre:r.team.name, pts:r.points, pj:r.all.played,
                dg:r.goalsDiff}))""")
            b.close()
        return out
    finally:
        srv.terminate()


def _html(filas, titulo, sub):
    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))

    def esc(slug):
        p = esc_placa(slug) if slug else None
        return (f'<img class="esc" src="{_b64(p, "image/png")}">'
                if (p and p.exists()) else '<div class="esc"></div>')

    # El alto total es fijo (950px): las filas se achican para que entren todas.
    # Con 6 filas de 112px la última se salía de la placa.
    n = max(1, len(filas))
    alto = 96 if n <= 6 else (76 if n <= 8 else 62)
    gap = 12 if n <= 6 else (10 if n <= 8 else 8)

    cuerpo = ''.join(
        '<div class="f%s"><div class="pos">%d</div>%s'
        '<div class="nom">%s</div>'
        '<div class="num pj">%d</div><div class="num dg">%s</div>'
        '<div class="pts">%d</div></div>'
        % (' lider' if i == 1 else '', i, esc(f['slug']), f['nombre'],
           f['pj'], ('+%d' % f['dg']) if f['dg'] > 0 else f['dg'], f['pts'])
        for i, f in enumerate(filas, 1))

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
.tit-box{text-align:center;margin:26px 0 14px}
.torneo{font-family:'Bebas Neue';font-size:19px;letter-spacing:5px;color:#38bdf8;margin-bottom:5px}
.tit{font-family:'Bebas Neue';font-size:44px;letter-spacing:9px;line-height:1}
.sub{font-family:'Bebas Neue';font-size:20px;letter-spacing:4px;color:#8b93a7;margin-top:7px}
/* encabezado de columnas: mismas medidas que las filas */
.head,.f{display:grid;grid-template-columns:46px 62px 1fr 56px 62px 74px;align-items:center}
.head{padding:0 16px 7px;font-family:'Bebas Neue';font-size:15px;letter-spacing:2.5px;color:#5d6479}
.head div{text-align:center}
.head .h-nom{text-align:left;padding-left:4px}
.lista{flex:1;display:flex;flex-direction:column;justify-content:center;gap:%dpx}
.f{height:%dpx;border:1px solid rgba(255,255,255,.13);border-radius:16px;
   background:rgba(255,255,255,.035);padding:0 16px}
.f.lider{border-color:rgba(56,189,248,.55);background:rgba(56,189,248,.09)}
.pos{font-family:'Bebas Neue';font-size:30px;letter-spacing:1px;color:#8b93a7;text-align:center}
.f.lider .pos{color:#38bdf8}
.esc{width:50px;height:50px;object-fit:contain;justify-self:center;
     filter:drop-shadow(0 5px 14px rgba(0,0,0,.55))}
.nom{font-family:'Bebas Neue';font-size:27px;letter-spacing:2.5px;padding-left:4px;
     white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.num{font-family:'Bebas Neue';font-size:24px;letter-spacing:1px;color:#8b93a7;text-align:center}
.pts{font-family:'Bebas Neue';font-size:36px;letter-spacing:1px;text-align:center;color:#e8edf7}
.f.lider .pts{color:#38bdf8}
.pie{text-align:center;font-family:'Bebas Neue';font-size:19px;letter-spacing:3px;color:#e8edf7;margin-top:10px}
.pie b{color:#38bdf8;font-weight:400}
</style></head><body>
<div class="bg"></div><div class="glow"></div>
<div class="wrap">
  <img class="logo" src="%s">
  <div class="tit-box">
    <div class="torneo">TORNEO LOCAL 2026</div>
    <div class="tit">%s</div>
    <div class="sub">%s</div>
  </div>
  <div class="head"><div></div><div></div><div class="h-nom">EQUIPO</div>
    <div>PJ</div><div>DIF</div><div>PTS</div></div>
  <div class="lista">%s</div>
  <div class="pie">TABLAS Y ESTADÍSTICAS EN <b>TRIBUNAPP.COM.AR</b></div>
</div></body></html>""" % (ff, gap, alto, _logo_datauri(), titulo, sub, cuerpo)


def generar(filas, titulo, sub, out):
    from playwright.sync_api import sync_playwright
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix('.html')
    tmp.write_text(_html(filas, titulo, sub), encoding='utf-8')
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 760, 'height': 950}, device_scale_factor=2)
        pg.goto(tmp.as_uri())
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(out))
        b.close()
    tmp.unlink(missing_ok=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=6, help='cuántos puestos (default 6)')
    ap.add_argument('--titulo', default='TABLA ANUAL')
    ap.add_argument('--sub', default=None, help='subtítulo; default "TOP N"')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    anual = leer_anual(bajar_standings())
    filas = []
    for r in anual[:args.top]:
        slug = POR_ID.get(r['id'])
        filas.append({**r, 'slug': slug,
                      'nombre': (NOM.get(slug) or r['nombre']).upper()})
    sub = args.sub if args.sub is not None else f'TOP {args.top}'
    out = Path(args.out) if args.out else PREVIEW / 'tabla-anual.png'
    print('imagen:', generar(filas, args.titulo.upper(), sub.upper(), out))
    for i, f in enumerate(filas, 1):
        print(f"  {i}. {f['nombre']:<18} PJ {f['pj']:>2}  DG {f['dg']:>+3}  {f['pts']} pts")


if __name__ == '__main__':
    main()
