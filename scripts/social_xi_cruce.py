#!/usr/bin/env python3
"""Placa de las DOS formaciones enfrentadas en una cancha apaisada.

Alternativa a las dos placas verticales de social_lineups (una por equipo):
mismo insumo (startXI con grid api-sports) pero los 22 en una sola imagen, el
local atacando a la derecha y el visitante a la izquierda — la misma orientación
que la ficha del partido en la web (js/ficha-cancha.js).

    python scripts/social_xi_cruce.py --test-lineups stub.json --local X --visitante Y
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from social_lineups import (NOM, _b64, _apellido, _elegir, _plantel_por_num,   # noqa: E402
                            esc_placa, posiciones)

PREVIEW = ROOT / 'data' / 'social' / 'preview'
ANCHO, ALTO = 1280, 800


def _jugadores(slug, startxi, es_local):
    """(x, y) de la placa vertical → cancha apaisada.

    posiciones() devuelve x = carril (col 1 = izquierda del equipo) e y = avance
    (90 = arquero, 14 = punta). El local ataca a la derecha: su lateral izquierdo
    queda arriba; el visitante ataca a la izquierda y va espejado en los dos ejes.
    """
    plantel = _plantel_por_num(slug) if slug else {}
    out = []
    for xv, yv, pl in posiciones(startxi):
        num = str(pl.get('number') or '')
        api_nom = pl.get('name') or ''
        del_plantel = _elegir(plantel.get(num) or [], api_nom)
        nombre = (del_plantel or api_nom) if '.' in api_nom else (api_nom or del_plantel)
        avance = (100 - yv) / 100.0                      # 0 = arquero, 1 = ataque
        x = 3.5 + avance * 45.5 if es_local else 96.5 - avance * 45.5
        y = 9 + xv * 0.82 if es_local else 91 - xv * 0.82
        out.append({'x': round(x, 2), 'y': round(y, 2), 'num': num,
                    'nombre': _apellido(nombre)})
    return out


def _html(local, visitante):
    """local/visitante: dict {slug, nombre, formacion, startXI}."""
    kits_js = (ROOT / 'js' / 'kits.js').read_text(encoding='utf-8')
    colors_js = (ROOT / 'js' / 'club-colors.js').read_text(encoding='utf-8')
    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))

    def esc_tag(slug, cls):
        p = esc_placa(slug)
        return f'<img class="{cls}" src="{_b64(p, "image/png")}">' if slug and p.exists() else ''

    jl = _jugadores(local['slug'], local['startXI'], True)
    jv = _jugadores(visitante['slug'], visitante['startXI'], False)

    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{width:%dpx;height:%dpx;font-family:'Barlow Condensed',sans-serif;
     background:linear-gradient(150deg,#10182e,#0a0f1e);color:#fff;padding:18px 20px;
     display:flex;flex-direction:column}
.hdr{display:flex;align-items:center;gap:14px;margin-bottom:12px}
.lado{display:flex;align-items:center;gap:11px;flex:1;min-width:0}
.lado.der{justify-content:flex-end}
.esc{width:44px;height:44px;object-fit:contain;flex:0 0 auto}
.nm{font-family:'Bebas Neue';font-size:31px;letter-spacing:2px;white-space:nowrap}
.form{font-family:'Bebas Neue';font-size:20px;letter-spacing:2px;color:#8b93a7}
.vs{font-family:'Bebas Neue';font-size:23px;letter-spacing:3px;color:#5d6479;padding:0 4px}
#pitch{position:relative;flex:1;border-radius:14px;overflow:hidden;
  background:repeating-linear-gradient(90deg, rgba(255,255,255,.045) 0 62px, transparent 62px 124px),
             linear-gradient(160deg,#12492a,#0a2f1a)}
.l{position:absolute;box-sizing:border-box;border:2px solid rgba(255,255,255,.30)}
.jug{position:absolute;transform:translate(-50%%,-50%%);display:flex;flex-direction:column;
     align-items:center;gap:4px}
.chip{width:46px;height:46px;border-radius:50%%;border:2.5px solid rgba(255,255,255,.92);
      box-shadow:0 2px 6px rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center}
.chip span{font-family:'Bebas Neue';font-size:20px;color:#fff;
  text-shadow:-1px -1px 0 rgba(0,0,0,.55),1px -1px 0 rgba(0,0,0,.55),-1px 1px 0 rgba(0,0,0,.55),1px 1px 0 rgba(0,0,0,.55)}
.tag{font-size:12.5px;font-weight:600;background:rgba(10,15,30,.88);
     border:1px solid rgba(255,255,255,.25);padding:2px 8px;border-radius:11px;white-space:nowrap}
.foot{text-align:right;font-size:12px;color:#5d6479;margin-top:9px}
</style></head><body>
<div class="hdr">
  <div class="lado">%s<div class="nm">%s</div><div class="form">%s</div></div>
  <div class="vs">VS</div>
  <div class="lado der"><div class="form">%s</div><div class="nm">%s</div>%s</div>
</div>
<div id="pitch">
  <div class="l" style="inset:10px;border-radius:8px"></div>
  <div class="l" style="top:10px;bottom:10px;left:50%%;width:0;border-width:0 0 0 2px"></div>
  <div class="l" style="left:50%%;top:50%%;width:130px;height:130px;margin:-65px 0 0 -65px;border-radius:50%%"></div>
  <div class="l" style="top:22%%;bottom:22%%;left:10px;width:11%%;border-left:none"></div>
  <div class="l" style="top:36%%;bottom:36%%;left:10px;width:4.5%%;border-left:none"></div>
  <div class="l" style="top:22%%;bottom:22%%;right:10px;width:11%%;border-right:none"></div>
  <div class="l" style="top:36%%;bottom:36%%;right:10px;width:4.5%%;border-right:none"></div>
</div>
<div class="foot">tribunapp.com.ar</div>
<script>%s</script><script>%s</script>
<script>
const EQ = %s;
const pitch = document.getElementById('pitch');
EQ.forEach(eq => {
  const kit = (typeof clubKit === 'function' && eq.slug) ? clubKit(eq.slug) : { type:'solid', colors:['#39445c'] };
  eq.jug.forEach(j => {
    const d = document.createElement('div');
    d.className = 'jug'; d.style.left = j.x + '%%'; d.style.top = j.y + '%%';
    const c = document.createElement('div');
    c.className = 'chip'; c.style.background = kitBackground(kit, 46);
    const n = document.createElement('span'); n.textContent = j.num; c.appendChild(n);
    const t = document.createElement('div'); t.className = 'tag'; t.textContent = j.nombre;
    d.appendChild(c); d.appendChild(t); pitch.appendChild(d);
  });
});
</script></body></html>""" % (
        ff, ANCHO, ALTO,
        esc_tag(local['slug'], 'esc'), (NOM.get(local['slug']) or local['nombre']).upper(),
        local.get('formacion') or '',
        visitante.get('formacion') or '',
        (NOM.get(visitante['slug']) or visitante['nombre']).upper(),
        esc_tag(visitante['slug'], 'esc'),
        kits_js, colors_js,
        json.dumps([{'slug': local['slug'], 'jug': jl},
                    {'slug': visitante['slug'], 'jug': jv}], ensure_ascii=False))


def generar(local, visitante, outdir=PREVIEW) -> Path:
    from playwright.sync_api import sync_playwright
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    Path(outdir).mkdir(parents=True, exist_ok=True)
    path = Path(outdir) / f"xi-{local['slug']}-{visitante['slug']}.png"
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': ANCHO, 'height': ALTO}, device_scale_factor=2)
        pg.set_content(_html(local, visitante))
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(path))
        b.close()
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--lineups', required=True,
                    help='JSON con [{slug, nombre, formacion, startXI}, ...] (local, visitante)')
    ap.add_argument('--out', default=str(PREVIEW))
    args = ap.parse_args()
    eq = json.loads(Path(args.lineups).read_text(encoding='utf-8'))
    print('imagen:', generar(eq[0], eq[1], args.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
