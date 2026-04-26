"""Migra formaciones y puntajes desde la Supabase legacy de Formaaajcion (solo
Argentinos Juniors) hacia la Supabase de TribunApp, agregando los campos
`club` y `match_date` que la nueva schema requiere.

Uso:
    python scripts/migrar_votos_formaaajcion.py            # dry-run (no escribe)
    python scripts/migrar_votos_formaaajcion.py --execute  # migra realmente

Dependencias: solo stdlib.

Idempotencia: el script NO chequea duplicados antes de insertar. Correrlo dos
veces va a crear copias. Conviene asegurar que la tabla destino esté vacía
para `club=argentinosjuniors` antes de ejecutar (ver `--check`).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

# Origen — Supabase de Formaaajcion (legacy AAAJ-only)
OLD_URL = "https://igfencxdekvtfspsskwd.supabase.co"
OLD_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlnZmVuY3hkZWt2dGZzcHNza3dkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM5NTUyOTEsImV4cCI6MjA4OTUzMTI5MX0.KVpBNe_p7OLAtZPMFUTpTbKmLCl-G63f53gvFJreinc"

# Destino — Supabase de TribunApp
NEW_URL = "https://ieujdkthaoujtnndkiqo.supabase.co"
NEW_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlldWpka3RoYW91anRubmRraXFvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMTEwOTYsImV4cCI6MjA5MTc4NzA5Nn0.FDzVx-W3v48Eq9_hSzsghP1Q8ES4e70S7MN2koGT5wY"

CLUB_SLUG = "argentinosjuniors"

# Mapa rival → match_date (Apertura 2026, fechas confirmadas vía api-sports)
DATE_MAP = {
    "Banfield": "2026-04-06",
    "Independiente Rivadavia": "2026-04-11",
    "Atlético Tucumán": "2026-04-19",
}


def get(url: str, key: str, path: str) -> list:
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Range": "0-9999",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def post(url: str, key: str, table: str, payload: dict) -> None:
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        r.read()


def fetch_old() -> tuple[list, list]:
    forms = get(OLD_URL, OLD_KEY, "formaciones?select=*")
    punts = get(OLD_URL, OLD_KEY, "puntajes?select=*")
    return forms, punts


def check_destination() -> None:
    forms = get(
        NEW_URL,
        NEW_KEY,
        f"formaciones?select=id&club=eq.{CLUB_SLUG}&limit=1",
    )
    punts = get(
        NEW_URL,
        NEW_KEY,
        f"puntajes?select=id&club=eq.{CLUB_SLUG}&limit=1",
    )
    print(f"TribunApp argentinosjuniors:")
    print(f"  formaciones existentes: {'sí' if forms else 'ninguna'}")
    print(f"  puntajes existentes:    {'sí' if punts else 'ninguno'}")
    if forms or punts:
        print("\n  AVISO: ya hay datos. Si migrás de nuevo vas a duplicar.")


def map_formacion(row: dict) -> dict | None:
    rival = row.get("rival")
    md = DATE_MAP.get(rival)
    if not md:
        return None
    return {
        "club": CLUB_SLUG,
        "rival": rival,
        "match_date": md,
        "jugadores": row.get("jugadores"),
        "likes": row.get("likes", 0) or 0,
        "dislikes": row.get("dislikes", 0) or 0,
        "device_id": row.get("device_id"),
        # created_at: dejamos que el destino use now() — preservar el original
        # requeriría tocar la columna y RLS.
    }


def map_puntaje(row: dict) -> dict | None:
    rival = row.get("rival")
    md = DATE_MAP.get(rival)
    if not md:
        return None
    return {
        "club": CLUB_SLUG,
        "rival": rival,
        "match_date": md,
        "puntajes": row.get("puntajes"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="Migrar de verdad (default: dry-run)")
    ap.add_argument("--check", action="store_true", help="Solo chequear estado del destino")
    args = ap.parse_args()

    if args.check:
        check_destination()
        return 0

    print("=== Estado del destino ===")
    check_destination()

    print("\n=== Datos del origen ===")
    old_forms, old_punts = fetch_old()
    print(f"  formaciones origen: {len(old_forms)}")
    print(f"  puntajes origen:    {len(old_punts)}")

    # Validar rivales y mapear
    new_forms = [map_formacion(r) for r in old_forms]
    new_punts = [map_puntaje(r) for r in old_punts]

    skipped_forms = [r for r, m in zip(old_forms, new_forms) if m is None]
    skipped_punts = [r for r, m in zip(old_punts, new_punts) if m is None]
    new_forms = [m for m in new_forms if m is not None]
    new_punts = [m for m in new_punts if m is not None]

    if skipped_forms or skipped_punts:
        rivals_skipped = set(r["rival"] for r in skipped_forms + skipped_punts)
        print(f"\n  AVISO: {len(skipped_forms)} formaciones y {len(skipped_punts)} puntajes")
        print(f"  con rivales sin match_date conocido: {rivals_skipped}")
        print(f"  Agregalos a DATE_MAP en el script si querés migrarlos.")

    print("\n=== Resumen de la migración ===")
    from collections import Counter
    fc = Counter((f["rival"], f["match_date"]) for f in new_forms)
    pc = Counter((p["rival"], p["match_date"]) for p in new_punts)
    print(f"  Formaciones a migrar ({len(new_forms)}):")
    for (r, d), n in fc.items():
        print(f"    {r:30} {d}  -> {n}")
    print(f"  Puntajes a migrar ({len(new_punts)}):")
    for (r, d), n in pc.items():
        print(f"    {r:30} {d}  -> {n}")

    if not args.execute:
        print("\n[DRY-RUN] No se escribió nada. Volvé a correr con --execute para migrar.")
        return 0

    print("\n=== Migrando ===")
    ok_f = err_f = ok_p = err_p = 0
    for f in new_forms:
        try:
            post(NEW_URL, NEW_KEY, "formaciones", f)
            ok_f += 1
        except urllib.error.HTTPError as e:
            err_f += 1
            print(f"  formacion error ({f['rival']}): {e.code} {e.read()[:200]}")
    for p in new_punts:
        try:
            post(NEW_URL, NEW_KEY, "puntajes", p)
            ok_p += 1
        except urllib.error.HTTPError as e:
            err_p += 1
            print(f"  puntaje error ({p['rival']}): {e.code} {e.read()[:200]}")

    print(f"\n  formaciones: {ok_f} OK, {err_f} error")
    print(f"  puntajes:    {ok_p} OK, {err_p} error")
    return 0 if (err_f == 0 and err_p == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
