"""Carga la API key de api-sports sin hardcodearla en el repo.

Prioridad:
  1. Variable de entorno API_SPORTS_KEY (la usan los GitHub Actions vía secret).
  2. Archivo local scripts/.apikey (gitignored) con la key en una sola línea
     (para correr los scripts en la compu).

Si no encuentra ninguna, aborta con un mensaje claro.

Modo proxy (sesiones en la nube de Claude Code): con API_SPORTS_VIA_PROXY=1 y sin
key a la vista, los scripts NO mandan el header: lo agrega el proxy de Anthropic
("API credential" del entorno, header x-apisports-key para v3.football.api-sports.io)
cuando el request ya salió de la VM. Así la key nunca entra a la sesión.
"""
import os
from pathlib import Path


def via_proxy() -> bool:
    return os.environ.get('API_SPORTS_VIA_PROXY', '').strip().lower() in ('1', 'true', 'yes', 'si')


def get_api_key() -> str:
    k = os.environ.get('API_SPORTS_KEY')
    if k and k.strip():
        return k.strip()
    f = Path(__file__).with_name('.apikey')
    if f.exists():
        v = f.read_text(encoding='utf-8').strip()
        if v:
            return v
    if via_proxy():
        return ''          # la pone el proxy del entorno; ver api_headers()
    raise SystemExit(
        'Falta la API key de api-sports. Seteá la variable de entorno '
        'API_SPORTS_KEY o creá el archivo scripts/.apikey con la key.'
    )


def api_headers() -> dict:
    """Headers para api-sports. Vacío en modo proxy: mandar un header falso podría
    pisar o duplicar el que inyecta el proxy."""
    k = get_api_key()
    return {'x-apisports-key': k} if k else {}


API_KEY = get_api_key()
