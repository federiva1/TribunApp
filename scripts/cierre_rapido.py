"""Cierre rápido de partidos: marca FT en liga.json y genera data/partidos
a los minutos del final, sin esperar los crons lentos.

El problema que resuelve: liga.json se regenera cada 2 h desde el AGREGADO de
api-sports (que además se atrasa >10 min al terminar un partido), así que el
gate de puntajes quedaba mostrando "1H" durante horas. El endpoint por-id
(fixtures?id=) marca FT al instante — es el mismo que usa la placa de
resultado y la ficha en vivo.

Flujo (workflow cierre-rapido.yml, cron cada 10 min):
  1. --check: ¿hay algún partido nuestro (liga o copa) que arrancó hace entre
     100 y 210 min y sigue sin finished? Solo lee data/fixtures, sin API.
  2. Sin --check: pregunta fixtures?id= por cada candidato. Si terminó:
     - parchea la entrada de liga.json (scores, winner, finished/FT) con el
       resultado del por-id — mismo formato que reparar_estados;
     - corre fetch_liga_partidos --date de ese día (genera el archivo con
       jugadores que abre el gate; si el agregado todavía no lo lista,
       reintenta en la próxima corrida);
     - recalcula la tabla xG.

Con esto el gate de puntajes abre ~10-20 min después del pitazo final en vez
de horas. Idempotente: un partido ya finished no es candidato.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# La consola de Windows usa cp1252: sin esto, un print con "→" o "✗" corta el
# script a mitad de camino (pasó al cerrar Est. Río Cuarto - Sarmiento el 4/9).
# En los runners de CI la salida ya es UTF-8, así que allá no cambia nada.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):   # stdout redirigido a algo sin reconfigure
    pass

ROOT = Path(__file__).resolve().parent.parent
FIXDIR = ROOT / 'data' / 'fixtures'

DESDE_MIN = 100   # min desde el kickoff en que un partido puede haber terminado
HASTA_MIN = 210   # después de esto lo agarran los crons normales igual

FT = ('FT', 'AET', 'PEN')

sys.path.insert(0, str(ROOT / 'scripts'))
from clubes_map import puntuar_url  # link compartible de la landing de puntajes


def _cargar():
    liga = json.loads((FIXDIR / 'liga.json').read_text(encoding='utf-8'))
    try:
        copas = json.loads((FIXDIR / 'copas.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        copas = {}
    return liga, copas


def candidatos(liga, copas, ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    out = []
    for e in liga:
        st = e.get('status') or {}
        if st.get('finished') or not st.get('utcTime'):
            continue
        mins = (ahora - datetime.fromisoformat(st['utcTime'])).total_seconds() / 60
        if DESDE_MIN <= mins <= HASTA_MIN:
            out.append({'comp': 'liga', 'entry': e, 'api_id': str(e['api_id'])})
    for key in ('libertadores', 'sudamericana'):
        for p in ((copas.get(key) or {}).get('partidos')) or []:
            if p.get('short') in FT or not p.get('utcTime'):
                continue
            mins = (ahora - datetime.fromisoformat(p['utcTime'])).total_seconds() / 60
            if DESDE_MIN <= mins <= HASTA_MIN:
                out.append({'comp': key, 'entry': p, 'api_id': str(p['api_id'])})
    return out


def fixture_por_id(api_id):
    from apikey import get_api_key
    req = urllib.request.Request(
        f'https://v3.football.api-sports.io/fixtures?id={api_id}',
        headers={'x-apisports-key': get_api_key()})
    with urllib.request.urlopen(req, timeout=25) as r:
        resp = json.loads(r.read()).get('response') or []
    return resp[0] if resp else None


def cerrar_liga(entry, fx):
    """Aplica al formato de liga.json lo que dice el por-id (mismos campos que
    reparar_estados). Valida la orientación por id de equipo, no por posición."""
    st = (fx.get('fixture') or {}).get('status') or {}
    goals = fx.get('goals') or {}
    home_id = str(((fx.get('teams') or {}).get('home') or {}).get('id') or '')
    if home_id != str(entry['home'].get('id')):
        print(f"  ! api_id {entry['api_id']}: el home del por-id ({home_id}) no coincide "
              f"con liga.json ({entry['home'].get('id')}), se saltea")
        return False
    gl, gv = goals.get('home'), goals.get('away')
    if gl is None or gv is None:
        return False
    entry['home_score'], entry['away_score'] = gl, gv
    entry['winner'] = None if gl == gv else (
        entry['home']['slug'] if gl > gv else entry['away']['slug'])
    entry['status'].update({'started': True, 'finished': True,
                            'short': st.get('short') or 'FT',
                            'elapsed': st.get('elapsed') or 90})
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    liga, copas = _cargar()
    cands = candidatos(liga, copas)

    if args.check:
        print(f'candidatos={len(cands)}')
        gh = os.environ.get('GITHUB_OUTPUT')
        if gh:
            with open(gh, 'a') as f:
                f.write(f'hay={"1" if cands else "0"}\n')
        return 0

    if not cands:
        print('sin partidos por cerrar')
        return 0

    cerrados_liga = False
    fechas = set()
    hay_copa = False
    for c in cands:
        e = c['entry']
        if c['comp'] == 'liga':
            tag = f"{e['home']['slug']} vs {e['away']['slug']} ({c['api_id']})"
        else:
            tag = f"{e['home'].get('slug') or e['home']['name']} vs " \
                  f"{e['away'].get('slug') or e['away']['name']} ({c['api_id']})"
        try:
            fx = fixture_por_id(c['api_id'])
        except Exception as ex:
            print(f'{tag}: error API ({ex})')
            continue
        if not fx:
            print(f'{tag}: sin respuesta por-id')
            continue
        short = ((fx.get('fixture') or {}).get('status') or {}).get('short')
        if short not in FT:
            print(f'{tag}: sigue en juego ({short})')
            continue
        utc = (e.get('status') or {}).get('utcTime') or e.get('utcTime')
        dia = datetime.fromisoformat(utc).astimezone(timezone.utc).strftime('%Y-%m-%d')
        if c['comp'] == 'liga':
            if cerrar_liga(e, fx):
                cerrados_liga = True
                fechas.add(dia)
                print(f'{tag}: FT {e["home_score"]}-{e["away_score"]} → liga.json actualizado')
                print(f'  link para compartir: {puntuar_url(e["home"]["slug"], e["away"]["slug"])}')
        else:
            # el gate de copa no mira copas.json (usa el archivo del partido);
            # alcanza con disparar la generación del archivo
            hay_copa = True
            fechas.add(dia)
            print(f'{tag}: FT → se genera el archivo de copa')
            print(f'  link para compartir: {puntuar_url(e["home"].get("slug") or e["home"]["name"], e["away"].get("slug") or e["away"]["name"])}')

    if cerrados_liga:
        (FIXDIR / 'liga.json').write_text(
            json.dumps(liga, ensure_ascii=False, indent=1), encoding='utf-8')

    # Genera data/partidos/{id}.json de los días afectados (abre el gate).
    # Si el agregado de api-sports todavía no lista el partido como FT, el
    # script lo saltea y la próxima corrida (10 min) lo reintenta.
    for dia in sorted(fechas):
        subprocess.run([sys.executable, 'scripts/fetch_liga_partidos.py',
                        '--torneo', 'clausura', '--date', dia], cwd=ROOT, check=False)
    if hay_copa:
        subprocess.run([sys.executable, 'scripts/fetch_liga_partidos.py',
                        '--competicion', 'copas'], cwd=ROOT, check=False)
    if fechas or hay_copa:
        subprocess.run([sys.executable, 'scripts/build_tabla_xg.py'],
                       cwd=ROOT, check=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
