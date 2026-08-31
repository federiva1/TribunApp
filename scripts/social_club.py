#!/usr/bin/env python3
"""Placa individual de un club: escudo grande + nombre + su URL amigable.

Misma identidad que las placas de partido (fondo de tribuna, escudos con
estrellas de escudos/placas, tipografías embebidas), pero de un solo club —
para presentar la sección del equipo en redes.

    python scripts/social_club.py bocajuniors
    python scripts/social_club.py river boca velez        # acepta el alias corto
    python scripts/social_club.py --all                   # los 30
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / 'data' / 'social' / 'preview'

sys.path.insert(0, str(ROOT / 'scripts'))
from social_lineups import NOM, _b64, esc_placa, aplicar_fondo_tribuna  # noqa: E402
from social_resultado import _logo_datauri                              # noqa: E402


def alias_por_slug() -> dict:
    """slug → alias corto de la URL amigable, leído de los rewrites de vercel.json
    (fuente única: si se agrega un club nuevo, la placa lo toma solo)."""
    out = {}
    try:
        cfg = json.loads((ROOT / 'vercel.json').read_text(encoding='utf-8'))
    except Exception:
        return out
    for r in cfg.get('rewrites', []):
        src, dst = r.get('source', ''), r.get('destination', '')
        if 'copa=' in dst:
            continue
        m_src = re.match(r'^/:alias\(([a-z]+)\|', src)
        m_dst = re.search(r'\?c=([a-z]+)$', dst)
        if m_src and m_dst:
            out[m_dst.group(1)] = m_src.group(1)
    return out


def _html(slug: str, nombre: str, alias: str) -> str:
    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))
    p = esc_placa(slug)
    escudo = f'<img class="esc" src="{_b64(p, "image/png")}">' if p.exists() else '<div class="esc"></div>'
    url = f'TRIBUNAPP.COM.AR/{alias.upper()}' if alias else 'TRIBUNAPP.COM.AR'

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
.hero{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px}
.esc{width:300px;height:300px;object-fit:contain;
     filter:drop-shadow(0 14px 34px rgba(0,0,0,.65))}
.nom{font-family:'Bebas Neue';font-size:64px;letter-spacing:5px;line-height:1;text-align:center;
     max-width:660px}
.claim{font-family:'Bebas Neue';font-size:23px;letter-spacing:4px;color:#8b93a7;text-align:center;
       line-height:1.35;max-width:600px}
.url{font-family:'Bebas Neue';font-size:34px;letter-spacing:4px;color:#38bdf8;
     border:2px solid rgba(56,189,248,.45);border-radius:10px;padding:9px 26px 6px}
</style></head><body>
<div class="bg"></div><div class="glow"></div>
<div class="wrap">
  <img class="logo" src="%s">
  <div class="hero">
    %s
    <div class="nom">%s</div>
    <div class="claim">ARMÁ TU FORMACIÓN IDEAL Y PUNTUÁ<br>A LOS JUGADORES FECHA A FECHA</div>
    <div class="url">%s</div>
  </div>
</div></body></html>""" % (ff, _logo_datauri(), escudo, nombre, url)


def generar(slug: str, nombre: str, alias: str, outdir) -> Path:
    from playwright.sync_api import sync_playwright
    import os
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    Path(outdir).mkdir(parents=True, exist_ok=True)
    path = Path(outdir) / f'club-{slug}.png'
    html = aplicar_fondo_tribuna(_html(slug, nombre, alias))
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 760, 'height': 950}, device_scale_factor=2)
        pg.set_content(html)
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(path))
        b.close()
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('clubes', nargs='*', help='slugs o alias cortos (river, boca…)')
    ap.add_argument('--all', action='store_true', help='los 30 clubes')
    ap.add_argument('--out', default=str(PREVIEW))
    args = ap.parse_args()

    alias = alias_por_slug()
    por_alias = {a: s for s, a in alias.items()}
    objetivo = list(alias) if args.all else [
        (c if c in alias else por_alias.get(c.lower(), c)) for c in args.clubes]
    if not objetivo:
        print('Indicá al menos un club (o --all)')
        return 1

    for slug in objetivo:
        nombre = (NOM.get(slug) or slug).upper()
        print(f'{slug:28} -> {generar(slug, nombre, alias.get(slug, ""), args.out)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
