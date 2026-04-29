# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TribunApp is a static fan engagement SPA for all 30 clubs of the Argentine Liga Profesional + Selección Nacional. No build system, no framework — pure HTML + CSS + JS. Deployed on Vercel (production) and GitHub Pages.

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

# Generate data/fixtures/{slug}.json for all 30 clubs (Liga) + copa files
python scripts/fetch_fixtures.py          # liga + copas
python scripts/fetch_fixtures.py --liga   # only liga
python scripts/fetch_fixtures.py --copas  # only copa files

# Automation scripts (also run by GitHub Actions — require API_SPORTS_KEY env var)
python scripts/update_estado.py    # poll api-sports for FT matches → open puntajes
python scripts/close_puntajes.py   # close puntajes 48h after matchDate

# Generar data/estadisticas/argentinosjuniors.json desde el Excel en la raíz
python scripts/excel_to_json.py

# (One-shot) migrar votos legacy de la Supabase de Formaaajcion → TribunApp
python scripts/migrar_votos_formaaajcion.py            # dry-run (default)
python scripts/migrar_votos_formaaajcion.py --execute  # migra de verdad
python scripts/migrar_votos_formaaajcion.py --check    # estado del destino
```

## Architecture

### Single shared template: `club.html`
All 30 clubs use the same file, parametrized via `?c=slug`. On load it reads the slug, looks up `CLUBES_CONFIG[slug]` in `js/clubes.js`, applies `--club-color` as a CSS variable, and loads the player squad from `data/planteles/{slug}.json`.

Sections are overlay `div`s toggled via `display:none/block`. Auth state controls which sections appear in the bottom nav:
- **Guests**: Formación (hero), Puntajes (hero), VER FECHAS (bottom bar — shows current fecha only)
- **Logged-in**: same + bottom bar expands to FIXTURE | VER FECHAS | ESTADÍSTICAS

`renderSecondaryRow()` re-renders the bottom bar on auth change.

### Auth system: `js/config.js` + `js/auth.js` + `js/auth-ui.js`

Script load order is critical across all 4 pages — must be exactly:
```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="js/config.js"></script>
<script src="js/auth.js"></script>
<script src="js/auth-ui.js"></script>
<script>
  initAuthHeaderBtn();
  renderSecondaryRow();          <!-- club.html only -->
  onAuthChange(() => renderSecondaryRow()); <!-- club.html only -->
  initAuth();
</script>
```

- **`js/config.js`**: declares `var currentUser = null` (must be `var`, not `let`, so it's hoisted and available to inline scripts that load before auth.js), plus `SUPABASE_URL` and `SUPABASE_KEY`.
- **`js/auth.js`**: Supabase auth client. Exports `window.onAuthChange`, `initAuth`, `signIn`, `signUp`, `signOut`. `currentUser` is the global from config.js (not re-declared here). `initAuth()` reads existing session + subscribes to `onAuthStateChange`.
- **`js/auth-ui.js`**: IIFE that injects modal CSS, creates modal DOM, and exposes `window.openAuthModal`, `window.closeAuthModal`, `window.initAuthHeaderBtn`. The `#auth-header-btn` must be hardcoded in each page's HTML (not created dynamically) — `initAuthHeaderBtn()` finds the existing element and attaches handlers. `_renderAuthBtn()` updates button appearance on auth change.

### Central config: `js/clubes.js`
The single source of truth for all 30 clubs. Defines three globals:
- `CLUBES_CONFIG` — per-club: `id` (api-sports ID), `nombre`, `nombreCorto`, `color`, `rivalActual`, `squad` (populated at runtime from JSON)
- `ESCUDO_MAP` — api-sports ID → slug
- `NOMBRE_CORTO_T` — api-sports ID → short display name

### Data flow
- **Live standings**: `https://v3.football.api-sports.io/standings?league=128&season=2026` with key `b8bbfc856fd5cf12cd7d697b2b01887d`. Returns 4 groups: `[0]` Zona A, `[1]` Zona B, `[2]` Anual, `[3]` Promedios. Group order can swap (Zona B first) — both index.html and club.html detect this by checking if the first group name contains `"b"`.
- **Live fixture** (club.html FIXTURE section): `https://v3.football.api-sports.io/fixtures?team={id}&season=2026&league=128` — same API key.
- **Static fixture data** (club.html VER FECHAS section): `data/fixtures/{slug}.json` for liga, `data/fixtures/{slug}_libertadores.json` / `data/fixtures/{slug}_sudamericana.json` for copa teams. Format: array of `{ num, fecha, rival, local, goles }` where `goles` is `[argGoals, rivalGoals]` or `null` if unplayed. Generated by `scripts/fetch_fixtures.py`.
- **Stats por jugador** (club.html ESTADÍSTICAS section): `data/estadisticas/{slug}.json` — solo `argentinosjuniors` por ahora. Generado por `scripts/excel_to_json.py` desde `AJ_Apertura2026_Completo.xlsx` en la raíz del repo (~108KB, commiteado). Estructura: `{ club, temporada, partidos: [{ fecha, rival, date, condicion, resultado, jugadores: [{nombre, jugo, minutos, goles, asistencias, xG, xA, xGxA, accDefensivas, disparos, toques, pasesAcertados, pasesIntentados}] }], acumulado: [...] }`. La columna "Pases precisos" del Excel viene como string `"acertados/intentados"` y se separa en dos campos numéricos para permitir ordenamiento.
- **Player squads**: static JSON at `data/planteles/{slug}.json`. Fields: `num`, `name`, `fid`, `nationality`, `position`.
- **Player photos**: `fotos/{slug}/{fid}.png` — sourced via FotMob scraper.
- **Community data**: read/written to Supabase. The `club` column (slug) differentiates the 30 teams.
- **Puntajes gate**: `data/estado.json` — one entry per club with `{ puntajesOpen, rival, matchDate }`. Fetched by `club.html` with `cache: 'no-store'` on every load. Updated by GitHub Actions (see below).

### Supabase tables
- `formaciones(id, club, rival, match_date, jugadores, likes, dislikes, device_id, user_id, equipo_hincha)` — `jugadores` is a JSON array of player objects placed on pitch. Logged-in users populate `user_id` + `equipo_hincha`; guests use `device_id` (localStorage UUID).
- `puntajes(id, club, rival, match_date, puntajes, user_id, equipo_hincha)` — `puntajes` is a JSON object mapping player num → score 1-10.
- `perfiles(id, equipo_hincha)` — one row per Supabase user, `id` matches `auth.users.id`.

`match_date` (type `date`) was added via:
```sql
ALTER TABLE formaciones ADD COLUMN IF NOT EXISTS match_date date;
ALTER TABLE puntajes    ADD COLUMN IF NOT EXISTS match_date date;
```
All queries filter by `club + rival + match_date` so the same two teams can meet multiple times (copa group stage, liga playoffs) without mixing data. `match_date` is resolved at runtime from `data/fixtures/{slug}.json` — the first entry where `rival === RIVAL && goles === null` gives the current match date (`FECHA_ACTUAL`). It is optional in queries (falls back to rival-only filter for rows inserted before this column existed).

### Auth-gated sections in club.html
`renderSecondaryRow()` controls the bottom nav bar and re-runs on every auth change:
- **Guests**: one button — VER FECHAS → `renderCurrentFechaGuest()` (current fecha only + CTA to register)
- **Logged-in**: three buttons — FIXTURE | VER FECHAS | ESTADÍSTICAS

When `COPA` URL param is set (`'libertadores'` or `'sudamericana'`), las secciones se acomodan a la copa:
- FIXTURE usa `league=13` (Libertadores) o `league=11` (Sudamericana) en vez de `128`
- VER FECHAS carga `data/fixtures/{slug}_libertadores.json` o `{slug}_sudamericana.json`
- ESTADÍSTICAS no tiene data específica de copa: muestra el JSON de Apertura para `argentinosjuniors` igualmente, o "próximamente" para el resto

#### ESTADÍSTICAS (`renderStats()` en club.html)
Gateada por `CLUB_SLUG`: solo `argentinosjuniors` carga datos; el resto muestra "próximamente" sin fetch. Dos tabs sincronizados por un selector de fecha único (`Acumulado` + 12 fechas):
- **Estadísticas de la web** — agrega de las tablas `formaciones` y `puntajes` de Supabase. Vista acumulada: cuántas fechas cada jugador fue elegido titular (barra "X/12"). Vista por fecha: dos bloques apilados estilo Formaaajcion — (a) tier list de formaciones (5 niveles por % de votos, 81-100% a 0-20%), donde los chips de jugadores con `jugo:true` en el JSON llevan ring verde para preservar la comparación TribunApp/real; (b) podio de puntajes 1/2/4/4 con medallas 🥇🥈🥉. Reutiliza el CSS `.tier-*` y las funciones `makeScoreCard`/`addGrid` que ya existen en `club.html` (originalmente del flujo `puntajes` hero).
- **Estadísticas del equipo** — del JSON. Vista acumulada: tabla ordenable de todos los jugadores. Vista por fecha: header del partido + tabla solo de los que jugaron.

Estado del módulo en el global `_stats = { data, formaciones, puntajes, tab, fechaSel, sortKey, sortAsc }`. Las tres fuentes (JSON, formaciones, puntajes) se cargan en paralelo en el primer abrir y quedan cacheadas en memoria. Matching de nombres entre el JSON estadísticas y el squad usa `_statsNorm()` (strip accents + lowercase) con fallback por primer+último apellido — necesario porque el Excel a veces escribe nombres distinto al `data/planteles/{slug}.json` (ej: "Erik Fernando Godoy" vs "Érik Godoy", "Gonzalo Siri Payer" vs "Gonzalo Siri").

### Puntajes automation (`data/estado.json` + GitHub Actions)

`data/estado.json` is a static file committed to the repo:
```json
{
  "bocajuniors": { "puntajesOpen": false, "rival": "Central Cordoba de Santiago", "matchDate": "2026-05-03" },
  ...
}
```

Three scheduled workflows in `.github/workflows/`:
- **`update-fixtures.yml`** — runs `fetch_fixtures.py` at 9h and 21h UTC to keep fixture JSONs current.
- **`match-monitor.yml`** — runs `update_estado.py` every 15 min; when a match is FT it sets `puntajesOpen: true`.
- **`close-puntajes.yml`** — runs `close_puntajes.py` every 6h; closes puntajes where `matchDate` is >48h in the past.

All three use `stefanzweifel/git-auto-commit-action@v5` with `[skip ci]` in the commit message to avoid loops. They require the `API_SPORTS_KEY` secret set in GitHub → Settings → Secrets.

In `club.html`, `PUNTAJES_OPEN` is loaded async from `estado.json` (only for liga, not copa context). It gates the puntajes section in `openSection('scores')`.

### copas.html
Hardcoded arrays `LIBERTADORES_SLUGS` and `SUDAMERICANA_SLUGS` define Argentine participants. Groups fetched live from api-sports (Libertadores: `league=13`, Sudamericana: `league=11`).

### Simulator (index.html tabla overlay)
`FIXTURE_T` is a hardcoded object with remaining fixture lists for Zona A and Zona B (fechas 13–16). Sim mode stores a `tSimState` object with current points per team and a `resultados` map keyed by `"fecha-homeId-awayId"`. The playoff bracket renders as an inline SVG.

### seleccion.html
Manages a `convocados` array (up to 26 players). Players sourced from `data/seleccion.json` plus live search across all 30 `data/planteles/{slug}.json` files.

## Key Conventions

- **Slug** is the canonical identifier: URL param, JSON filenames, escudo path, Supabase `club` column, and `CLUBES_CONFIG` key all use the same slug (e.g. `bocajuniors`, `argentinosjuniors`).
- **api-sports ID** is used only when talking to the external API and in `ESCUDO_MAP`/`NOMBRE_CORTO_T`. Always convert to slug before writing to Supabase or loading local assets.
- `rivalActual` in `js/clubes.js` must match the rival name used in `data/fixtures/{slug}.json` exactly — this string is used as the Supabase `rival` column value.
- `var currentUser = null` in config.js is intentional — `var` hoisting makes it available to inline scripts before auth.js loads. Do not change to `let` or `const`.
- `data/fixtures/{slug}.json` exists for all 30 clubs (liga) and 12 copa files. Regenerated by `fetch_fixtures.py`.
- `data/estado.json` drives puntajes open/close state. Update manually with `update_estado.py` or via GitHub Actions.
- Fixture data (`FIXTURE_T`) and copa participants are hardcoded and must be manually updated each season/round.
- `rivalActual` in `js/clubes.js` is updated by running `fetch_proximos_partidos.py` before each matchday.
- `fetch_fixtures.py` and `update_estado.py` both read `API_SPORTS_KEY` from the environment (fallback to hardcoded key for local use).
- `data/estadisticas/{slug}.json` solo existe para `argentinosjuniors`. Para habilitar otro club: generar el archivo (con un Excel equivalente al de AJ) y quitar el gate en `renderStats()` de `club.html` (la línea `if (CLUB_SLUG !== 'argentinosjuniors')`).
- `AJ_Apertura2026_Completo.xlsx` en la raíz es la fuente de verdad para las stats individuales de AJ. `scripts/excel_to_json.py` lee por **índice de columna** (no por nombre) porque varias columnas se repiten entre las secciones del Excel (Top Estadísticas, Ataque, Pases, Defensa, Duelos, Portero) — ej: "Goles" aparece en col 2 (Top) y col 8 (Ataque).
- `scripts/migrar_votos_formaaajcion.py` es one-shot. Ya se ejecutó una vez: 107 formaciones + 114 puntajes (Banfield, Independiente Rivadavia, Atlético Tucumán) pasaron de la Supabase legacy `igfencxdekvtfspsskwd` a la de TribunApp con `club='argentinosjuniors'`. No volver a correr con `--execute` — duplica filas.
