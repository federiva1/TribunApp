#!/usr/bin/env python3
"""Placa de las DOS formaciones enfrentadas en una cancha apaisada.

Alternativa a las dos placas verticales de social_lineups (una por equipo): los
22 en una sola imagen. La cancha la dibuja **js/ficha-cancha.js**, el mismo
módulo que la ficha del partido en el index — así la placa y la web se ven
igual y no hay dos dibujos que mantener.

    python scripts/social_xi_cruce.py --lineups partido.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from social_lineups import NOM, _b64, _elegir, _plantel_por_num   # noqa: E402
from social_resultado import _logo_datauri                        # noqa: E402

PREVIEW = ROOT / 'data' / 'social' / 'preview'
ANCHO, ALTO = 1000, 760
KIT_PX = 46          # diámetro del kit chip en la placa (en la web son 24)


def _jugadores(slug, startxi):
    """startXI de api-sports → jugadores del schema data/partidos (lo que come
    fcCanchaHTML): nombre completo del plantel, dorsal, tipo y grid."""
    plantel = _plantel_por_num(slug) if slug else {}
    out = []
    for j in startxi:
        pl = j.get('player') or {}
        num = str(pl.get('number') or '')
        api_nom = pl.get('name') or ''
        del_plantel = _elegir(plantel.get(num) or [], api_nom)
        nombre = (del_plantel or api_nom) if '.' in api_nom else (api_nom or del_plantel)
        out.append({'nombre': nombre, 'num': num, 'tipo': 'titular',
                    'grid': pl.get('grid') or ''})
    return out


def _html(local, visitante, subtitulo=''):
    """local/visitante: dict {slug, nombre, formacion, startXI}."""
    payload = {
        'partido': {
            'local': local['slug'], 'visitante': visitante['slug'],
            'local_nombre': local.get('nombre') or '', 'visitante_nombre': visitante.get('nombre') or '',
            'formacion': {local['slug']: local.get('formacion') or '',
                          visitante['slug']: visitante.get('formacion') or ''},
        },
        'jugadores': {local['slug']: _jugadores(local['slug'], local['startXI']),
                      visitante['slug']: _jugadores(visitante['slug'], visitante['startXI'])},
    }
    nombres = {s: (NOM.get(s) or n) for s, n in
               ((local['slug'], local.get('nombre')), (visitante['slug'], visitante.get('nombre')))}
    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))
    sub = f'<div class="sub">{subtitulo}</div>' if subtitulo else ''

    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{width:%dpx;height:%dpx;font-family:'Barlow Condensed',sans-serif;color:#fff;
     background:linear-gradient(150deg,#10182e,#0a0f1e);padding:26px 30px 20px;
     display:flex;flex-direction:column}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.logo{height:34px;width:auto}
.sub{font-family:'Bebas Neue';font-size:19px;letter-spacing:4px;color:#38bdf8}
#ficha{flex:1;display:flex;align-items:center}
/* La ficha del index está pensada para el ancho del celular; acá se agranda
   manteniendo las proporciones del módulo. */
.fc-h{max-width:100%% !important;width:100%%}
.fc-hdr img{width:30px !important;height:30px !important}
.fc-hdr .fc-nom{font-size:22px !important}
.fc-hdr .fc-form{font-size:18px !important}
.fc-h-hdr{margin-bottom:10px !important}
.fc-pitch-h{aspect-ratio:16/9.9 !important;border-radius:12px !important}
.fc-pitch-h .fc-nm{font-size:17px !important;padding:2px 9px !important;border-radius:9px !important;
                   font-weight:600}
.fc-pitch-h .fc-spot{gap:5px !important;width:15%% !important}
.fc-pitch-h .fc-kit{border-width:2.5px !important}
.foot{text-align:right;font-size:13px;color:#5d6479;margin-top:12px}
</style></head><body>
<div class="top"><img class="logo" src="%s">%s</div>
<div id="ficha"></div>
<div class="foot">tribunapp.com.ar</div>
<script src="js/kits.js"></script>
<script src="js/club-colors.js"></script>
<script src="js/ficha-cancha.js"></script>
<script>
const DATA = %s, NOMBRES = %s, KIT_PX = %d;
document.getElementById('ficha').innerHTML =
  fcCanchaHTML(DATA, { nomFn: (slug, nom) => NOMBRES[slug] || nom || slug, layout: 'horizontal' })
  || '<div style="color:#f88">Faltan posiciones (grid) en el XI</div>';
// La ficha dibuja chips de 24px (medida del celular) y el patrón del kit se
// genera para ESE tamaño, así que agrandarlos por CSS deformaría los bastones:
// se regeneran con el tamaño de la placa. El lado sale de la mitad de la cancha.
document.querySelectorAll('.fc-pitch-h .fc-spot').forEach(sp => {
  const x = parseFloat(sp.style.left);
  const esLocal = x < 50;
  const slug = esLocal ? DATA.partido.local : DATA.partido.visitante;
  // Con los chips grandes, las líneas más adelantadas de los dos equipos se
  // tocaban en el círculo central: se comprime la profundidad hacia el arco
  // propio para abrir el pasillo del medio.
  const dist = esLocal ? x - 6 : 94 - x;
  sp.style.left = (esLocal ? 8 + dist * 0.85 : 92 - dist * 0.85) + '%%';
  const chip = sp.querySelector('.fc-kit');
  if (!chip) return;
  chip.style.width = chip.style.height = KIT_PX + 'px';
  chip.style.background = kitBackground(clubKit(slug), KIT_PX);
  const n = chip.querySelector('span');
  if (n) n.style.fontSize = Math.round(KIT_PX * 0.44) + 'px';
});
</script></body></html>""" % (ff, ANCHO, ALTO, _logo_datauri(), sub,
                              json.dumps(payload, ensure_ascii=False),
                              json.dumps(nombres, ensure_ascii=False), KIT_PX)


def generar(local, visitante, subtitulo='', outdir=PREVIEW) -> Path:
    from playwright.sync_api import sync_playwright
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    Path(outdir).mkdir(parents=True, exist_ok=True)
    path = Path(outdir) / f"xi-{local['slug']}-{visitante['slug']}.png"
    # El HTML se escribe DENTRO del repo y se abre con file:// para que resuelvan
    # los paths relativos de js/ y escudos/ (con set_content no cargarían).
    tmp = tempfile.NamedTemporaryFile('w', suffix='.html', dir=ROOT, delete=False,
                                      encoding='utf-8')
    try:
        tmp.write(_html(local, visitante, subtitulo))
        tmp.close()
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
            pg = b.new_page(viewport={'width': ANCHO, 'height': ALTO}, device_scale_factor=2)
            pg.goto('file://' + tmp.name)
            pg.wait_for_timeout(900)
            pg.screenshot(path=str(path))
            b.close()
    finally:
        os.unlink(tmp.name)
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--lineups', required=True,
                    help='JSON con [{slug, nombre, formacion, startXI}, ...] (local, visitante)')
    ap.add_argument('--sub', default='', help='subtítulo (ej. "FECHA 7 · 19:00")')
    ap.add_argument('--out', default=str(PREVIEW))
    args = ap.parse_args()
    eq = json.loads(Path(args.lineups).read_text(encoding='utf-8'))
    print('imagen:', generar(eq[0], eq[1], args.sub.upper(), args.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
