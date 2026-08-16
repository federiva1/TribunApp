"""Placa + tweet de FINAL DEL PARTIDO (liga + copas), invitando a puntuar.

Flujo (workflow resultado-social.yml, cron cada 10 min):
  1. --check: ¿hay algún partido nuestro que arrancó hace entre 100 y 300 min y
     todavía no se posteó? Solo lee data/fixtures (sin API, sin dependencias).
  2. Sin --check: pregunta el estado a api-sports (fixtures?id=, que marca FT al
     toque, a diferencia de los agregados). Si terminó, arma la placa con el
     resultado + goleadores y tuitea invitando a puntuar.
  3. Sin credenciales de X corre en MODO ENSAYO: guarda la imagen en
     data/social/preview/ y marca el partido como posteado (dry).

Estado en data/social/resultados_posted.json (separado del de formaciones).

Test manual / sandbox (sin API, leyendo un partido ya generado):
  python scripts/social_resultado.py --test-partido sanlorenzo-union
"""
import argparse
import base64
import io
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXDIR = ROOT / 'data' / 'fixtures'
SOCIAL = ROOT / 'data' / 'social'
PREVIEW = SOCIAL / 'preview'
STATE = SOCIAL / 'resultados_posted.json'

VENTANA_DESDE = 100   # min desde el kickoff en que empezamos a mirar si terminó
VENTANA_HASTA = 300   # y hasta cuándo seguimos intentando

sys.path.insert(0, str(ROOT / 'scripts'))
from clubes_map import CLUBES  # noqa: E402
from social_lineups import NOM, hashtag, _cargar_partidos, _b64  # noqa: E402

FT = ('FT', 'AET', 'PEN')


def _estado():
    try:
        return json.loads(STATE.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def candidatos(ahora=None):
    """Partidos nuestros que ya deberían haber terminado y no se postearon."""
    ahora = ahora or datetime.now(timezone.utc)
    posted = _estado()
    out = []
    for m in _cargar_partidos(incluir_terminados=True):
        if m['api_id'] in posted:
            continue
        mins = (ahora - datetime.fromisoformat(m['utc'])).total_seconds() / 60
        if VENTANA_DESDE <= mins <= VENTANA_HASTA:
            out.append(m)
    return out


# ── datos del partido ────────────────────────────────────────────────────────
# api-sports devuelve los nombres sin tildes; los de uso frecuente los corregimos
# a mano (la clave es el nombre en minúsculas y sin acentos).
ACENTOS_ESTADIO = {
    'estadio jose maria minella': 'Estadio José María Minella',
    'estadio ciudad de vicente lopez': 'Estadio Ciudad de Vicente López',
    'estadio presidente juan domingo peron': 'Estadio Presidente Juan Domingo Perón',
    'estadio jose amalfitani': 'Estadio José Amalfitani',
    'estadio tomas adolfo duco': 'Estadio Tomás Adolfo Ducó',
    'estadio marcelo alberto bielsa': 'Estadio Marcelo Alberto Bielsa',
    'estadio ciudad de lanus - nestor diaz perez': 'Estadio Ciudad de Lanús',
    'estadio libertadores de america': 'Estadio Libertadores de América',
    'estadio mario alberto kempes': 'Estadio Mario Alberto Kempes',
    'estadio julio humberto grondona': 'Estadio Julio Humberto Grondona',
    'estadio 15 de abril': 'Estadio 15 de Abril',
    'estadio nuevo francisco urbano': 'Estadio Nuevo Francisco Urbano',
    'estadio bautista gargantini': 'Estadio Bautista Gargantini',
    'estadio eva peron': 'Estadio Eva Perón',
    'estadio brigadier general estanislao lopez': 'Estadio Brigadier General Estanislao López',
}


def _limpiar_estadio(nombre):
    """"Estadio Jose Maria Minella, Mar del Plata" → "ESTADIO JOSÉ MARÍA MINELLA"
    (se queda con el nombre, sin la ciudad; el acento lo pone api-sports o no)."""
    n = (nombre or '').split(',')[0].strip()
    if not n:
        return ''
    if not n.lower().startswith('estadio'):
        n = 'Estadio ' + n
    plano = unicodedata.normalize('NFD', n).encode('ascii', 'ignore').decode().lower()
    return ACENTOS_ESTADIO.get(plano, n).upper()


def _etiqueta_torneo(comp, fecha_num, ronda):
    c = (comp or '').lower()
    if 'libertadores' in c:
        return f'COPA LIBERTADORES · {ronda.upper()}' if ronda else 'COPA LIBERTADORES'
    if 'sudamericana' in c:
        return f'COPA SUDAMERICANA · {ronda.upper()}' if ronda else 'COPA SUDAMERICANA'
    return f'TORNEO LOCAL · FECHA {fecha_num}' if fecha_num else 'TORNEO LOCAL'


def payload_desde_json(pid):
    """Partido ya procesado en data/partidos/{id}.json (camino de test)."""
    d = json.loads((ROOT / 'data' / 'partidos' / f'{pid}.json').read_text(encoding='utf-8'))
    p = d['partido']
    goles = []
    for lado in ('local', 'visitante'):
        slug = p[lado]
        for g in (p.get('goles_detalle') or {}).get(lado) or []:
            nombre = g.get('jugador') or ''
            if g.get('en_contra'):
                nombre += ' (e/c)'
            elif g.get('penal'):
                nombre += ' (p)'
            goles.append({'min': g.get('min'), 'jugador': nombre, 'slug': slug})
    goles.sort(key=lambda g: g['min'] if g['min'] is not None else 999)
    return {
        'api_id': str(p.get('api_id') or ''),
        'home': {'slug': p['local'], 'name': p.get('local_nombre') or p['local'], 'goles': p['goles_local']},
        'away': {'slug': p['visitante'], 'name': p.get('visitante_nombre') or p['visitante'], 'goles': p['goles_visitante']},
        'estadio': _limpiar_estadio(p.get('estadio')),
        'torneo': _etiqueta_torneo(p.get('competicion'), p.get('fecha_num'), p.get('ronda')),
        'goles': goles,
        'comp': 'libertadores' if 'libertadores' in (p.get('competicion') or '').lower()
                else 'sudamericana' if 'sudamericana' in (p.get('competicion') or '').lower() else 'liga',
    }


def _api(path):
    from apikey import get_api_key
    req = urllib.request.Request('https://v3.football.api-sports.io/' + path,
                                 headers={'x-apisports-key': get_api_key()})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read()).get('response', [])


def payload_desde_api(match):
    """Estado real del partido: el endpoint por-id marca FT al instante."""
    resp = _api(f'fixtures?id={match["api_id"]}')
    if not resp:
        return None
    fx = resp[0]
    short = ((fx.get('fixture') or {}).get('status') or {}).get('short')
    if short not in FT:
        return None
    goals = fx.get('goals') or {}
    ids = {'home': ((fx.get('teams') or {}).get('home') or {}).get('id'),
           'away': ((fx.get('teams') or {}).get('away') or {}).get('id')}
    slug_por_id = {v.get('apisports'): k for k, v in CLUBES.items()}
    goles = []
    for ev in fx.get('events') or []:
        if (ev.get('type') or '') != 'Goal' or (ev.get('detail') or '') == 'Missed Penalty':
            continue
        t = (ev.get('time') or {})
        minuto = (t.get('elapsed') or 0) + (t.get('extra') or 0)
        tid = (ev.get('team') or {}).get('id')
        nombre = ((ev.get('player') or {}).get('name') or '')
        det = (ev.get('detail') or '')
        if det == 'Own Goal':
            nombre += ' (e/c)'
        elif det == 'Penalty':
            nombre += ' (p)'
        goles.append({'min': minuto, 'jugador': nombre, 'slug': slug_por_id.get(tid) or ''})
    goles.sort(key=lambda g: g['min'] if g['min'] is not None else 999)
    ronda = ((fx.get('league') or {}).get('round') or '')
    num = None
    m = re.search(r'(\d+)\s*$', ronda)
    if m:
        num = m.group(1)
    return {
        'api_id': match['api_id'],
        'home': {'slug': match['home']['slug'], 'name': match['home']['name'], 'goles': goals.get('home')},
        'away': {'slug': match['away']['slug'], 'name': match['away']['name'], 'goles': goals.get('away')},
        'estadio': _limpiar_estadio(((fx.get('fixture') or {}).get('venue') or {}).get('name')),
        'torneo': _etiqueta_torneo(match['comp'], num, None if match['comp'] == 'liga' else ronda),
        'goles': goles,
        'comp': match['comp'],
    }


# ── imagen ───────────────────────────────────────────────────────────────────
_LOGO = None


def _logo_datauri():
    """Recorta Logo.png y saca el fondo oscuro (alpha por diferencia) para que
    apoye sobre el degradado de la placa sin caja."""
    global _LOGO
    if _LOGO:
        return _LOGO
    from PIL import Image, ImageChops
    im = Image.open(ROOT / 'Logo.png').convert('RGB')
    fondo = Image.new('RGB', im.size, im.getpixel((0, 0)))
    dif = ImageChops.difference(im, fondo).convert('L')
    box = dif.point(lambda v: 255 if v > 12 else 0).getbbox()
    im, dif = im.crop(box), dif.crop(box)
    im.putalpha(dif.point(lambda v: min(255, int(v * 3.2))))
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    _LOGO = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    return _LOGO


BALL = ('<svg viewBox="0 0 24 24" width="20" height="20"><circle cx="12" cy="12" r="10.4" '
        'fill="#fff"/><path fill="#0b1020" d="M12 6.2l3.3 2.4-1.3 3.9h-4l-1.3-3.9zM5.1 '
        '10.9l1.2 3.7-1.9 1.3a8 8 0 0 1-.6-4.2zm13.8 0l1.3.8a8 8 0 0 1-.6 4.2l-1.9-1.3zM8.6 '
        '17.4h6.8l.7 2.1a8 8 0 0 1-8.2 0z"/></svg>')

ESTADIO_ICO = ('<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#38bdf8" '
               'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M3 9c0-1.7 4-3 9-3s9 1.3 9 3"/><path d="M3 9v7c0 1.7 4 3 9 3s9-1.3 9-3V9"/>'
               '<path d="M8 7v12M16 7v12"/></svg>')


def _nombre(slug, fallback):
    return (NOM.get(slug) or fallback or '').upper()


def _html(pl):
    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))

    def esc_tag(slug, cls):
        p = ROOT / 'escudos' / f'{slug}.png'
        return f'<img class="{cls}" src="{_b64(p, "image/png")}">' if slug and p.exists() else ''

    filas = ''.join(
        '<div class="gol"><span class="min">%s\'</span><span class="ball">%s</span>'
        '<span class="quien">%s</span>%s</div>'
        % (g['min'], BALL, (g['jugador'] or '').upper(), esc_tag(g['slug'], 'mini'))
        for g in pl['goles'])
    caja = f'<div class="goles">{filas}</div>' if filas else ''

    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{width:760px;height:950px;font-family:'Barlow Condensed',sans-serif;color:#fff;position:relative;
  overflow:hidden;background:#080c17;}
/* luces de tribuna abajo, como el fondo de estadio de las placas */
.bg{position:absolute;inset:0;
  background:radial-gradient(120%% 62%% at 50%% 118%%, rgba(56,140,220,.30) 0%%, rgba(20,44,86,.16) 42%%, transparent 70%%),
             radial-gradient(90%% 55%% at 50%% -10%%, rgba(28,58,110,.30), transparent 62%%),
             linear-gradient(180deg,#080c17 0%%,#0a1122 55%%,#070b16 100%%);}
.glow{position:absolute;left:0;right:0;bottom:0;height:38%%;
  background:repeating-linear-gradient(90deg, rgba(120,180,255,.05) 0 3px, transparent 3px 9px);
  -webkit-mask-image:linear-gradient(0deg,rgba(0,0,0,.85),transparent);}
.wrap{position:relative;height:100%%;padding:30px 34px 26px;display:flex;flex-direction:column}
.logo{height:38px;width:auto;align-self:flex-start}
.mid{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;margin-top:-26px}
.torneo{font-family:'Bebas Neue';font-size:19px;letter-spacing:5px;color:#38bdf8;margin-bottom:6px}
.tit{font-family:'Bebas Neue';font-size:44px;letter-spacing:9px;margin-bottom:44px}
.marc{display:flex;align-items:center;justify-content:center;gap:34px}
.eq{width:216px;display:flex;flex-direction:column;align-items:center;gap:18px}
.esc{width:150px;height:150px;object-fit:contain;filter:drop-shadow(0 8px 22px rgba(0,0,0,.6))}
.nom{font-family:'Bebas Neue';font-size:26px;letter-spacing:5px}
.num{font-family:'Bebas Neue';font-size:86px;line-height:1;margin-top:-34px}
.slash{width:2px;height:104px;margin-top:-34px;transform:rotate(14deg);
  background:linear-gradient(180deg,transparent,#38bdf8,transparent)}
.goles{margin-top:40px;display:flex;flex-direction:column;gap:8px;padding:14px 26px;
  border:1px solid rgba(255,255,255,.14);border-radius:16px;background:rgba(255,255,255,.035)}
.gol{display:flex;align-items:center;gap:16px}
.min{font-family:'Bebas Neue';font-size:22px;color:#38bdf8;min-width:44px}
.ball{display:flex;opacity:.92}
.quien{font-family:'Bebas Neue';font-size:22px;letter-spacing:2px;flex:1;text-align:center;padding:0 6px}
.mini{width:26px;height:26px;object-fit:contain}
.pie{display:flex;align-items:center;justify-content:center;gap:12px;
  font-family:'Bebas Neue';font-size:20px;letter-spacing:3px;color:#e8edf7}
</style></head><body>
<div class="bg"></div><div class="glow"></div>
<div class="wrap">
  <img class="logo" src="%s">
  <div class="mid">
    <div class="torneo">%s</div>
    <div class="tit">FINAL DEL PARTIDO</div>
    <div class="marc">
      <div class="eq">%s<div class="nom">%s</div></div>
      <div class="num">%s</div><div class="slash"></div><div class="num">%s</div>
      <div class="eq">%s<div class="nom">%s</div></div>
    </div>
    %s
  </div>
  <div class="pie">%s<span>%s</span></div>
</div></body></html>""" % (
        ff, _logo_datauri(), pl['torneo'],
        esc_tag(pl['home']['slug'], 'esc'), _nombre(pl['home']['slug'], pl['home']['name']),
        pl['home']['goles'], pl['away']['goles'],
        esc_tag(pl['away']['slug'], 'esc'), _nombre(pl['away']['slug'], pl['away']['name']),
        caja, ESTADIO_ICO, pl['estadio'])


def generar_imagen(pl, outdir):
    from playwright.sync_api import sync_playwright
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    path = Path(outdir) / f"ft-{pl['api_id'] or 'x'}-{pl['home']['slug']}-{pl['away']['slug']}.png"
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 760, 'height': 950}, device_scale_factor=2)
        pg.set_content(_html(pl))
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(path))
        b.close()
    return path


# ── tweet ────────────────────────────────────────────────────────────────────
def texto_tweet(pl):
    h = hashtag(pl['home']['slug'], pl['home']['name'])
    a = hashtag(pl['away']['slug'], pl['away']['name'])
    return (f"Terminó el partido: {h} {pl['home']['goles']}-{pl['away']['goles']} {a}\n\n"
            "¿Cómo jugaron? Puntuá a los jugadores y mirá las estadísticas del "
            "partido en tribunapp.com.ar")


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--test-partido', help='id de data/partidos (ej. sanlorenzo-union), sin API')
    args = ap.parse_args()

    if args.test_partido:
        pl = payload_desde_json(args.test_partido)
        PREVIEW.mkdir(parents=True, exist_ok=True)
        img = generar_imagen(pl, PREVIEW)
        print(f'imagen: {img}')
        print('texto:')
        for ln in texto_tweet(pl).splitlines():
            print('  |', ln)
        return 0

    cands = candidatos()
    if args.check:
        print(f'candidatos={len(cands)}')
        gh = os.environ.get('GITHUB_OUTPUT')
        if gh:
            with open(gh, 'a') as f:
                f.write(f'hay={"1" if cands else "0"}\n')
        return 0

    if not cands:
        print('sin partidos para cerrar')
        return 0

    SOCIAL.mkdir(parents=True, exist_ok=True)
    posted = _estado()
    from social_lineups import credenciales, tuitear
    keys = credenciales()
    for m in cands:
        tag = f"{m['home']['name']} vs {m['away']['name']} ({m['api_id']})"
        try:
            pl = payload_desde_api(m)
        except Exception as e:
            print(f'{tag}: error API ({e}), reintenta en la próxima corrida')
            continue
        if not pl:
            print(f'{tag}: todavía no terminó')
            continue
        outdir = PREVIEW if not keys else Path('/tmp')
        outdir.mkdir(parents=True, exist_ok=True)
        img = generar_imagen(pl, outdir)
        texto = texto_tweet(pl)
        if keys:
            try:
                tid = tuitear(texto, [img], keys)
                print(f'{tag}: tweet publicado ({tid})')
                posted[m['api_id']] = {'tweet_id': tid, 'at': datetime.now(timezone.utc).isoformat()}
            except Exception as e:
                print(f'{tag}: ERROR al tuitear: {e}')
                continue
        else:
            print(f'{tag}: MODO ENSAYO — imagen en {img}')
            for ln in texto.splitlines():
                print('   |', ln)
            posted[m['api_id']] = {'dry': True, 'at': datetime.now(timezone.utc).isoformat()}
        STATE.write_text(json.dumps(posted, ensure_ascii=False, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
