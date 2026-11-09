"""Placas de los playoffs del torneo local.

CUADRO (default): placa apaisada 16:9 con las llaves, como el cuadro del inicio: las dos
mitades de octavos convergen en la final, cada llave con los dos equipos uno arriba del
otro. Las rondas siguientes se completan solas con los ganadores que ya estén en liga.json
(con marcador y penales); lo que falta queda "A definir".

LISTA (--lista): misma estética que las placas de la fecha (social_fecha): logo, torneo en celeste,
título grande y una tarjeta por cruce con escudos, nombres y la posición de cada
uno en su zona. Las tarjetas van en el orden del cuadro y de a pares: los dos
cruces de cada par se enfrentan en la instancia siguiente.

De dónde salen los cruces:
  - si liga.json ya trae los partidos de esa instancia (campo `fase`, ver
    fetch_liga_fixtures.fecha_y_fase), de ahí, con día y hora;
  - si no, y es octavos, se arman con la tabla final de api-sports con el formato
    del torneo (el mismo PL_OCTAVOS del cuadro de index.html).

Uso:
  python scripts/social_cruces.py --sub "OCTAVOS 21 Y 22/11 · FINAL 12/12"   # cuadro (1280x720 x2)
  python scripts/social_cruces.py --lista --sub "21 Y 22 DE NOVIEMBRE"      # lista de octavos
  python scripts/social_cruces.py --lista --fase cuartos

Sale en data/social/preview/cuadro-playoffs.png / cruces-{fase}.png (gitignored): no publica nada.
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


# Trofeo de la LPF: la misma silueta que _plTrofeo() del cuadro de index.html.
TROFEO = (
    '<svg viewBox="0 0 120 194" fill="url(#tg)"><defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#eef0f4"/><stop offset="1" stop-color="#aeb4bf"/></linearGradient></defs>'
    '<circle cx="60" cy="20" r="13"/>'
    '<path d="M60.00 15.40 L64.37 18.58 L62.70 23.72 L57.30 23.72 L55.63 18.58 Z M60.00 15.40 L60.00 11.40 '
    'M60.00 11.40 L54.30 8.32 M60.00 11.40 L65.70 8.32 M64.37 18.58 L68.18 17.34 M68.18 17.34 L69.35 10.97 '
    'M68.18 17.34 L72.87 21.81 M62.70 23.72 L65.05 26.96 M65.05 26.96 L71.48 26.10 M65.05 26.96 L62.26 32.80 '
    'M57.30 23.72 L54.95 26.96 M54.95 26.96 L57.74 32.80 M54.95 26.96 L48.52 26.10 M55.63 18.58 L51.82 17.34 '
    'M51.82 17.34 L47.13 21.81 M51.82 17.34 L50.65 10.97" fill="none" stroke="#0d0d1a" stroke-opacity=".45" '
    'stroke-width=".9" stroke-linejoin="round"/>'
    '<path d="M50 33 H70 L73 41 H47 Z"/><rect x="41" y="41" width="38" height="4" rx="2"/>'
    '<rect x="46" y="46" width="28" height="5" rx="1"/>'
    '<path d="M44 51 C36 53 32 58 32 67 C32 93 44 122 52 142 L48 151 H72 L68 142 C76 122 88 93 88 67 '
    'C88 58 84 53 76 51 Z"/>'
    '<path d="M50 131 C27 120 7 101 8 72 C8.5 56 11 45 14.2 36.8 C15.6 35.4 18.4 35.6 19.4 37.2 C17 47 14 58 14 72 '
    'C14 97 31 114 51 122 Z"/><path d="M 70 131 C 93 120 113 101 112 72 C 111.5 56 109 45 105.8 36.8 '
    'C 104.4 35.4 101.6 35.6 100.6 37.2 C 103 47 106 58 106 72 C 106 97 89 114 69 122 Z"/>'
    '<path d="M36 58 C29 54 21 52 12 52 L12 55.5 C21 55.5 28 57.5 34 62 Z"/>'
    '<path d="M 84 58 C 91 54 99 52 108 52 L 108 55.5 C 99 55.5 92 57.5 86 62 Z"/>'
    '<rect x="38" y="153" width="44" height="40" rx="2"/></svg>')


def _fuentes():
    return ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))


def armar_cuadro(octavos):
    """octavos: 8 cruces en orden de cuadro. Devuelve {'o1'..'o8','q1'..'q4','s1','s2','f'}
    con {home, away, sh, sa, hs, as, hp, ap, ganador} completando cada ronda con los
    ganadores de la anterior y los resultados de liga.json."""
    liga = json.loads((ROOT / 'data' / 'fixtures' / 'liga.json').read_text(encoding='utf-8'))
    jugados = {}
    for p in liga:
        if p.get('fase'):
            jugados[frozenset((p['home']['slug'], p['away']['slug']))] = p

    def con_resultado(c):
        p = jugados.get(frozenset((c.get('home'), c.get('away'))))
        if p and (p.get('status') or {}).get('finished'):
            local = p['home']['slug'] == c['home']
            c['hs'], c['as'] = (p['home_score'], p['away_score']) if local else (p['away_score'], p['home_score'])
            c['hp'], c['ap'] = (p.get('home_pen'), p.get('away_pen')) if local else (p.get('away_pen'), p.get('home_pen'))
            g = p.get('winner')
            if not g and c['hs'] is not None and c['hs'] != c['as']:
                g = c['home'] if c['hs'] > c['as'] else c['away']
            c['ganador'] = g
        return c

    nodos = {f'o{i + 1}': con_resultado(dict(c)) for i, c in enumerate(octavos)}
    for nuevo, (a, b) in (('q1', ('o1', 'o2')), ('q2', ('o3', 'o4')), ('q3', ('o5', 'o6')), ('q4', ('o7', 'o8')),
                          ('s1', ('q1', 'q2')), ('s2', ('q3', 'q4')), ('f', ('s1', 's2'))):
        ga, gb = nodos[a].get('ganador'), nodos[b].get('ganador')
        sd = {nodos[a].get('home'): nodos[a].get('sh'), nodos[a].get('away'): nodos[a].get('sa'),
              nodos[b].get('home'): nodos[b].get('sh'), nodos[b].get('away'): nodos[b].get('sa')}
        nodos[nuevo] = con_resultado({'home': ga, 'away': gb, 'sh': sd.get(ga), 'sa': sd.get(gb)}) if ga and gb \
            else {'home': ga, 'away': gb, 'sh': sd.get(ga), 'sa': sd.get(gb)}
    return nodos


def _html_cuadro(nodos, sub):
    """Cuadro apaisado 1280x720: octavos | cuartos | semis | FINAL | semis | cuartos | octavos."""
    W_, TOP, ALTO = 1280, 168, 520            # zona de llaves: de y=168 a y=688
    FILA = 30                                 # alto de cada equipo dentro de la llave
    cols = {  # x izquierda y ancho de cada columna
        'o_i': (14, 178), 'q_i': (214, 156), 's_i': (392, 150), 'f': (555, 170),
        's_d': (738, 150), 'q_d': (910, 156), 'o_d': (1088, 178)}

    def cy(n, k):          # centro vertical de la llave k (0..n-1) en una columna con n llaves
        return TOP + ALTO * (2 * k + 1) / (2 * n)

    pos = {}
    for k in range(4):
        pos[f'o{k + 1}'] = ('o_i', cy(4, k)); pos[f'o{k + 5}'] = ('o_d', cy(4, k))
    for k in range(2):
        pos[f'q{k + 1}'] = ('q_i', cy(2, k)); pos[f'q{k + 3}'] = ('q_d', cy(2, k))
    pos['s1'] = ('s_i', cy(1, 0)); pos['s2'] = ('s_d', cy(1, 0)); pos['f'] = ('f', cy(1, 0))

    def esc(slug):
        p = esc_placa(slug) if slug else None
        return f'<img class="e" src="{_b64(p, "image/png")}">' if p and p.exists() else '<span class="e"></span>'

    def fila(slug, seed, goles, pen, gano, perdio):
        if not slug:
            return '<div class="f vacia"><span class="e"></span><span class="n">A DEFINIR</span></div>'
        g = '' if goles is None else (f'{goles}' + (f'<i>({pen})</i>' if pen is not None else ''))
        cls = ' gano' if gano else (' perdio' if perdio else '')
        sd = f'<span class="s">{seed[1]}{seed[0]}</span>' if seed else ''
        return (f'<div class="f{cls}">{sd}{esc(slug)}<span class="n">{NOM.get(slug, slug).upper()}</span>'
                f'<span class="g">{g}</span></div>')

    html_nodos, lineas = [], []
    for nid, (col, y) in pos.items():
        x, w = cols[col]
        c = nodos[nid]
        gan = c.get('ganador')
        cuerpo = (fila(c.get('home'), c.get('sh'), c.get('hs'), c.get('hp'), gan and gan == c.get('home'), gan and gan != c.get('home'))
                  + fila(c.get('away'), c.get('sa'), c.get('as'), c.get('ap'), gan and gan == c.get('away'), gan and gan != c.get('away')))
        extra = ' fin' if nid == 'f' else ''
        html_nodos.append(f'<div class="nodo{extra}" style="left:{x}px;top:{y - FILA:.0f}px;width:{w}px">{cuerpo}</div>')

    # conectores: de cada par de llaves a la llave siguiente (codo en el medio del hueco)
    def conectar(a, b, dest):
        ca, ya = pos[a]; cb, yb = pos[b]; cd, yd = pos[dest]
        xa, wa = cols[ca]; xd, wd = cols[cd]
        izq = xd > xa
        x0 = xa + wa if izq else xa                 # borde de salida de las llaves de origen
        x1 = xd if izq else xd + wd                 # borde de entrada de la llave destino
        xm = (x0 + x1) / 2
        for y in (ya, yb):
            lineas.append(f'M{x0} {y:.0f} H{xm:.0f}')
        lineas.append(f'M{xm:.0f} {ya:.0f} V{yb:.0f} M{xm:.0f} {yd:.0f} H{x1}')
    for a, b, d in (('o1', 'o2', 'q1'), ('o3', 'o4', 'q2'), ('o5', 'o6', 'q3'), ('o7', 'o8', 'q4'),
                    ('q1', 'q2', 's1'), ('q3', 'q4', 's2')):
        conectar(a, b, d)
    yf = pos['f'][1]
    lineas.append(f"M{cols['s_i'][0] + cols['s_i'][1]} {yf:.0f} H{cols['f'][0]}")
    lineas.append(f"M{cols['s_d'][0]} {yf:.0f} H{cols['f'][0] + cols['f'][1]}")

    rondas = ''.join(f'<div class="r" style="left:{cols[c][0]}px;width:{cols[c][1]}px">{t}</div>'
                     for c, t in (('o_i', 'OCTAVOS'), ('q_i', 'CUARTOS'), ('s_i', 'SEMIS'), ('f', 'FINAL'),
                                  ('s_d', 'SEMIS'), ('q_d', 'CUARTOS'), ('o_d', 'OCTAVOS')))
    campeon = nodos['f'].get('ganador')
    fx, fw = cols['f']
    corona = (f'<div class="campeon" style="left:{fx}px;width:{fw}px;top:{yf - 108:.0f}px">'
              f'<div class="ct">CAMPEÓN</div>{esc(campeon) if campeon else ""}</div>')
    trofeo = f'<div class="trofeo{" ok" if campeon else ""}" style="left:{fx + fw / 2 - 38:.0f}px;top:{yf + 50:.0f}px">{TROFEO}</div>'
    fondo = ROOT / 'img' / 'portada-estadio.jpg'
    bg_img = f",url({_b64(fondo, 'image/jpeg')}) center 58% / cover no-repeat" if fondo.exists() else ''

    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{width:%dpx;height:720px;font-family:'Barlow Condensed',sans-serif;color:#fff;position:relative;overflow:hidden;
  background:linear-gradient(180deg,rgba(8,12,23,.97) 0%%,rgba(8,12,23,.86) 45%%,rgba(8,12,23,.93) 100%%)%s,#080c17}
.logo{position:absolute;left:24px;top:22px;height:32px}
.url{position:absolute;right:24px;top:30px;font-family:'Bebas Neue';font-size:18px;letter-spacing:3px;color:#38bdf8}
.cab{position:absolute;left:0;right:0;top:20px;text-align:center}
.torneo{font-family:'Bebas Neue';font-size:16px;letter-spacing:5px;color:#38bdf8}
.tit{font-family:'Bebas Neue';font-size:38px;letter-spacing:8px;line-height:1.05}
.sub{font-family:'Bebas Neue';font-size:16px;letter-spacing:3px;color:#8b93a7;margin-top:3px}
.r{position:absolute;top:140px;text-align:center;font-family:'Bebas Neue';font-size:14px;letter-spacing:3px;color:#5d6479}
svg.lin{position:absolute;inset:0;width:%dpx;height:720px}
.nodo{position:absolute;border:1px solid rgba(255,255,255,.16);border-radius:9px;background:rgba(13,20,36,.92);overflow:hidden}
.nodo.fin{border-color:rgba(56,189,248,.7);box-shadow:0 0 18px rgba(56,189,248,.25)}
.f{height:30px;display:flex;align-items:center;gap:6px;padding:0 8px}
.f+.f{border-top:1px solid rgba(255,255,255,.08)}
.f .s{font-family:'Bebas Neue';font-size:12px;letter-spacing:1px;color:#38bdf8;width:17px;flex:0 0 auto}
.f .e{width:22px;height:22px;object-fit:contain;flex:0 0 auto}
.f .n{font-family:'Bebas Neue';font-size:16.5px;letter-spacing:1.2px;white-space:nowrap;overflow:hidden;flex:1}
.f .g{font-family:'Bebas Neue';font-size:17px;color:#fff;min-width:12px;text-align:right}
.f .g i{font-style:normal;font-size:12px;color:#8b93a7;margin-left:2px}
.f.vacia .n{color:#3c4560;font-size:14px;letter-spacing:2px}
.f.perdio{opacity:.4}
.f.gano .n{color:#fff}
.campeon{position:absolute;text-align:center}
.campeon .ct{font-family:'Bebas Neue';font-size:20px;letter-spacing:6px;color:#f5c542}
.campeon .e{width:44px;height:44px;object-fit:contain;margin-top:4px}
.trofeo{position:absolute;width:76px;opacity:.55}
.trofeo.ok{opacity:1;filter:drop-shadow(0 0 14px rgba(245,197,66,.5))}
.trofeo svg{width:76px;height:auto;display:block}
</style></head><body>
<img class="logo" src="%s"><div class="url">TRIBUNAPP.COM.AR</div>
<div class="cab"><div class="torneo">TORNEO CLAUSURA 2026</div><div class="tit">CUADRO DE PLAYOFFS</div>%s</div>
%s
<svg class="lin" viewBox="0 0 %d 720"><path d="%s" fill="none" stroke="rgba(56,189,248,.55)" stroke-width="2"/></svg>
%s%s%s
</body></html>""" % (_fuentes(), W_, bg_img, W_, _logo_datauri(),
                      f'<div class="sub">{sub}</div>' if sub else '', rondas, W_, ' '.join(lineas),
                      ''.join(html_nodos), corona, trofeo)


def generar_cuadro(nodos, sub, path, escala=2):
    from playwright.sync_api import sync_playwright
    import os
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 1280, 'height': 720}, device_scale_factor=escala)
        pg.set_content(_html_cuadro(nodos, sub))
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(path))
        b.close()
    return path


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
    ap.add_argument('--lista', action='store_true',
                    help='lista de cruces de una instancia en vez del cuadro completo')
    ap.add_argument('--fase', default='octavos', choices=list(FASES), help='(con --lista) instancia')
    ap.add_argument('--sub', default='', help='línea debajo del título (ej. "21 Y 22 DE NOVIEMBRE")')
    ap.add_argument('--escala', type=int, default=2)
    ap.add_argument('--out', default=str(PREVIEW))
    args = ap.parse_args()
    sufijo = '' if args.escala == 2 else f'-x{args.escala}'
    if not args.lista:
        seeds = seeds_de_la_tabla()
        pos = {v: k for k, v in seeds.items()}
        octavos = [{'home': seeds[a], 'away': seeds[b], 'sh': a, 'sa': b} for a, b in PL_OCTAVOS]
        nodos = armar_cuadro(octavos)
        for k in ('o1', 'o2', 'o3', 'o4', 'o5', 'o6', 'o7', 'o8'):
            c = nodos[k]
            print(f"  {k}: {c['home']} ({c['sh']}) vs {c['away']} ({c['sa']})"
                  + (f"  {c['hs']}-{c['as']}" if c.get('hs') is not None else ''))
        print('imagen:', generar_cuadro(nodos, args.sub.upper(), Path(args.out) / f'cuadro-playoffs{sufijo}.png',
                                        escala=args.escala))
        return 0
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
    print('imagen:', generar(cruces, titulo, args.sub.upper(), Path(args.out) / f'cruces-{args.fase}{sufijo}.png',
                             escala=args.escala))
    return 0


if __name__ == '__main__':
    sys.exit(main())
