"""Convierte AJ_Apertura2026_Completo.xlsx a data/estadisticas/argentinosjuniors.json.

Lee 12 hojas de partidos (formato 'MM-DD  Rival'), ignora 'Análisis', y agrega
la hoja 'Acumulado'. Se accede por índice de columna porque varias columnas
('Goles', 'xG', 'Asistencias'...) se repiten en distintas secciones.

Uso:
    python scripts/excel_to_json.py

Dependencias: pandas, openpyxl.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXCEL = ROOT / "AJ_Apertura2026_Completo.xlsx"
OUT_DIR = ROOT / "data" / "estadisticas"
OUT_FILE = OUT_DIR / "argentinosjuniors.json"

SKIP_SHEETS = {"Acumulado", "Análisis"}

# (clave_json, índice_columna_en_excel). La columna "Pases precisos" viene como
# string "acertados/intentados" en los partidos y como NaN en el acumulado, así
# que se procesa aparte (PASES_COL_*).
MATCH_COLS = [
    ("minutos", 1),
    ("goles", 2),
    ("asistencias", 3),
    ("xG", 4),
    ("xA", 5),
    ("xGxA", 6),
    ("accDefensivas", 7),
    ("disparos", 11),
    ("toques", 16),
]
PASES_COL_MATCH = 17

ACUM_COLS = [
    ("partidos", 1),
    ("minutos", 2),
    ("goles", 3),
    ("asistencias", 4),
    ("xG", 5),
    ("xA", 6),
    ("xGxA", 7),
    ("accDefensivas", 8),
    ("disparos", 12),
    ("toques", 17),
]
PASES_COL_ACUM = 18

TITLE_RE = re.compile(
    r"Argentinos Juniors\s+vs\s+(?P<rival>.+?)\s*\|\s*"
    r"(?P<date>\d{4}-\d{2}-\d{2})\s*\|\s*"
    r"(?P<condicion>Local|Visitante)\s*\|\s*"
    r"(?P<resultado>.+)$"
)


def clean(value):
    """NaN → None; números enteros que vienen como float → int."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value.is_integer():
            return int(value)
        return round(value, 2)
    return value


def parse_title(raw: str) -> dict:
    s = str(raw).strip()
    m = TITLE_RE.match(s)
    if not m:
        raise ValueError(f"No pude parsear el título: {raw!r}")
    return {
        "rival": m.group("rival").strip(),
        "date": m.group("date"),
        "condicion": m.group("condicion"),
        "resultado": m.group("resultado").strip(),
    }


def parse_pases(value):
    """'27/32' → (27, 32). NaN/inválido → (None, None)."""
    if pd.isna(value):
        return None, None
    s = str(value).strip()
    if "/" not in s:
        return None, None
    a, b = s.split("/", 1)
    try:
        return int(a.strip()), int(b.strip())
    except ValueError:
        return None, None


def parse_player_row(row, cols, pases_col):
    """Devuelve dict {nombre, ...stats} o None si la fila no tiene jugador."""
    nombre = row.iloc[0]
    if pd.isna(nombre):
        return None
    out = {"nombre": str(nombre).strip()}
    for key, idx in cols:
        out[key] = clean(row.iloc[idx])
    pa, pi = parse_pases(row.iloc[pases_col])
    out["pasesAcertados"] = pa
    out["pasesIntentados"] = pi
    return out


def parse_match_sheet(df: pd.DataFrame, fecha_num: int) -> dict:
    head = parse_title(df.iloc[0, 0])
    jugadores = []
    for i in range(3, df.shape[0]):
        p = parse_player_row(df.iloc[i], MATCH_COLS, PASES_COL_MATCH)
        if p is None:
            continue
        minutos = p.get("minutos")
        p["jugo"] = bool(minutos) and minutos > 0
        # ordenar para que "nombre" y "jugo" queden al principio
        ordered = {"nombre": p["nombre"], "jugo": p["jugo"]}
        for key, _ in MATCH_COLS:
            ordered[key] = p[key]
        ordered["pasesAcertados"] = p["pasesAcertados"]
        ordered["pasesIntentados"] = p["pasesIntentados"]
        jugadores.append(ordered)
    return {
        "fecha": fecha_num,
        "rival": head["rival"],
        "date": head["date"],
        "condicion": head["condicion"],
        "resultado": head["resultado"],
        "jugadores": jugadores,
    }


def parse_acumulado(df: pd.DataFrame) -> list[dict]:
    out = []
    for i in range(3, df.shape[0]):
        p = parse_player_row(df.iloc[i], ACUM_COLS, PASES_COL_ACUM)
        if p is None:
            continue
        out.append(p)
    return out


def main() -> int:
    if not EXCEL.exists():
        print(f"ERROR: no encuentro {EXCEL}", file=sys.stderr)
        return 1

    xl = pd.ExcelFile(EXCEL)
    match_sheets = [s for s in xl.sheet_names if s not in SKIP_SHEETS]

    partidos = []
    for fecha_num, sheet in enumerate(match_sheets, start=1):
        df = pd.read_excel(EXCEL, sheet_name=sheet, header=None)
        partidos.append(parse_match_sheet(df, fecha_num))

    if "Acumulado" in xl.sheet_names:
        df_acum = pd.read_excel(EXCEL, sheet_name="Acumulado", header=None)
        acumulado = parse_acumulado(df_acum)
    else:
        acumulado = []

    payload = {
        "club": "argentinosjuniors",
        "temporada": "Apertura 2026",
        "partidos": partidos,
        "acumulado": acumulado,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OK: {len(partidos)} partidos, {len(acumulado)} jugadores en acumulado")
    print(f"     escrito a {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
