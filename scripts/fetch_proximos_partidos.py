"""
fetch_proximos_partidos.py
Obtiene el próximo partido de cada uno de los 30 clubes de la Liga Profesional 2026
y actualiza js/clubes.js con rivalActual para cada club.
"""

import json
import re
import urllib.request
from datetime import datetime, timezone

API_KEY = 'b8bbfc856fd5cf12cd7d697b2b01887d'
LEAGUE  = 128
SEASON  = 2026

# API ID → slug
ESCUDO_MAP = {
    438:'velezsarsfield', 450:'estudiantes', 451:'bocajuniors', 442:'defensayjusticia',
    441:'union', 446:'lanus', 456:'talleres', 453:'independiente', 460:'sanlorenzo',
    1064:'clubatleticoplatense', 1066:'gimnasiamendoza', 1065:'centralcordobadesantiago',
    478:'instituto', 476:'deportivoriestra', 457:'newellsoldboys', 473:'independienterivadavia',
    435:'riverplate', 458:'argentinosjuniors', 440:'belgrano', 436:'racingclub',
    437:'rosariocentral', 452:'tigre', 2432:'barracascentral', 474:'sarmiento',
    445:'huracan', 434:'gimnasialp', 449:'banfield', 455:'atleticotucuman',
    463:'aldosivi', 2424:'estudiantesderiocuarto'
}

# API ID → nombre corto legible (para usar como rivalActual)
NOMBRE_CORTO = {
    438:'Vélez', 450:'Estudiantes', 451:'Boca', 442:'Def. Justicia', 441:'Unión SF',
    446:'Lanús', 456:'Talleres', 453:'Independiente', 460:'San Lorenzo', 1064:'Platense',
    1066:'Gimnasia M', 1065:'Cen. Córdoba', 478:'Instituto', 476:'Riestra', 457:"Newell's",
    473:'Ind. Rivadavia', 435:'River', 458:'Argentinos', 440:'Belgrano', 436:'Racing',
    437:'Rosario C', 452:'Tigre', 2432:'Barracas C', 474:'Sarmiento', 445:'Huracán',
    434:'Gimnasia LP', 449:'Banfield', 455:'Atl. Tucumán', 463:'Aldosivi', 2424:'Est. Río Cuarto'
}


def api_get(endpoint):
    url = f'https://v3.football.api-sports.io/{endpoint}'
    req = urllib.request.Request(url, headers={'x-apisports-key': API_KEY})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def fetch_fixtures():
    """Trae todos los fixtures NS (no iniciados) de la liga."""
    print('Consultando fixtures próximos...')
    data = api_get(f'fixtures?league={LEAGUE}&season={SEASON}&status=NS')
    fixtures = data.get('response', [])
    print(f'  {len(fixtures)} fixtures pendientes encontrados')
    return fixtures


def find_next_per_team(fixtures):
    """Para cada team ID retorna el fixture más próximo."""
    now = datetime.now(timezone.utc)
    next_fix = {}   # team_id → fixture dict

    for f in fixtures:
        try:
            ts = f['fixture']['date']
            # "2026-04-20T18:00:00+00:00" o similar
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            continue

        if dt < now:
            continue

        for side in ('home', 'away'):
            tid = f['teams'][side]['id']
            if tid not in ESCUDO_MAP:
                continue
            if tid not in next_fix or dt < datetime.fromisoformat(
                    next_fix[tid]['fixture']['date'].replace('Z', '+00:00')):
                next_fix[tid] = f

    return next_fix


def build_rival_map(next_fix):
    """team_id → nombre corto del rival."""
    rivals = {}
    for tid, f in next_fix.items():
        home_id = f['teams']['home']['id']
        away_id = f['teams']['away']['id']
        rival_id = away_id if home_id == tid else home_id

        if rival_id in NOMBRE_CORTO:
            rival_name = NOMBRE_CORTO[rival_id]
        else:
            side = 'away' if home_id == tid else 'home'
            rival_name = f['teams'][side]['name']

        slug = ESCUDO_MAP[tid]
        date_str = f['fixture']['date'][:10]
        rival_full = f['teams']['away']['name'] if home_id == tid else f['teams']['home']['name']
        print(f'  {slug:<30} vs {rival_name:<20}  ({date_str})')
        rivals[slug] = rival_name

    return rivals


def update_clubes_js(rivals):
    """Reemplaza/agrega rivalActual en js/clubes.js para cada slug."""
    js_path = '../js/clubes.js'
    with open(js_path, 'r', encoding='utf-8') as fh:
        src = fh.read()

    updated = 0
    for slug, rival in rivals.items():
        # Escapa comillas simples en el nombre
        rival_safe = rival.replace("'", "\\'")

        # Intenta reemplazar rivalActual existente
        pattern_existing = rf"(  {re.escape(slug)}: \{{[^}}]*?)rivalActual: '[^']*'"
        replacement = rf"\1rivalActual: '{rival_safe}'"
        new_src, n = re.subn(pattern_existing, replacement, src, flags=re.DOTALL)

        if n:
            src = new_src
            updated += 1
        else:
            # Agrega rivalActual después de la línea colorSecundario o squad
            # Busca el bloque del slug y añade antes de squad: []
            pattern_insert = (
                rf"(  {re.escape(slug)}: \{{[^\n]*\n"
                rf"(?:    (?!squad)[^\n]*\n)*?)"
                rf"(    squad: \[\])"
            )
            replacement_insert = rf"\1    rivalActual: '{rival_safe}',\n\2"
            new_src, n = re.subn(pattern_insert, replacement_insert, src)
            if n:
                src = new_src
                updated += 1
            else:
                print(f'  WARN: no se pudo insertar rivalActual para {slug}')

    with open(js_path, 'w', encoding='utf-8') as fh:
        fh.write(src)

    print(f'\nclubues.js actualizado: {updated}/{len(rivals)} clubes con rivalActual.')


def main():
    fixtures = fetch_fixtures()
    if not fixtures:
        print('Sin fixtures. Puede que la temporada no tenga partidos pendientes o la API esté vacía.')
        return

    print('\nPróximo partido por equipo:')
    next_fix = find_next_per_team(fixtures)

    missing = [NOMBRE_CORTO[tid] for tid in ESCUDO_MAP if tid not in next_fix]
    if missing:
        print(f'\nSin próximo partido detectado: {missing}')

    rivals = build_rival_map(next_fix)
    print()
    update_clubes_js(rivals)


if __name__ == '__main__':
    main()
