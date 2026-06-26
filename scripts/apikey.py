"""Carga la API key de api-sports sin hardcodearla en el repo.

Prioridad:
  1. Variable de entorno API_SPORTS_KEY (la usan los GitHub Actions vía secret).
  2. Archivo local scripts/.apikey (gitignored) con la key en una sola línea
     (para correr los scripts en la compu).

Si no encuentra ninguna, aborta con un mensaje claro.
"""
import os
from pathlib import Path


def get_api_key() -> str:
    k = os.environ.get('API_SPORTS_KEY')
    if k and k.strip():
        return k.strip()
    f = Path(__file__).with_name('.apikey')
    if f.exists():
        v = f.read_text(encoding='utf-8').strip()
        if v:
            return v
    raise SystemExit(
        'Falta la API key de api-sports. Seteá la variable de entorno '
        'API_SPORTS_KEY o creá el archivo scripts/.apikey con la key.'
    )


API_KEY = get_api_key()
