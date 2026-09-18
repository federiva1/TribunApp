"""Placa comparativa de un club entre dos bloques de fechas del torneo:
goles, remates, remates al arco, toques en área rival y pases al último tercio.

Uso:
  python scripts/social_comparativa.py --club argentinosjuniors --bloques 1-4,5-8
  python scripts/social_comparativa.py --club argentinosjuniors --bloques 1-4,5-8 \
      --excluir estudiantesderiocuarto,aldosivi --sub "SIN ESTUDIANTES RC NI ALDOSIVI"

Fuente: data/partidos/{id}.json (FotMob). Remates, remates al arco y toques en
área salen de top_stats del partido; los pases al último tercio no vienen a
nivel equipo, se suman los de cada jugador. Sale en data/social/preview/.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / 'data' / 'social' / 'preview'
sys.path.insert(0, str(ROOT / 'scripts'))
from social_lineups import NOM, _b64, esc_placa   # noqa: E402
from social_resultado import _logo_datauri        # noqa: E402

STATS = [('goles', 'GOLES'), ('tiros', 'REMATES'), ('arco', 'REMATES AL ARCO'),
         ('area', 'TOQUES EN ÁREA RIVAL'), ('ut', 'PASES AL ÚLTIMO TERCIO')]


def partidos_club(slug, torneo='Clausura'):
    idx = json.loads((ROOT / 'data' / 'partidos' / 'index.json').read_text(encoding='utf-8'))
    out = []
    for e in idx:
        if slug not in (e['local'], e['visitante']):
            continue
        d = json.loads((ROOT / 'data' / 'partidos' / f"{e['id']}.json").read_text(encoding='utf-8'))
        p = d['partido']
        if torneo.lower() not in (p.get('competicion') or '').lower() or not p.get('fecha_num'):
            continue
        local = p['local'] == slug
        side = 'local' if local else 'visitante'
        ts = {t['label']: t[side] for t in d.get('top_stats') or []}
        js = d['jugadores'].get(slug) or []
        out.append({
            'fecha': int(p['fecha_num']), 'dia': p['fecha'], 'local': local,
            'rival': p['visitante'] if local else p['local'],
            'gf': p['goles_local'] if local else p['goles_visitante'],
            'gc': p['goles_visitante'] if local else p['goles_local'],
            'goles': p['goles_local'] if local else p['goles_visitante'],
            'tiros': ts.get('Tiros totales') or 0,
            'arco': ts.get('Tiros al arco') or 0,
            'area': ts.get('Toques en area rival') or 0,
            'ut': sum((x.get('ataque') or {}).get('pases_ultimo_tercio') or 0 for x in js),
        })
    return sorted(out, key=lambda m: m['dia'])


def _rango(txt):
    a, b = txt.split('-')
    return set(range(int(a), int(b) + 1))


def _titulo_bloque(fechas):
    fs = sorted(fechas)
    if fs == list(range(fs[0], fs[-1] + 1)):
        return f'FECHAS {fs[0]}-{fs[-1]}'
    return 'FECHAS ' + '·'.join(map(str, fs))


def _lista(ms):
    return ' · '.join(f"{NOM.get(m['rival'], m['rival'])} {m['gf']}-{m['gc']}" for m in ms)


def _fila(k, lab, ma, mb):
    va, vb = sum(m[k] for m in ma), sum(m[k] for m in mb)
    mx = max(va, vb, 1)
    pa = f"{va / len(ma):.1f}" if ma else '-'
    pb = f"{vb / len(mb):.1f}" if mb else '-'
    ca = 'win' if va > vb else ('lose' if va < vb else 'tie')
    cb = 'win' if vb > va else ('lose' if vb < va else 'tie')
    return (
        '<div class="fila">'
        f'<div class="lado izq {ca}"><div class="val">{va}</div><div class="prom">{pa} por partido</div>'
        f'<div class="bar"><i style="width:{va / mx * 100:.0f}%"></i></div></div>'
        f'<div class="lab">{lab}</div>'
        f'<div class="lado der {cb}"><div class="val">{vb}</div><div class="prom">{pb} por partido</div>'
        f'<div class="bar"><i style="width:{vb / mx * 100:.0f}%"></i></div></div>'
        '</div>')


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:760px;height:950px;font-family:'Barlow Condensed',sans-serif;color:#fff;position:relative;overflow:hidden;
  background:radial-gradient(90% 55% at 50% -10%, rgba(28,58,110,.35), transparent 62%),
             radial-gradient(120% 60% at 50% 115%, rgba(56,140,220,.22), transparent 68%),
             linear-gradient(180deg,#080c17 0%,#0a1122 55%,#070b16 100%);}
.wrap{position:relative;height:100%;padding:30px 34px 24px;display:flex;flex-direction:column}
.logo{height:38px;width:auto;align-self:flex-start}
.tit-box{text-align:center;margin:14px 0 0}
.torneo{font-family:'Bebas Neue';font-size:19px;letter-spacing:5px;color:#38bdf8;margin-bottom:5px}
.tit{font-family:'Bebas Neue';font-size:44px;letter-spacing:8px;line-height:1}
.sub{font-family:'Bebas Neue';font-size:18px;letter-spacing:4px;color:#8b93a7;margin-top:7px;min-height:18px}
.esc{width:96px;height:96px;object-fit:contain;display:block;margin:14px auto 0;filter:drop-shadow(0 8px 20px rgba(0,0,0,.6))}
.cabs{display:flex;justify-content:space-between;margin-top:18px;gap:16px}
.cab{width:50%}
.cab h3{font-family:'Bebas Neue';font-size:30px;letter-spacing:3px;line-height:1}
.cab p{font-size:14px;color:#8b93a7;margin-top:5px;line-height:1.25;font-weight:600;letter-spacing:.3px}
.cab.der{text-align:right}
.tabla{flex:1;display:flex;flex-direction:column;justify-content:space-evenly;margin-top:6px}
.fila{display:flex;align-items:center;gap:14px;padding:6px 0;border-top:1px solid rgba(255,255,255,.07)}
.lab{width:190px;text-align:center;font-family:'Bebas Neue';font-size:20px;letter-spacing:2.5px;color:#e8edf7;line-height:1.05}
.lado{flex:1}
.lado.der{text-align:right}
.val{font-family:'Bebas Neue';font-size:52px;line-height:1;color:#8b93a7}
.win .val{color:#38bdf8}
.tie .val{color:#e8edf7}
.prom{font-size:13px;color:#5d6479;letter-spacing:.5px;margin-top:2px;font-weight:600;text-transform:uppercase}
.bar{height:6px;border-radius:3px;background:rgba(255,255,255,.06);margin-top:8px;overflow:hidden}
.der .bar{transform:scaleX(-1)}
.bar i{display:block;height:100%;border-radius:3px;background:#3b4560}
.win .bar i{background:#38bdf8}
.tie .bar i{background:#8b93a7}
.pie{text-align:center;font-family:'Bebas Neue';font-size:17px;letter-spacing:3px;color:#8b93a7;margin-top:8px}
.pie b{color:#38bdf8;font-weight:400}
"""


def _html(slug, bloques, titulo, sub):
    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))
    (fa, ma), (fb, mb) = bloques
    filas = ''.join(_fila(k, lab, ma, mb) for k, lab in STATS)
    esc = _b64(esc_placa(slug), 'image/png')
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><style>' + ff + CSS + '</style></head><body>'
        '<div class="wrap">'
        f'<img class="logo" src="{_logo_datauri()}">'
        f'<div class="tit-box"><div class="torneo">{NOM.get(slug, slug).upper()} · CLAUSURA 2026</div>'
        f'<div class="tit">{titulo}</div><div class="sub">{sub}</div></div>'
        f'<img class="esc" src="{esc}">'
        '<div class="cabs">'
        f'<div class="cab izq"><h3>{_titulo_bloque(fa)}</h3><p>{_lista(ma)}</p></div>'
        f'<div class="cab der"><h3>{_titulo_bloque(fb)}</h3><p>{_lista(mb)}</p></div>'
        '</div>'
        f'<div class="tabla">{filas}</div>'
        '<div class="pie">DATOS FOTMOB · MÁS ESTADÍSTICAS EN <b>TRIBUNAPP.COM.AR</b></div>'
        '</div></body></html>')


def render(html, out):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 760, 'height': 950}, device_scale_factor=2)
        pg.set_content(html, wait_until='load')
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(out))
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--club', required=True)
    ap.add_argument('--bloques', default='1-4,5-8', help='dos rangos de fecha, ej. 1-4,5-8')
    ap.add_argument('--excluir', default='', help='slugs de rivales a dejar afuera, separados por coma')
    ap.add_argument('--titulo', default='PRIMEROS 4 VS ÚLTIMOS 4')
    ap.add_argument('--sub', default='')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    excl = {s.strip() for s in a.excluir.split(',') if s.strip()}
    ms = [m for m in partidos_club(a.club) if m['rival'] not in excl]
    bloques = []
    for r in a.bloques.split(','):
        fs = _rango(r)
        sel = [m for m in ms if m['fecha'] in fs]
        bloques.append(({m['fecha'] for m in sel}, sel))
    for fs, sel in bloques:
        print(_titulo_bloque(fs), '|', _lista(sel))
        for k, lab in STATS:
            print(f'   {lab:<24}', sum(m[k] for m in sel))
    PREVIEW.mkdir(parents=True, exist_ok=True)
    suf = ('-sin-' + '-'.join(sorted(excl))) if excl else ''
    out = PREVIEW / (a.out or f'comparativa-{a.club}{suf}.png')
    render(_html(a.club, bloques, a.titulo, a.sub), out)
    print('imagen:', out)


if __name__ == '__main__':
    main()
