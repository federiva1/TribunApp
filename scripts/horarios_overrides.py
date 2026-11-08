"""Horarios confirmados por la AFA que la API todavía no tiene.

`data/horarios_overrides.json`: {"{local}-{visitante}": {"hora": "2026-11-07T17:30:00-03:00",
"api_original": "2026-11-08T21:00:00+00:00"}} (slugs de js/clubes.js).

Se aplica SOLO mientras la API siga devolviendo `api_original` (el horario de relleno) y el
partido no haya terminado: si la API cambia por su cuenta, gana la API. Así un refresco de
fixtures no deshace el horario a mano ni pisa uno nuevo de la API.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ARCHIVO = Path(__file__).resolve().parent.parent / 'data' / 'horarios_overrides.json'


def _utc(iso):
    return datetime.fromisoformat(iso).astimezone(timezone.utc)


def cargar():
    try:
        return json.loads(ARCHIVO.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def hora_para(local, visitante, api_iso, terminado=False):
    """Devuelve el ISO a usar (en UTC, formato de la API) o None si no hay override aplicable."""
    if terminado:
        return None
    o = cargar().get(f'{local}-{visitante}')
    if not o:
        return None
    try:
        if _utc(api_iso) != _utc(o['api_original']):
            return None            # la API ya cambió el horario: manda la API
        return _utc(o['hora']).isoformat()
    except Exception:
        return None
