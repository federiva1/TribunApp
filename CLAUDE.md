# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TribunApp is a static fan engagement SPA for all 30 clubs of the Argentine Liga Profesional + Selección Nacional. No build system, no framework — pure HTML + CSS + JS. Hosted on GitHub Pages.

## No Build / No Tests

There is no build step, bundler, linter, or test suite. Development is direct file editing. To preview locally, open the HTML files directly in a browser or use any static file server (e.g. `python -m http.server 8080`).

## Python Scripts

Run from the project root:

```bash
# Scrape player squads + photos for all 30 clubs from FotMob
python scripts/scraper_planteles.py

# Scrape eligible players for the Selección
python scripts/scraper_seleccion.py

# Update rivalActual for each club in js/clubes.js (reads next fixtures from API)
python scripts/fetch_proximos_partidos.py
```

## Architecture

### Single shared template: `club.html`
All 30 clubs use the same file, parametrized via `?c=slug`. On load it reads the slug, looks up `CLUBES_CONFIG[slug]` in `js/clubes.js`, applies `--club-color` as a CSS variable, and loads the player squad from `data/planteles/{slug}.json`. The four sections (Formación, Puntajes, Fechas, Tabla) are overlay `div`s toggled via `display:none/block`, not separate pages.

### Central config: `js/clubes.js`
The single source of truth for all 30 clubs. Defines three globals:
- `CLUBES_CONFIG` — per-club: `id` (api-sports ID), `nombre`, `color`, `rivalActual`, `squad` (populated at runtime from JSON)
- `ESCUDO_MAP` — api-sports ID → slug (used in both index.html and club.html to resolve escudo paths like `escudos/{slug}.png`)
- `NOMBRE_CORTO_T` — api-sports ID → short display name (used in table rendering)

### Data flow
- **Live standings**: fetched from `https://v3.football.api-sports.io/standings?league=128&season=2026` with key `b8bbfc856fd5cf12cd7d697b2b01887d`. The API returns 4 groups: `[0]` Zona A Apertura, `[1]` Zona B Apertura, `[2]` Anual, `[3]` Promedios. Group order can be swapped (Zona B first), so both index.html and club.html detect this by checking if the first group name contains `"b"`.
- **Player squads**: static JSON at `data/planteles/{slug}.json`. Fields: `num`, `name`, `fid`, `nationality`, `position`.
- **Player photos**: `fotos/{slug}/{fid}.png` — sourced via FotMob scraper. Photos load with `onerror` fallbacks to show jersey number.
- **Community data (formaciones + puntajes)**: read/written to Supabase (URL and anon key are hardcoded in `club.html`). The `club` column (slug) differentiates the 30 teams in a shared table. `device_id` is a localStorage UUID used to prevent duplicate votes.

### Supabase tables
- `formaciones(id, club, rival, jugadores, likes, dislikes, device_id)` — `jugadores` is a JSON array of player objects placed on pitch
- `puntajes(id, club, rival, puntajes)` — `puntajes` is a JSON object mapping player name → score 1-10

### copas.html
Hardcoded arrays `LIBERTADORES_SLUGS` and `SUDAMERICANA_SLUGS` define which Argentine clubs participate. Groups are fetched live from api-sports.io (Libertadores: `league=13`, Sudamericana: `league=11`). Argentine teams are detected by checking against `ARG_IDS` (all IDs from `CLUBES_CONFIG`).

### Simulator (index.html tabla overlay)
`FIXTURE_T` is a hardcoded object with remaining fixture lists for Zona A and Zona B (fechas 13–16). Sim mode stores a `tSimState` object with current points per team and a `resultados` map keyed by `"fecha-homeId-awayId"`. `tSimAuto()` picks a random result weighted by recent form. The playoff bracket renders as an inline SVG using `foreignObject` for club crests.

### seleccion.html
Manages a `convocados` array (up to 26 players). Players are sourced from `data/seleccion.json` (last 5 match squad) plus a live search across all 30 `data/planteles/{slug}.json` files. Formation logic is identical to `club.html` but operates on convocados instead of a fixed squad.

## Key Conventions

- **Slug** is the canonical identifier across all files: URL param, JSON filename, escudo filename, Supabase `club` column, and `CLUBES_CONFIG` key all use the same slug (e.g. `bocajuniors`, `riverplate`).
- **api-sports ID** is used only when talking to the external API and in `ESCUDO_MAP`/`NOMBRE_CORTO_T`. Always convert to slug before writing to Supabase or loading local assets.
- Fixture data (`FIXTURE_T`) and copa participants are hardcoded and must be manually updated each season/round.
- `rivalActual` in `js/clubes.js` is updated by running `fetch_proximos_partidos.py` before each matchday.
