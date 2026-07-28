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
    'velezsarsfield':           {'apisports': 438,  'fotmob': None,  'nombre': 'Vélez Sarsfield'},
    'estudiantes':              {'apisports': 450,  'fotmob': None,  'nombre': 'Estudiantes de La Plata'},
    'bocajuniors':              {'apisports': 451,  'fotmob': None,  'nombre': 'Boca Juniors'},
    'defensayjusticia':         {'apisports': 442,  'fotmob': None,  'nombre': 'Defensa y Justicia'},
    'union':                    {'apisports': 441,  'fotmob': None,  'nombre': 'Unión de Santa Fe'},
    'lanus':                    {'apisports': 446,  'fotmob': None,  'nombre': 'Lanús'},
    'talleres':                 {'apisports': 456,  'fotmob': None,  'nombre': 'Talleres de Córdoba'},
    'independiente':            {'apisports': 453,  'fotmob': 10078, 'nombre': 'Independiente'},
    'sanlorenzo':               {'apisports': 460,  'fotmob': None,  'nombre': 'San Lorenzo'},
    'clubatleticoplatense':     {'apisports': 1064, 'fotmob': 10089, 'nombre': 'Platense'},
    'gimnasiamendoza':          {'apisports': 1066, 'fotmob': None,  'nombre': 'Gimnasia Mendoza'},
    'centralcordobadesantiago': {'apisports': 1065, 'fotmob': None,  'nombre': 'Central Córdoba'},
    'instituto':                {'apisports': 478,  'fotmob': None,  'nombre': 'Instituto'},
    'deportivoriestra':         {'apisports': 476,  'fotmob': 298629,'nombre': 'Deportivo Riestra'},
    'newellsoldboys':           {'apisports': 457,  'fotmob': None,  'nombre': "Newell's Old Boys"},
    'independienterivadavia':   {'apisports': 473,  'fotmob': None,  'nombre': 'Independiente Rivadavia'},
    'riverplate':               {'apisports': 435,  'fotmob': None,  'nombre': 'River Plate'},
    'belgrano':                 {'apisports': 440,  'fotmob': None,  'nombre': 'Belgrano'},
    'racingclub':               {'apisports': 436,  'fotmob': 10080, 'nombre': 'Racing Club'},
    'rosariocentral':           {'apisports': 437,  'fotmob': None,  'nombre': 'Rosario Central'},
    'tigre':                    {'apisports': 452,  'fotmob': None,  'nombre': 'Tigre'},
    'barracascentral':          {'apisports': 2432, 'fotmob': None,  'nombre': 'Barracas Central'},
    'sarmiento':                {'apisports': 474,  'fotmob': None,  'nombre': 'Sarmiento de Junín'},
    'huracan':                  {'apisports': 445,  'fotmob': None,  'nombre': 'Huracán'},
    'gimnasialp':               {'apisports': 434,  'fotmob': None,  'nombre': 'Gimnasia La Plata'},
    'banfield':                 {'apisports': 449,  'fotmob': None,  'nombre': 'Banfield'},
    'atleticotucuman':          {'apisports': 455,  'fotmob': None,  'nombre': 'Atlético Tucumán'},
    'aldosivi':                 {'apisports': 463,  'fotmob': None,  'nombre': 'Aldosivi'},
    'estudiantesderiocuarto':   {'apisports': 2424, 'fotmob': None,  'nombre': 'Est. de Río Cuarto'},
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
