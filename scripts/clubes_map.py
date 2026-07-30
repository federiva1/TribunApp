"""Mapping centralizado club_slug -> {apisports_id, fotmob_id, nombre}.

Lo usan los scripts de scraping (fetch_match_stats.py, scrape_fotmob_partidos.py)
para resolver IDs sin tener que repetirlos en cada script.

A medida que probamos nuevos clubes, completamos su `fotmob` ID. Los `apisports`
ya están todos en `fetch_fixtures.py`.
"""
from __future__ import annotations

# slug -> {apisports, fotmob (si lo conocemos), nombre}
CLUBES = {
    # Liga Profesional Argentina
    'argentinosjuniors':        {'apisports': 458,  'fotmob': 10086, 'nombre': 'Argentinos Juniors'},
    'velezsarsfield':           {'apisports': 438,  'fotmob': 10079,  'nombre': 'Vélez Sarsfield'},
    'estudiantes':              {'apisports': 450,  'fotmob': 10094,  'nombre': 'Estudiantes de La Plata'},
    'bocajuniors':              {'apisports': 451,  'fotmob': 10077,  'nombre': 'Boca Juniors'},
    'defensayjusticia':         {'apisports': 442,  'fotmob': 161730,  'nombre': 'Defensa y Justicia'},
    'union':                    {'apisports': 441,  'fotmob': 10096,  'nombre': 'Unión de Santa Fe'},
    'lanus':                    {'apisports': 446,  'fotmob': 10082,  'nombre': 'Lanús'},
    'talleres':                 {'apisports': 456,  'fotmob': 10101,  'nombre': 'Talleres de Córdoba'},
    'independiente':            {'apisports': 453,  'fotmob': 10078, 'nombre': 'Independiente'},
    'sanlorenzo':               {'apisports': 460,  'fotmob': 10083,  'nombre': 'San Lorenzo'},
    'clubatleticoplatense':     {'apisports': 1064, 'fotmob': 10089, 'nombre': 'Platense'},
    'gimnasiamendoza':          {'apisports': 1066, 'fotmob': 568727,  'nombre': 'Gimnasia Mendoza'},
    'centralcordobadesantiago': {'apisports': 1065, 'fotmob': 213596,  'nombre': 'Central Córdoba'},
    'instituto':                {'apisports': 478,  'fotmob': 10090,  'nombre': 'Instituto'},
    'deportivoriestra':         {'apisports': 476,  'fotmob': 298629,'nombre': 'Deportivo Riestra'},
    'newellsoldboys':           {'apisports': 457,  'fotmob': 10201,  'nombre': "Newell's Old Boys"},
    'independienterivadavia':   {'apisports': 473,  'fotmob': 161729,  'nombre': 'Independiente Rivadavia'},
    'riverplate':               {'apisports': 435,  'fotmob': 10076,  'nombre': 'River Plate'},
    'belgrano':                 {'apisports': 440,  'fotmob': 10092,  'nombre': 'Belgrano'},
    'racingclub':               {'apisports': 436,  'fotmob': 10080, 'nombre': 'Racing Club'},
    'rosariocentral':           {'apisports': 437,  'fotmob': 10084,  'nombre': 'Rosario Central'},
    'tigre':                    {'apisports': 452,  'fotmob': 89396,  'nombre': 'Tigre'},
    'barracascentral':          {'apisports': 2432, 'fotmob': 213534,  'nombre': 'Barracas Central'},
    'sarmiento':                {'apisports': 474,  'fotmob': 202757,  'nombre': 'Sarmiento de Junín'},
    'huracan':                  {'apisports': 445,  'fotmob': 10081,  'nombre': 'Huracán'},
    'gimnasialp':               {'apisports': 434,  'fotmob': 10103,  'nombre': 'Gimnasia La Plata'},
    'banfield':                 {'apisports': 449,  'fotmob': 10087,  'nombre': 'Banfield'},
    'atleticotucuman':          {'apisports': 455,  'fotmob': 161727,  'nombre': 'Atlético Tucumán'},
    'aldosivi':                 {'apisports': 463,  'fotmob': 161728,  'nombre': 'Aldosivi'},
    'estudiantesderiocuarto':   {'apisports': 2424, 'fotmob': 213591,  'nombre': 'Est. de Río Cuarto'},
}

# Liga ID api-sports
LEAGUE_LIGA          = 128
LEAGUE_LIBERTADORES  = 13
LEAGUE_SUDAMERICANA  = 11

LEAGUE_BY_COPA = {
    '':              LEAGUE_LIGA,
    'libertadores':  LEAGUE_LIBERTADORES,
    'sudamericana':  LEAGUE_SUDAMERICANA,
}


def lookup(slug: str) -> dict:
    if slug not in CLUBES:
        raise KeyError(f'Slug desconocido: {slug!r}. Agregalo a clubes_map.py')
    return CLUBES[slug]


def league_id(copa: str) -> int:
    if copa not in LEAGUE_BY_COPA:
        raise KeyError(f'Copa desconocida: {copa!r}. Usá libertadores | sudamericana | "" (liga)')
    return LEAGUE_BY_COPA[copa]


def estadisticas_path(slug: str, copa: str = '') -> str:
    """Devuelve el path relativo al JSON de estadísticas para ese club + copa."""
    suffix = f'_{copa}' if copa else ''
    return f'data/estadisticas/{slug}{suffix}.json'
