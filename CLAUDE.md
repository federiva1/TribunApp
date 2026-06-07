# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TribunApp is a static fan engagement SPA for all 30 clubs of the Argentine Liga Profesional + Selección Nacional. No build system, no framework — pure HTML + CSS + JS. Deployed on Vercel (production) and GitHub Pages.

`FLUJO.md` complementa este doc con el ciclo de vida de cada fecha (pre-partido → FT → scraping → cierre de puntajes) y el plan de automatización.

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

# === Stats por partido (genéricos, post-partido) ===

# Stats globales del partido (api-sports /fixtures/statistics) → data/estadisticas/{slug}[_copa].json
python scripts/fetch_match_stats.py                                          # default: AAAJ liga, 4 rivales con votos migrados
python scripts/fetch_match_stats.py --slug racingclub --copa sudamericana    # otro club + copa
python scripts/fetch_match_stats.py --slug clubatleticoplatense --date 2026-04-29 --include-pending

# Player stats de FotMob (Playwright, ambos equipos del partido)
python scripts/scrape_fotmob_partidos.py                                     # AAAJ liga (PARTIDOS_AAAJ hardcodeado)
python scripts/scrape_fotmob_partidos.py --slug racingclub --copa sudamericana --date 2026-04-29
python scripts/scrape_fotmob_partidos.py --headed                            # browser visible (debug)

# === One-shots ya ejecutados — NO volver a correr con --execute ===

# Generar argentinosjuniors.json desde el Excel (deprecado a favor del scraper FotMob, mantenido)
python scripts/excel_to_json.py

# Migrar votos legacy de Formaaajcion → TribunApp (one-shot)
python scripts/migrar_votos_formaaajcion.py            # dry-run (default)
python scripts/migrar_votos_formaaajcion.py --execute  # migra de verdad
python scripts/migrar_votos_formaaajcion.py --check    # estado del destino
```

`scripts/clubes_map.py` es el módulo compartido con el mapping `slug → {apisports_id, fotmob_id, nombre}` y los helpers `lookup()`, `league_id()`, `estadisticas_path()`. Los scripts de stats lo importan. Los `fotmob_id` se van completando a medida que extendemos la app a nuevos clubes (hoy AAAJ + Platense + Riestra + Racing).

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
The single source of truth for all 30 clubs (frontend). Defines three globals:
- `CLUBES_CONFIG` — per-club: `id` (api-sports ID), `nombre`, `nombreCorto`, `color`, `rivalActual`, `squad` (populated at runtime from JSON)
- `ESCUDO_MAP` — api-sports ID → slug
- `NOMBRE_CORTO_T` — api-sports ID → short display name

Para los scripts Python hay un equivalente: `scripts/clubes_map.py` (slug → `{apisports, fotmob, nombre}`).

### Data flow
- **Live standings**: `https://v3.football.api-sports.io/standings?league=128&season=2026` with key `b8bbfc856fd5cf12cd7d697b2b01887d`. Returns 4 groups: `[0]` Zona A, `[1]` Zona B, `[2]` Anual, `[3]` Promedios. Group order can swap (Zona B first) — both index.html and club.html detect this by checking if the first group name contains `"b"`.
- **Live fixture** (club.html FIXTURE section): `https://v3.football.api-sports.io/fixtures?team={id}&season=2026&league={league}` con `league` 128 (liga) / 13 (Libertadores) / 11 (Sudamericana).
- **Static fixture data** (club.html VER FECHAS section): `data/fixtures/{slug}.json` for liga, `data/fixtures/{slug}_libertadores.json` / `data/fixtures/{slug}_sudamericana.json` for copa teams. Format: array of `{ num, fecha, rival, local, goles }` where `goles` is `[argGoals, rivalGoals]` or `null` if unplayed. Generated by `scripts/fetch_fixtures.py` — excepto `argentinosjuniors.json` que se mantiene a mano (línea `if slug == 'argentinosjuniors': skipped (manual file)`).
- **Stats por partido + jugadores** (club.html ESTADÍSTICAS section): `data/estadisticas/{slug}[_copa].json` (suffixes `_libertadores`, `_sudamericana` para copa). Schema:
  ```json
  {
    "club": "argentinosjuniors", "temporada": "Apertura 2026",
    "partidos": [{
      "fecha": 13, "rival": "Banfield", "rivalId": 449, "rivalSlug": "banfield",
      "date": "2026-04-06", "condicion": "Local", "resultado": "3 - 2",
      "stats_partido": {
        "equipo": { "posesion": 67, "xG": 1.07, "tiros": 17, "tirosAlArco": 7,
                    "pasesAcertados": 485, "pasesIntentados": 552,
                    "faltas": 9, "corners": 9, "amarillas": 1, "rojas": null },
        "rival":  { ... }
      },
      "jugadores":      [ /* AAAJ — schema TribunApp (nombre, jugo, minutos, goles, ...) */ ],
      "jugadoresRival": [ /* mismo schema, para el rival */ ]
    }],
    "acumulado": [ /* totales por jugador AAAJ del torneo */ ]
  }
  ```
  El `fecha` viene del `league.round` de api-football (parseado del string "Apertura - 14"). Cuando el partido todavía no se jugó, `stats_partido` y `resultado` no están presentes (header básico solamente). `xG` se rellena sumando el xG individual cuando api-sports no lo provee (común en LPF).
- **Player squads**: static JSON at `data/planteles/{slug}.json`. Fields: `num`, `name`, `fid`, `nationality`, `position`. **Pueden tener `num` duplicados** (ej AAAJ #10 = Lescano y Florentín, #17 = Paredes y Ferreira, #33 = Riquelme y Pérez) porque más de un jugador comparte número entre titular/suplente o por movimientos de plantel. La sección ESTADÍSTICAS desambigua cruzando con `partido.jugadores[].nombre` de FotMob.
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
Es el campo canónico para identificar el partido. La sección ESTADÍSTICAS matchea filas Supabase ↔ partido del JSON usando `match_date === partido.date` (no por `rival` string, porque api-sports y Supabase usan grafías distintas: "Independ. Rivadavia" vs "Independiente Rivadavia", "Atletico Tucuman" vs "Atlético Tucumán"). El insert de votos resuelve `match_date` a runtime desde `data/fixtures/{slug}.json` — la primera entrada con `rival === RIVAL && goles === null` da el `FECHA_ACTUAL`.

### Auth-gated sections in club.html
`renderSecondaryRow()` controls the bottom nav bar and re-runs on every auth change:
- **Guests**: one button — VER FECHAS → `renderCurrentFechaGuest()` (current fecha only + CTA to register)
- **Logged-in**: three buttons — FIXTURE | VER FECHAS | ESTADÍSTICAS

When `COPA` URL param is set (`'libertadores'` or `'sudamericana'`):
- FIXTURE usa `league=13` / `league=11` en vez de `128`
- VER FECHAS carga `data/fixtures/{slug}_{copa}.json`
- ESTADÍSTICAS carga `data/estadisticas/{slug}_{copa}.json`. Si el archivo no existe, muestra "próximamente".

#### FIXTURE — toggle Apertura/Clausura
Para liga, una sola llamada a api-sports trae todos los partidos del año. El toggle filtra por `league.round` (busca "apertura"/"clausura" case-insensitive) con fallback al mes (≤6 = Apertura, ≥7 = Clausura). Default = torneo en curso según el mes de hoy. El toggle no aparece en contexto de copa.

#### ESTADÍSTICAS (`renderStats()` en club.html)
Sin gate por club — intenta cargar el JSON correspondiente; si no existe, muestra "próximamente" (no es un error). Dos tabs:
- **Equipo** (default — datos reales del partido) — scoreboard con escudos AAAJ + rival + resultado, bloque "Top estadísticas" estilo planilla (posesión / xG / tiros / disparos / pases con % / faltas / córners / tarjetas, con pill destacando al equipo con mayor valor), tabla de jugadores ordenable. Selector de fecha = solo fechas con `stats_partido` cargado + Acumulado. Default = última fecha jugada.
- **Página** (votos de Supabase) — vista por fecha: tier list de formaciones (5 tiers por % de votos: 81-100, 61-80, 41-60, 21-40, 0-20) + podio de puntajes 1/2/4/4 con medallas. Vista acumulada: suma global de votos sobre todas las fechas con datos.

Estado del módulo: global `_stats = { data, formaciones, puntajes, tab, fechaSel, sortKey, sortAsc }`. Las tres fuentes (JSON, formaciones, puntajes) se cargan secuencialmente (JSON primero — si no existe, fallback a "próximamente") y quedan cacheadas en memoria.

**Filtros importantes del podio de puntajes** (`_statsRenderPodio`):
1. **Solo jugadores que jugaron** — usa `partido.jugadores[].jugo === true` para excluir votos a no-convocados. Si alguien le puso puntaje a un jugador que no jugó, ese voto se descarta.
2. **Lookup por nombre, no por num** — los planteles tienen `num` duplicados; la función `_statsMatchSquad(j.nombre, squad)` busca el squad entry por nombre normalizado (tildes/case-insensitive), con fallback por primer+último apellido o solo apellido. Así el name+fid del podio sale del jugador real, no del primer match por num.
3. **Cutoff acumulado** — un jugador aparece en el podio acumulado solo si fue puntuado en al menos `Math.ceil(N/2)` de los partidos del scope (50%+). Para 4 fechas → mín. 2.

`_renderStatsTabWeb` usa la global `squad` cargada por `initSquad()` (no `CLUB.squad`, que nunca se completa). El tier list de formaciones prioriza `j.name` y `j.fid` del snapshot del vote sobre la lookup en squad por la misma razón de duplicados.

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

**Por automatizar** (ver `FLUJO.md`): un workflow `post-match-stats.yml` que dispare los scrapers (`fetch_match_stats.py` + `scrape_fotmob_partidos.py`) cuando `match-monitor` detecta FT, esperando ~30–60 min para que FotMob procese. Requiere agregar Playwright al runner (`pip install playwright && playwright install chromium`).

### copas.html
Hardcoded arrays `LIBERTADORES_SLUGS` and `SUDAMERICANA_SLUGS` define Argentine participants. Groups fetched live from api-sports (Libertadores: `league=13`, Sudamericana: `league=11`).

### Simulator (index.html tabla overlay)
`FIXTURE_T` is a hardcoded object with remaining fixture lists for Zona A and Zona B (fechas 13–16). Sim mode stores a `tSimState` object with current points per team and a `resultados` map keyed by `"fecha-homeId-awayId"`. The playoff bracket renders as an inline SVG.

### seleccion.html
Manages a `convocados` array (up to 26 players). Players sourced from `data/seleccion.json` plus live search across all 30 `data/planteles/{slug}.json` files.

## Mundial 2026 Module

Módulo separado del flujo de clubes argentinos. Todas las páginas del Mundial son standalone (no dependen de `js/clubes.js` ni Supabase).

### Páginas

- **`fixture.html`** — Fixture del Mundial. Muestra amistosos + todas las fases (Fase de Grupos, Octavos, Cuartos, Semis, Final). Datos en `data/fixtures/mundial.json`. La pill "Estadísticas" del header apunta a `estadisticas-torneo.html`.
- **`estadisticas-torneo.html`** — Landing de estadísticas del torneo. Sección superior: goleadores y asistidores globales (computados dinámicamente leyendo todos los JSONs de `data/partidos/`). Sección inferior: grilla de 48 selecciones. Selecciones con datos (`data/partidos/index.json` tiene entradas para ese slug) muestran "VER STATS" y linkan a `equipo.html?c={slug}`.
- **`equipo.html`** — Perfil de selección. Tiene una sección "estadísticas" que llama a `loadPartidosStats()`: busca en `data/partidos/index.json` los partidos de ese slug, muestra una card Acumulado + cards por partido. Cada card es un `<a href="estadisticas.html?p={id}&c={slug}">`.
- **`estadisticas.html`** — Vista de un partido específico. URL: `?p={partido-id}` + `?c={slug-equipo}` (opcional, para auto-seleccionar el tab del equipo visitante si se entra desde su perfil). Tiene dos tabs: **Estadísticas** (stats globales del partido) y **Jugadores** (switcher Local/Visitante con cards expandibles por jugador).

### Data

- **`data/fixtures/mundial.json`** — Array de partidos. Campos clave: `round`, `roundName`, `id` (FotMob ID), `stats_id` (ID del JSON en `data/partidos/`), `home`/`away` con `name`/`id`, `home_score`/`away_score`, `status.finished`. Si `stats_id` está presente y el partido está finalizado, `fixture.html` genera un link a `estadisticas.html?p={stats_id}`.
- **`data/partidos/index.json`** — Array de entradas de partidos con estadísticas disponibles: `{ id, local, visitante, fecha, goles_local, goles_visitante, competicion, estadio }`. El `id` es el filename base (ej. `"brazil-panama"`).
- **`data/partidos/{id}.json`** — Stats de un partido específico. Schema:
  ```json
  {
    "partido": { "local", "visitante", "goles_local", "goles_visitante", "fecha", "estadio", "competicion", "goles_detalle": { "local": [...], "visitante": [...] } },
    "top_stats": [ { "label", "local", "visitante", "tipo": "posesion|numero|texto", "local_val", "visitante_val" } ],
    "jugadores": {
      "{slug-local}": [ /* array de jugadores */ ],
      "{slug-visitante}": [ /* array de jugadores */ ]
    }
  }
  ```
  Schema de cada jugador:
  ```json
  {
    "nombre": "Carlos Harvey", "id": 1017520, "mvp": false, "portero": false,
    "min": 84, "goles": 1, "asist": 0,
    "top":    { "tiros_totales", "disparos_puerta", "oport_creadas", "grandes_oport", "acc_defensivas", "pases_precisos" },
    "ataque": { "toques", "toques_area", "regates", "pases_ultimo_tercio", "tiros_largos", "perdida_balon" },
    "defensa": { "acc_defensivas", "entradas", "interceptaciones", "recuperaciones", "despejes", "bloqueos", "regateado" },
    "duelos":  { "ganados", "perdidos", "terrestres", "aereos", "faltas", "faltas_recibidas" },
    "portero_stats": null  // o { "paradas", "goles_contra", "goles_evitados" } para porteros
  }
  ```
  Campos opcionales son `null` cuando FotMob no reporta el valor (se muestran como `—`). `regates` y `terrestres`/`aereos` son strings fracción (`"2/5"`). Los jugadores están ordenados por minutos desc.

### Escudos de selecciones

`escudos/{slug}.png` — el slug es el nombre en minúsculas sin espacios (ej. `brazil`, `panama`, `unitedstates`). El frontend de estas páginas no usa `CLUBES_CONFIG`.

### TribunApp Stats Module (community data — Mundial)

Pages showing community-generated data (formation votes + puntajes) for Mundial 2026:

- **`estadisticas-tribunapp.html`** — Landing page. Lists all 48 teams. Queries Supabase `formaciones?select=club` and `puntajes?select=club` to detect which teams have data. Teams with data appear first (gold "VER STATS" badge, clickable → `tribunapp-equipo.html?c={slug}`). Teams without data are grayed and non-clickable.
- **`tribunapp-equipo.html`** — Per-team community stats. Two tabs: **Acumulado** (all matches aggregated) and **Partidos** (one expandable card per match). For each match, shows formation vote % (player selection count / total submissions × 100) and puntajes average (sum of scores / count of votes per player). Uses `fetchAll()` → `agruparPorPartido()` keyed by `"${match_date}|${rival}"`.

### `data/estado_mundial.json` (Mundial puntajes gate)

```json
{
  "brazil": { "puntajesOpen": true, "rival": "panama", "match_date": "2026-05-31" },
  "panama": { "puntajesOpen": true, "rival": "brazil", "match_date": "2026-05-31" }
}
```

Fetched by `equipo.html` on load (with `?v=${Date.now()}` cache bust). Controls whether the puntajes section is open for a team. Also provides the `rival` and `match_date` for the active match — used to:
1. Scope localStorage keys: `${slug}_${match_date}_formacion` / `_formacion_data` / `_puntajes`
2. Filter Supabase formaciones/puntajes queries by `match_date`
3. Load match-specific players from `data/partidos/index.json` → `data/partidos/{id}.json` for the puntajes section (only players who actually played in that match)
4. Include `rival` and `match_date` in Supabase insert payloads

### Extracción de stats FotMob (manual vía Chrome MCP)

La API de FotMob para playerStats usa `stats` por sección como **objeto** (dict), no array. Al iterar:
```js
Object.entries(sec.stats || {}).forEach(([label, data]) => { ... })
```
Para Panama/selecciones, `p.name` es string directo (no `p.name.fullName`). El Chrome MCP trunca outputs largos — extraer un jugador a la vez con `JSON.stringify(window.__data[i])`.

## Key Conventions

- **Slug** is the canonical identifier: URL param, JSON filenames, escudo path, Supabase `club` column, and `CLUBES_CONFIG` key all use the same slug (e.g. `bocajuniors`, `argentinosjuniors`).
- **api-sports ID** is used only when talking to the external API and in `ESCUDO_MAP`/`NOMBRE_CORTO_T`. Always convert to slug before writing to Supabase or loading local assets.
- **FotMob ID** se mantiene en `scripts/clubes_map.py` para los scripts de scraping (no se usa en el frontend).
- `rivalActual` in `js/clubes.js` must match the rival name used in `data/fixtures/{slug}.json` exactly — this string is used as the Supabase `rival` column value.
- `var currentUser = null` in config.js is intentional — `var` hoisting makes it available to inline scripts before auth.js loads. Do not change to `let` or `const`.
- `data/fixtures/{slug}.json` exists for all 30 clubs (liga) and 12 copa files. Regenerated by `fetch_fixtures.py` (skips `argentinosjuniors.json` que es manual).
- `data/estado.json` drives puntajes open/close state. Update via `update_estado.py` o GitHub Actions.
- `data/estadisticas/{slug}[_copa].json` se genera con `fetch_match_stats.py` + `scrape_fotmob_partidos.py` (en ese orden — el segundo recomputa el `xG` sumando individual). Para fechas viejas de AAAJ existe `excel_to_json.py` (deprecado pero mantenido).
- `fetch_match_stats.py` y `scrape_fotmob_partidos.py` aceptan `--slug --copa --date` y resuelven IDs vía `clubes_map.py`. Para clubes nuevos hay que agregar el `fotmob` ID a ese archivo.
- `match_date` es el matching canónico para Supabase ↔ JSON. Nunca matchear por `rival` string.
- Los planteles pueden tener `num` duplicados (real). El frontend de stats desambigua via lookup por nombre con FotMob.
- `scripts/migrar_votos_formaaajcion.py` es one-shot. Ya se ejecutó (107 formaciones + 114 puntajes para Banfield/IndRiv/AtlTuc; después se sumaron 14+19 de Huracán). **No volver a correr con `--execute` — duplica filas.**
- `fetch_fixtures.py`, `update_estado.py`, `fetch_match_stats.py` leen `API_SPORTS_KEY` del environment (fallback a la key hardcodeada para uso local).
- `FLUJO.md` documenta el ciclo de vida completo de una fecha y el plan de automatización.
