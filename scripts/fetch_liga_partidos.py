"""Batch: procesa TODOS los partidos FT de la Liga Profesional → data/partidos/.

Para cada partido finalizado:
  1. Base (lineup/eventos/top_stats) desde api-sports  → fetch_mundial_match.process_fixture
  2. Resuelve la URL de FotMob (por fotmob_id del club, vía clubes_map)
  3. Enriquece jugadores (top/ataque/defensa/duelos) desde FotMob → scrape_fotmob_mundial

Idempotente: saltea los que ya tienen stats de FotMob (salvo --force).

Uso:
    python scripts/fetch_liga_partidos.py                 # FT de Clausura no procesados
    python scripts/fetch_liga_partidos.py --force         # reprocesa también los hechos
    python scripts/fetch_liga_partidos.py --torneo apertura
    python scripts/fetch_liga_partidos.py --torneo all
    python scripts/fetch_liga_partidos.py --date 2026-07-26
    python scripts/fetch_liga_partidos.py --limit 3       # solo los primeros N (probar)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import fetch_mundial_match as fmm       # noqa: E402
import scrape_fotmob_mundial as sfm     # noqa: E402
from clubes_map import CLUBES           # noqa: E402

SEASON = 2026
FINISHED = ('FT', 'AET', 'PEN')

# Copa: NO backfillear la fase de grupos (ya jugada). Solo se cargan partidos de
# copa de esta fecha en adelante (octavos y siguientes). Overridable con --desde.
COPA_DESDE = '2026-08-01'

# Competiciones soportadas → league id de api-sports + label + si es copa.
# En copa solo se procesan los partidos que involucran a un club argentino
# (el rival extranjero se resuelve por nombre y la URL de FotMob por el fotmob_id
# del club argentino).
COMPS = {
    'liga':         {'league': 128, 'label': None,                       'copa': False},
    'libertadores': {'league': 13,  'label': 'Copa Libertadores 2026',   'copa': True},
    'sudamericana': {'league': 11,  'label': 'Copa Sudamericana 2026',    'copa': True},
}


def resolve_fotmob_url(fotmob_id: int, date_str: str):
    """Baja la página de fixtures del equipo en FotMob y devuelve la URL del
    partido de esa fecha (o None)."""
    d = sfm._next_data_http(f'https://www.fotmob.com/teams/{fotmob_id}/fixtures')
    if not d:
        return None
    try:
        fx = d['props']['pageProps']['fallback'][f'team-{fotmob_id}']['fixtures']
    except Exception:
        return None
    fixtures = fx.get('allFixtures', {}).get('fixtures', fx) if isinstance(fx, dict) else fx
    for m in fixtures or []:
        utc = (m.get('status') or {}).get('utcTime', '') or m.get('utcTime', '')
        if date_str in str(utc):
            page = m.get('pageUrl', '')
            if page:
                return f'https://www.fotmob.com{page}'
    return None


def already_enriched(out_id: str) -> bool:
    f = fmm.PARTIDOS_DIR / f'{out_id}.json'
    if not f.exists():
        return False
    try:
        d = json.loads(f.read_text(encoding='utf-8'))
    except Exception:
        return False
    jugs = [j for jj in d.get('jugadores', {}).values() for j in jj if j.get('tipo') != 'dt']
    return any(j.get('top') is not None for j in jugs)


def competicion_de(round_str: str) -> str:
    r = (round_str or '').lower()
    if 'clausura' in r:
        return 'Clausura 2026'
    if 'apertura' in r:
        return 'Apertura 2026'
    return round_str or 'Liga Profesional 2026'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='Reprocesar aunque ya tenga stats FotMob')
    ap.add_argument('--date', default=None, help='Solo el/los partido(s) de esta fecha YYYY-MM-DD')
    ap.add_argument('--torneo', default='clausura', help='(liga) clausura | apertura | all')
    ap.add_argument('--competicion', default='liga',
                    help='liga | libertadores | sudamericana | copas | all')
    ap.add_argument('--desde', default=COPA_DESDE,
                    help=f'(copa) fecha mínima YYYY-MM-DD; no carga partidos anteriores (default {COPA_DESDE})')
    ap.add_argument('--limit', type=int, default=0, help='Procesar solo los primeros N (probar)')
    args = ap.parse_args()

    if args.competicion == 'all':
        comps = list(COMPS.keys())
    elif args.competicion == 'copas':
        comps = ['libertadores', 'sudamericana']
    else:
        comps = [args.competicion]

    todo = []
    for cname in comps:
        cfg = COMPS[cname]
        print(f'GET fixtures {cname} (league={cfg["league"]}) season={SEASON}...')
        data = fmm.api_get(f'fixtures?league={cfg["league"]}&season={SEASON}')
        fixtures = data.get('response', [])
        for f in fixtures:
            if f['fixture']['status']['short'] not in FINISHED:
                continue
            rnd = f['league'].get('round', '') or ''
            # En liga se filtra por torneo (clausura/apertura); en copa no aplica.
            if not cfg['copa'] and args.torneo != 'all' and args.torneo not in rnd.lower():
                continue
            date = f['fixture']['date'][:10]
            if args.date and date != args.date:
                continue
            # Copa: solo de --desde en adelante (no backfillear fase de grupos vieja).
            if cfg['copa'] and args.desde and date < args.desde:
                continue
            home, away = f['teams']['home'], f['teams']['away']
            ls = fmm.team_slug(home['id'], home['name'])
            vs = fmm.team_slug(away['id'], away['name'])
            # En copa: solo partidos con un club argentino (tiene fotmob_id en clubes_map).
            if cfg['copa'] and not (CLUBES.get(ls, {}).get('fotmob') or CLUBES.get(vs, {}).get('fotmob')):
                continue
            comp_label = cfg['label'] if cfg['copa'] else competicion_de(rnd)
            todo.append({
                'fid': f['fixture']['id'], 'oid': f'{ls}-{vs}', 'ls': ls, 'vs': vs,
                'comp': comp_label, 'date': date,
            })

    todo.sort(key=lambda m: m['date'])
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(todo)} partidos FT objetivo ({args.competicion})\n')

    ok = skip = err = nourl = 0
    for i, m in enumerate(todo, 1):
        tag = f"[{i}/{len(todo)}] {m['oid']} ({m['date']})"
        if not args.force and already_enriched(m['oid']):
            skip += 1
            print(f'{tag}  -> skip (ya procesado)')
            continue
        print(tag)
        try:
            # 1. Base api-sports (lineup/eventos/top_stats) + index.json
            fmm.process_fixture(m['fid'], m['oid'], m['ls'], m['vs'], m['comp'])

            # 2. URL FotMob — por fotmob_id del local; fallback al visitante
            url = None
            for slug in (m['ls'], m['vs']):
                fid = (CLUBES.get(slug) or {}).get('fotmob')
                if fid:
                    url = resolve_fotmob_url(fid, m['date'])
                    if url:
                        break
            if not url:
                nourl += 1
                print('   sin URL FotMob (queda con base api-sports, sin stats individuales)')
                ok += 1
                continue

            # 3. Enriquecer jugadores desde FotMob
            out_file = fmm.PARTIDOS_DIR / f"{m['oid']}.json"
            payload = json.loads(out_file.read_text(encoding='utf-8'))
            nd = sfm._fetch_next_data(url)
            payload = sfm._enrich_payload_from_nd(nd, payload)
            out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'   enriquecido ({url.split("#")[0]})')
            ok += 1
        except Exception as e:
            err += 1
            print(f'   ERROR: {e}')
        time.sleep(1.5)

    print(f'\nOK {ok} · skip {skip} · sin-URL {nourl} · error {err}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
