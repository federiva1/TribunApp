"""Tweet automático de formaciones confirmadas (liga + copas).

Flujo (workflow lineups-social.yml, cron cada 5 min):
  1. --check: ¿hay algún partido nuestro que arranca dentro de los próximos 32
     min y sin postear? Solo lee data/fixtures (sin API, sin dependencias). Si
     no hay, el workflow corta ahí sin instalar Playwright ni gastar llamadas.
  2. Sin --check: pide las alineaciones a api-sports (fixtures/lineups). Si los
     dos equipos tienen XI confirmado, genera una imagen por equipo (cancha
     vertical con kit chips + nombre, estilo TribunApp) y tuitea.
  3. Sin credenciales de X (secrets X_API_KEY etc.) corre en MODO ENSAYO:
     genera las imágenes, las commitea en data/social/preview/ para revisarlas
     y marca el partido como posteado (dry) para no duplicar.

Estado en data/social/lineups_posted.json (commiteado): {api_id: {...}}.
La ventana va de 32 min antes del kickoff hasta el kickoff: con el cron cada 5
min hay ~6 intentos (30, 25, 20, 15, 10 y 5 min antes). El primero que encuentra
los dos XI confirmados postea y deja el partido marcado, así los intentos que
siguen lo saltean. Después del kickoff ya no se intenta: la gracia es que la
gente vea las formaciones ANTES de que empiece.

Test manual / sandbox:
  python scripts/social_lineups.py --test-fixture 12345 --test-lineups f.json
(fuerza ese partido como candidato y usa las alineaciones del archivo en vez
de la API; sin credenciales queda en ensayo).
"""
import argparse
import base64
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXDIR = ROOT / 'data' / 'fixtures'
SOCIAL = ROOT / 'data' / 'social'
PREVIEW = SOCIAL / 'preview'
STATE = SOCIAL / 'lineups_posted.json'

VENTANA_ANTES = 32   # min antes del kickoff en que empezamos a intentar
VENTANA_DESPUES = 0  # cortamos en el kickoff: después ya no sirve postearlas

sys.path.insert(0, str(ROOT / 'scripts'))
from clubes_map import CLUBES  # noqa: E402


# ── metadatos de clubes (nombres/hashtags desde js/clubes.js) ────────────────
def _nombres_cortos():
    # Ojo con las comillas: los nombres con apóstrofo van entre dobles
    # (nombreCorto: "Newell's"), así que hay que aceptar los dos estilos.
    src = (ROOT / 'js' / 'clubes.js').read_text(encoding='utf-8')
    return {m.group(1): m.group(3) for m in
            re.finditer(r"""^  ([a-z0-9]+):\s*\{[^}]*?nombreCorto:\s*(['"])(.*?)\2""",
                        src, re.M | re.S)}


NOM = _nombres_cortos()


def hashtag(slug, nombre_api=''):
    """#Boca, #UnionSF, #Newells… Para rivales sin slug (copa) no hay hashtag."""
    n = NOM.get(slug) or ''
    if not n:
        return nombre_api          # rival extranjero: nombre pelado
    plano = unicodedata.normalize('NFD', n).encode('ascii', 'ignore').decode()
    plano = re.sub(r'[^A-Za-z0-9]', '', plano)
    return '#' + plano if plano else nombre_api


# ── candidatos: partidos nuestros cerca del kickoff ──────────────────────────
def _cargar_partidos(incluir_terminados=False):
    """Partidos nuestros (liga + copas) con su kickoff. Los terminados se saltean
    salvo que los pida quien llama (la placa de FT justamente los necesita)."""
    out = []
    liga = json.loads((FIXDIR / 'liga.json').read_text(encoding='utf-8'))
    for p in liga:
        st = p.get('status') or {}
        if not st.get('utcTime') or (st.get('finished') and not incluir_terminados):
            continue
        out.append({
            'api_id': str(p['api_id']), 'utc': st['utcTime'], 'comp': 'liga',
            'home': {'slug': p['home']['slug'], 'name': p['home']['name']},
            'away': {'slug': p['away']['slug'], 'name': p['away']['name']},
        })
    try:
        copas = json.loads((FIXDIR / 'copas.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        copas = {}
    for key in ('libertadores', 'sudamericana'):
        for p in ((copas.get(key) or {}).get('partidos')) or []:
            if not p.get('utcTime') or (p.get('short') in ('FT', 'AET', 'PEN')
                                        and not incluir_terminados):
                continue
            out.append({
                'api_id': str(p['api_id']), 'utc': p['utcTime'], 'comp': key,
                'home': {'slug': p['home'].get('slug'), 'name': p['home']['name']},
                'away': {'slug': p['away'].get('slug'), 'name': p['away']['name']},
            })
    return out


def _estado():
    try:
        return json.loads(STATE.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def candidatos(ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    posted = _estado()
    out = []
    for m in _cargar_partidos():
        if m['api_id'] in posted:
            continue
        ko = datetime.fromisoformat(m['utc'])
        delta = (ko - ahora).total_seconds() / 60
        if -VENTANA_DESPUES <= delta <= VENTANA_ANTES:
            out.append(m)
    return out


# ── api-sports ───────────────────────────────────────────────────────────────
def fetch_lineups(api_id):
    from apikey import get_api_key
    req = urllib.request.Request(
        f'https://v3.football.api-sports.io/fixtures/lineups?fixture={api_id}',
        headers={'x-apisports-key': get_api_key()})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read()).get('response', [])


# ── nombres completos: dorsal → plantel ──────────────────────────────────────
def _plantel_por_num(slug):
    try:
        d = json.loads((ROOT / 'data' / 'planteles' / f'{slug}.json').read_text(encoding='utf-8'))
    except (FileNotFoundError, TypeError):
        return {}
    return {str(p.get('num') or ''): p['name'] for p in d if str(p.get('num') or '').strip()}


def _apellido(nombre):
    """Etiqueta corta: "Nicolás Gaitán" entero si entra; api-sports ya abrevia."""
    return nombre if len(nombre) <= 22 else nombre.split()[-1]


# ── layout: grid api-sports → posiciones en cancha vertical ──────────────────
# Ancho que ocupa una línea según cuántos jugadores tenga: una dupla de volantes
# centrales va junta en el medio (34-66) y una línea de 4 se abre hasta los laterales.
ANCHO_LINEA = {1: 0, 2: 32, 3: 56, 4: 76, 5: 84}


def posiciones(startxi):
    """grid "fila:col" (fila 1 = arquero, crece hacia el ataque; col 1 = IZQUIERDA
    mirando la cancha con el arquero abajo, que es como se dibuja la placa: el
    lateral izquierdo queda a la izquierda). Sin grid (raro) → filas de a 4."""
    filas = {}
    sueltos = []
    for j in startxi:
        pl = j.get('player') or {}
        g = pl.get('grid') or ''
        m = re.match(r'^(\d+):(\d+)$', g)
        (filas.setdefault(int(m.group(1)), []).append((int(m.group(2)), pl))
         if m else sueltos.append(pl))
    out = []
    nf = sorted(filas)
    for i, f in enumerate(nf):
        cols = sorted(filas[f], key=lambda t: t[0])
        y = 90 if f == 1 else 72 - (i - 1) * (58 / max(1, len(nf) - 2))
        n = len(cols)
        ancho = ANCHO_LINEA.get(n, 84)
        for k, (_, pl) in enumerate(cols):
            x = 50 if n == 1 else (50 - ancho / 2) + k * (ancho / (n - 1))
            out.append((x, y, pl))
    for k, pl in enumerate(sueltos):
        out.append((15 + (k % 4) * 23, 50 - (k // 4) * 14, pl))
    return out


# ── imagen: HTML + Playwright ────────────────────────────────────────────────
def _b64(path, mime):
    return f'data:{mime};base64,' + base64.b64encode(Path(path).read_bytes()).decode()


def _html_equipo(slug, nombre_api, formacion, startxi):
    kits_js = (ROOT / 'js' / 'kits.js').read_text(encoding='utf-8')
    colors_js = (ROOT / 'js' / 'club-colors.js').read_text(encoding='utf-8')
    plantel = _plantel_por_num(slug) if slug else {}
    jugadores = []
    for x, y, pl in posiciones(startxi):
        num = str(pl.get('number') or '')
        nombre = plantel.get(num) or pl.get('name') or ''
        jugadores.append({'x': x, 'y': y, 'num': num, 'nombre': _apellido(nombre)})
    ff = ''.join(
        "@font-face{font-family:'%s';font-weight:%s;src:url(%s) format('woff2');}"
        % (fam, w, _b64(ROOT / 'fonts' / f, 'font/woff2'))
        for fam, w, f in (("Bebas Neue", 400, 'bebas-neue-latin-400-normal.woff2'),
                          ("Barlow Condensed", 400, 'barlow-condensed-latin-400-normal.woff2'),
                          ("Barlow Condensed", 600, 'barlow-condensed-latin-600-normal.woff2')))
    titulo = NOM.get(slug) or nombre_api
    esc = ROOT / 'escudos' / f'{slug}.png'
    esc_tag = (f'<img class="esc" src="{_b64(esc, "image/png")}">'
               if slug and esc.exists() else '')
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
%s
* { margin:0; padding:0; box-sizing:border-box; }
body { width:700px; height:860px; font-family:'Barlow Condensed',sans-serif;
       background:linear-gradient(150deg,#10182e,#0a0f1e); color:#fff; padding:16px 18px; }
.hdr { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.esc { width:34px; height:34px; object-fit:contain; }
h1 { font-family:'Bebas Neue',sans-serif; font-size:27px; letter-spacing:2px; flex:1; }
.form { font-family:'Bebas Neue',sans-serif; font-size:19px; letter-spacing:2px; color:#8b93a7; }
#pitch { position:relative; width:100%%; height:724px; border-radius:12px; overflow:hidden;
  background: repeating-linear-gradient(0deg, rgba(255,255,255,.045) 0 45px, transparent 45px 90px),
              linear-gradient(160deg,#12492a,#0a2f1a); }
.l { position:absolute; box-sizing:border-box; border:2px solid rgba(255,255,255,.30); }
.jug { position:absolute; transform:translate(-50%%,-50%%); display:flex; flex-direction:column;
       align-items:center; gap:4px; }
.chip { width:52px; height:52px; border-radius:50%%; border:2.5px solid rgba(255,255,255,.92);
        box-shadow:0 2px 6px rgba(0,0,0,.5); display:flex; align-items:center; justify-content:center; }
.chip span { font-family:'Bebas Neue',sans-serif; font-size:22px; color:#fff;
  text-shadow:-1px -1px 0 rgba(0,0,0,.55),1px -1px 0 rgba(0,0,0,.55),-1px 1px 0 rgba(0,0,0,.55),1px 1px 0 rgba(0,0,0,.55); }
.tag { font-size:13.5px; font-weight:600; background:rgba(10,15,30,.88); border:1px solid rgba(255,255,255,.25);
       padding:2px 9px; border-radius:11px; white-space:nowrap; }
.foot { text-align:right; font-size:12px; color:#5d6479; margin-top:8px; }
</style></head><body>
<div class="hdr">%s<h1>%s</h1><div class="form">%s</div></div>
<div id="pitch">
  <div class="l" style="inset:10px; border-radius:8px;"></div>
  <div class="l" style="left:10px; right:10px; top:50%%; height:0; border-width:1px 0 0 0;"></div>
  <div class="l" style="left:50%%; top:50%%; width:110px; height:110px; margin:-55px 0 0 -55px; border-radius:50%%;"></div>
  <div class="l" style="left:22%%; right:22%%; bottom:10px; height:14%%; border-bottom:none;"></div>
  <div class="l" style="left:35%%; right:35%%; bottom:10px; height:6%%; border-bottom:none;"></div>
  <div class="l" style="left:22%%; right:22%%; top:10px; height:14%%; border-top:none;"></div>
  <div class="l" style="left:35%%; right:35%%; top:10px; height:6%%; border-top:none;"></div>
</div>
<div class="foot">tribunapp.com.ar</div>
<script>%s</script><script>%s</script>
<script>
const SLUG = %s, JUG = %s;
const pitch = document.getElementById('pitch');
const kit = (typeof clubKit === 'function' && SLUG) ? clubKit(SLUG) : { type:'solid', colors:['#39445c'] };
JUG.forEach(j => {
  const d = document.createElement('div');
  d.className = 'jug'; d.style.left = j.x + '%%'; d.style.top = j.y + '%%';
  const c = document.createElement('div');
  c.className = 'chip'; c.style.background = kitBackground(kit, 52);
  const n = document.createElement('span'); n.textContent = j.num; c.appendChild(n);
  const t = document.createElement('div'); t.className = 'tag'; t.textContent = j.nombre;
  d.appendChild(c); d.appendChild(t); pitch.appendChild(d);
});
</script></body></html>""" % (ff, esc_tag, titulo.upper(), formacion or '',
                              kits_js, colors_js,
                              json.dumps(slug or ''), json.dumps(jugadores, ensure_ascii=False))


def generar_imagenes(match, lineups, outdir):
    from playwright.sync_api import sync_playwright
    exe = os.environ.get('PLAYWRIGHT_CHROMIUM') or None
    archivos = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        for lado in ('home', 'away'):
            team = match[lado]
            lu = next((x for x in lineups
                       if str((x.get('team') or {}).get('id') or '') ==
                       str((CLUBES.get(team['slug']) or {}).get('apisports') or '__')
                       or (x.get('team') or {}).get('name') == team['name']), None)
            if not lu:
                lu = lineups[0 if lado == 'home' else 1]
            pg = b.new_page(viewport={'width': 700, 'height': 860}, device_scale_factor=2)
            pg.set_content(_html_equipo(team['slug'], team['name'],
                                        lu.get('formation') or '', lu.get('startXI') or []))
            pg.wait_for_timeout(700)
            path = Path(outdir) / f"{match['api_id']}-{team['slug'] or 'rival'}-{lado}.png"
            pg.screenshot(path=str(path))
            archivos.append(path)
            pg.close()
        b.close()
    return archivos


# ── tweet ────────────────────────────────────────────────────────────────────
def credenciales():
    ks = [os.environ.get(k) for k in
          ('X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET')]
    return ks if all(ks) else None


def texto_tweet(match):
    h = hashtag(match['home']['slug'], match['home']['name'])
    a = hashtag(match['away']['slug'], match['away']['name'])
    comp = {'libertadores': ' (Copa Libertadores)', 'sudamericana': ' (Copa Sudamericana)'}.get(match['comp'], '')
    return (f"Formaciones confirmadas para {h} y {a}{comp}\n\n"
            "Podés seguir el partido, ver las estadísticas y calificar a los "
            "jugadores en tribunapp.com.ar")


def tuitear(texto, imagenes, keys):
    from requests_oauthlib import OAuth1
    import requests
    auth = OAuth1(*keys)
    media_ids = []
    for img in imagenes:
        r = requests.post('https://upload.twitter.com/1.1/media/upload.json',
                          files={'media': img.read_bytes()}, auth=auth, timeout=60)
        r.raise_for_status()
        media_ids.append(r.json()['media_id_string'])
    r = requests.post('https://api.twitter.com/2/tweets',
                      json={'text': texto, 'media': {'media_ids': media_ids}},
                      auth=auth, timeout=60)
    r.raise_for_status()
    return r.json()['data']['id']


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='solo dice si hay candidatos (para el guard del workflow)')
    ap.add_argument('--test-fixture', help='fuerza este api_id como candidato')
    ap.add_argument('--test-lineups', help='archivo con la respuesta de lineups (sin API)')
    args = ap.parse_args()

    cands = candidatos()
    if args.test_fixture:
        todos = {m['api_id']: m for m in _cargar_partidos()}
        if args.test_fixture in todos:
            cands = [todos[args.test_fixture]]
        else:
            print(f'test-fixture {args.test_fixture} no está en los fixtures')
            return 1

    if args.check:
        print(f'candidatos={len(cands)}')
        gh = os.environ.get('GITHUB_OUTPUT')
        if gh:
            with open(gh, 'a') as f:
                f.write(f'hay={"1" if cands else "0"}\n')
        return 0

    if not cands:
        print('sin partidos en ventana')
        return 0

    SOCIAL.mkdir(parents=True, exist_ok=True)
    posted = _estado()
    keys = credenciales()
    for m in cands:
        tag = f"{m['home']['name']} vs {m['away']['name']} ({m['api_id']})"
        if args.test_lineups:
            lineups = json.loads(Path(args.test_lineups).read_text(encoding='utf-8'))
        else:
            try:
                lineups = fetch_lineups(m['api_id'])
            except Exception as e:
                print(f'{tag}: error API ({e}), reintenta en la próxima corrida')
                continue
        xi_ok = (len(lineups) >= 2 and
                 all(len(x.get('startXI') or []) == 11 for x in lineups[:2]))
        if not xi_ok:
            print(f'{tag}: alineaciones todavía no confirmadas')
            continue

        outdir = PREVIEW if not keys else Path('/tmp')
        outdir.mkdir(parents=True, exist_ok=True)
        imgs = generar_imagenes(m, lineups, outdir)
        texto = texto_tweet(m)
        if keys:
            try:
                tid = tuitear(texto, imgs, keys)
                print(f'{tag}: tweet publicado ({tid})')
                posted[m['api_id']] = {'tweet_id': tid, 'at': datetime.now(timezone.utc).isoformat()}
            except Exception as e:
                print(f'{tag}: ERROR al tuitear: {e}')
                continue
        else:
            print(f'{tag}: MODO ENSAYO (sin credenciales de X) — imágenes en {outdir}')
            print('   texto que se hubiera tuiteado:')
            for ln in texto.splitlines():
                print('   |', ln)
            posted[m['api_id']] = {'dry': True, 'at': datetime.now(timezone.utc).isoformat()}
        STATE.write_text(json.dumps(posted, ensure_ascii=False, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
