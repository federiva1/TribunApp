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

# === Mundial 2026 — pipeline post-partido ===

# 1. Actualizar fixture del mundial (estados, scores) desde api-sports
python scripts/fetch_mundial_fixtures.py

# 2. Generar data/partidos/{stats_id}.json para partidos FT sin archivo aún
python scripts/fetch_mundial_match.py --auto
python scripts/fetch_mundial_match.py --fixture-id 1234567 --id germany-curacao  # manual

# 3. Enriquecer con stats individuales FotMob (HTTP/urllib; Playwright solo fallback local)
python scripts/scrape_fotmob_mundial.py --auto                          # todos los pendientes
python scripts/scrape_fotmob_mundial.py --url "https://..." --id germany-curacao  # manual
python scripts/scrape_fotmob_mundial.py --auto --headed                 # browser visible (debug, fallback)

# 4. Actualizar tabla de posiciones del mundial
python scripts/fetch_mundial_standings.py

# 5. Abrir/cerrar puntajes (ventana 24h desde FT)
python scripts/fetch_mundial_estado.py           # conserva puntajesOpen existentes
python scripts/fetch_mundial_estado.py --force   # recalcula puntajesOpen según tiempo

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
- **Live standings**: `https://v3.football.api-sports.io/standings?league=128&season=2026`. La API key NO va hardcodeada: los scripts la leen vía `scripts/apikey.py` (env var `API_SPORTS_KEY` o archivo local gitignored `scripts/.apikey`); el frontend nunca la toca (usa el proxy `/api/apisports`, que la lee de la env var de Vercel). Returns 4 groups: `[0]` Zona A, `[1]` Zona B, `[2]` Anual, `[3]` Promedios. Group order can swap (Zona B first) — both index.html and club.html detect this by checking if the first group name contains `"b"`.
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

### index.html — hoy es la home del Mundial 2026
`index.html` es la landing del Mundial (title "TribunApp — Mundial 2026"), **no** un índice de clubes argentinos (el viejo simulador `FIXTURE_T`/`tSimState` fue removido). Ver "Mundial 2026 Module → index.html (bracket de eliminatorias)". Las páginas de clubes argentinos (`club.html`, `copas.html`) siguen en el repo pero ya no cuelgan de `index.html`. La sección Selección (`seleccion.html`) fue removida — no se usa por ahora.

## Mundial 2026 Module

Módulo separado del flujo de clubes argentinos. Todas las páginas del Mundial son standalone (no dependen de `js/clubes.js` ni Supabase).

### Páginas

- **`index.html`** — Home del Mundial. Header + partido en vivo + toggle **ELIMINATORIA (default) / FASE DE GRUPOS**. Ver "index.html (bracket de eliminatorias)" abajo.
- **`fixture.html`** — Fixture del Mundial. Muestra amistosos + todas las fases (Fase de Grupos, **Dieciseisavos** (round `1/32`), Octavos, Cuartos, Semis, Final). Los tabs de fase se muestran solos cuando esa ronda tiene partidos en `mundial.json`, y abre en la más avanzada disponible (`FASES` con `visible` recalculado al cargar). Partidos definidos por penales muestran "Pen X-Y" bajo el marcador y marcan al ganador vía `p.winner`. Datos en `data/fixtures/mundial.json`. La pill "Estadísticas" del header apunta a `estadisticas-torneo.html`.
- **`estadisticas-torneo.html`** — Landing de estadísticas del torneo. Sección superior: goleadores y asistidores globales (computados dinámicamente leyendo todos los JSONs de `data/partidos/`). Sección inferior: grilla de 48 selecciones. Selecciones con datos (`data/partidos/index.json` tiene entradas para ese slug) muestran "VER STATS" y linkan a `equipo.html?c={slug}`.
- **`equipo.html`** — Perfil de selección. Tiene una sección "estadísticas" que llama a `loadPartidosStats()`: busca en `data/partidos/index.json` los partidos de ese slug, muestra una card Acumulado + cards por partido. Cada card es un `<a href="estadisticas.html?p={id}&c={slug}">`.
- **`estadisticas.html`** — Vista de un partido específico. URL: `?p={partido-id}` + `?c={slug-equipo}` (opcional, para auto-seleccionar el tab del equipo visitante si se entra desde su perfil). Tiene dos tabs: **Estadísticas** (stats globales del partido) y **Jugadores** (switcher Local/Visitante con cards expandibles por jugador).

### index.html (bracket de eliminatorias)

Vista **ELIMINATORIA** (default) — cuadro de 32 equipos que se completa solo a medida que el pipeline procesa partidos. Vista **FASE DE GRUPOS** — grilla estática de los 12 grupos leída de `data/estado_torneo.json` (se **quitó** el fetch live a `/api/apisports/standings`; los grupos ya no dependen de la API).

- **Estructura fija**: la constante `BRACKET = { left:[...8 pares...], right:[...8 pares...] }` define el orden del cuadro (pares `[homeSlug, awaySlug]` de la Ronda de 32, de arriba a abajo). Pares **adyacentes** alimentan cada nodo de octavos. El orden **no** sale de `mundial.json` (ese array es cronológico) — se mantiene a mano según el sorteo. Si un cruce queda mal emparejado, se reordena acá (cross-check contra los octavos ya definidos en `mundial.json`).
- **Auto-avance**: `_bkNode(home, away, partidos)` busca el partido en `mundial.json` por slugs (sin importar local/visitante) y, si está `finished`, saca el ganador de `match.winner` (cubre penales; fallback a comparar marcador). `_bkNext()` propaga ganadores a la ronda siguiente. Nodos sin definir = "A definir" (`?`). Penales se muestran como `1 (4)` en el nodo y `(4 pen)` en el popover.
- **Híbrido responsive**: desktop = cuadro completo con nombre (usa `NOMBRES_CORTO` para los largos: EE.UU., P. Bajos, R.D. Congo, C. Marfil…); mobile (`≤720px`) = condensado solo-escudos, y tocar un cruce abre un popover con nombres + link a `equipo.html?c={slug}`. Los conectores son pseudo-elementos (`.has-child`/`.has-parent` + `.side-right`) sobre columnas flex con `flex:1`.
- **Ancho**: `.bracket { width:max-content; margin:0 auto }` para centrar y evitar barra horizontal; achicar columnas/gap si se pasa del contenedor.
- Tocar una bandera → `equipo.html?c={slug}` (misma metodología de formación/puntajes que en grupos).

### Data

- **`data/fixtures/mundial.json`** — Array de partidos. Campos clave: `round`, `roundName`, `api_id`, `stats_id` (ID del JSON en `data/partidos/`), `home`/`away` con `name`/`slug`/`id`, `home_score`/`away_score`, `status.finished`/`status.short`/`status.utcTime`. **Eliminatorias**: `winner` (slug del ganador — lo pone `fetch_mundial_fixtures.py` desde `teams.X.winner` de api-sports; cubre penales/prórroga aunque el marcador sea empate) y `home_pen`/`away_pen` (marcador de la tanda, `null` si no hubo). Si `stats_id` está presente y el partido está finalizado, `fixture.html` genera un link a `estadisticas.html?p={stats_id}`. El orden del array **no** es orden de bracket (es cronológico) — el cuadro usa un mapeo fijo (ver "index.html (bracket de eliminatorias)").
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

### Foto FID — convención crítica

Los archivos de foto (`fotos/{fid}.png`) usan el **fid del plantel** (`data/planteles/{slug}.json → jugadores[].fid`), NO el ID de FotMob del partido (`data/partidos/{id}.json → jugadores[slug][].id`). Estos dos IDs difieren para muchos jugadores. Siempre usar `enPlantel?.fid` para construir la URL de foto; el `j.id` del partido es solo para identificación interna.

### Puntajes — convenciones de `equipo.html`

- `checkScoresReady()` usa `sq.every(p => p.num in userScores)` (no comparación de lengths) para manejar jugadores con número duplicado (frecuente en amistosos donde dos arqueros juegan).
- Al enviar puntajes: Supabase primero, localStorage después. Si el fetch falla (`!res.ok`), se lanza error y el localStorage no se setea → el usuario puede reintentar.
- Los scores se persisten en localStorage en `lsScoresKey() + '_data'` (JSON) para restaurarlos al recargar, además del flag `lsScoresKey()` que indica "ya votó".
- Post-submit: **nunca bloquear la pantalla** con overlay. Solo toast + botón "Ya enviaste ✓" deshabilitado. Los botones de puntaje individuales quedan activos (el usuario puede ver/modificar localmente pero no reenviar).
- `tipo` field en cada jugador: `'titular'` / `'suplente'` / `'dt'`. Se lee del JSON del partido (`j.tipo`) con fallback `idx < 11 ? 'titular' : 'suplente'`. Debe estar en `data/partidos/{id}.json`.
- `device_id` NO existe en la tabla `puntajes` de Supabase (sí en `formaciones`). No incluir en el payload de puntajes.

### Formación — convenciones de `equipo.html`

- Post-submit: nunca mostrar `#formation-success` overlay. Solo toast. El pitch queda libre para editar/descargar.
- Tap-to-place: al hacer tap (< 12px movimiento) sobre un chip del banco, se llama `placeFromBench(p)` que posiciona al jugador según `POSICION_ZONE[p.posicion]` con collision avoidance en espiral.
- `POSICION_ZONE`: `GK {x:50,y:87}`, `DEF {x:50,y:71}`, `MED {x:50,y:50}`, `DEL {x:50,y:26}`.

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

### Extracción de stats FotMob — vía HTTP (no browser)

`scrape_fotmob_mundial.py` baja el `__NEXT_DATA__` **por HTTP con `urllib`** (`_next_data_http`), no con Playwright. FotMob hace SSR: `props.pageProps.content.playerStats` (del match) y `...fallback[team-{id}].fixtures` (de la página del equipo) vienen embebidos en `<script id="__NEXT_DATA__">` del HTML. Esto es clave porque **el chromium de Playwright está bloqueado por el proxy del entorno cloud y por la IP de GitHub Actions** (`ERR_CONNECTION_CLOSED`), pero urllib usa el proxy y sí llega. Playwright quedó solo como **fallback** (`_next_data_browser`, para la compu local). Por eso `sync_playwright` es import opcional.

- El flujo `--auto` (`resolve_fotmob_url` → `_fetch_next_data` → `_enrich_payload_from_nd`) ya funciona derecho; **no** hace falta el viejo workaround de copiar la "URL resuelta" y correr `--url` a mano.
- Bug histórico ya corregido: `--auto` llamaba `enrich_players(nd, payload)` salteando la extracción de `playerStats` y el matching local/visitante (daba `'str' object has no attribute 'get'`). Esa lógica vive en `_enrich_payload_from_nd(nd, payload)`, compartida por `--auto` y `--url`.
- Estructura FotMob: `playerStats` es dict `{pid: {name, teamId, isGoalkeeper, stats:[{title, stats:{label:{stat:{value}}}}]}}`. `stats` por sección es **objeto** (dict), no array. Para selecciones `p.name` es string directo (no `p.name.fullName`), pero el MVP (`matchFacts.playerOfTheMatch.name`) puede venir string o dict.

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

## Mundial 2026 — Automatización Post-Partido

### Scripts del pipeline

| Script | Fuente | Output |
|--------|--------|--------|
| `fetch_mundial_fixtures.py` | api-sports league=1 | `data/fixtures/mundial.json` |
| `fetch_mundial_match.py --auto` | api-sports fixtures/{id} | `data/partidos/{stats_id}.json` |
| `scrape_fotmob_mundial.py --auto` | FotMob vía HTTP (urllib, fallback Playwright) | enriquece jugadores en el mismo JSON |
| `fetch_mundial_standings.py` | api-sports standings | `data/partidos/standings.json` |
| `fetch_mundial_estado.py --force` | lee mundial.json | `data/estado_mundial.json` |

**Ventana de puntajes**: 24h desde el FT (no 48h como en liga). Configurado en `fetch_mundial_estado.py`.

**Deduplicación jugadores**: `fetch_mundial_match.py` deduplica por player ID antes de devolver — api-sports double-lista jugadores que juegan los 90' como titular Y suplente. El fix evita que aparezcan duplicados en stats/puntajes.

**Resolución URL FotMob auto**: `scrape_fotmob_mundial.py` tiene `resolve_fotmob_url(stats_id, date_str, local_slug)` que baja `fotmob.com/teams/{fotmob_id}/fixtures` (por HTTP), extrae `__NEXT_DATA__`, encuentra el partido por fecha y devuelve la URL exacta — sin tener que buscarla manualmente.

**Photo matching** (`estadisticas.html` + `equipo.html`): jerarquía de 5 niveles:
1. Exacto normalizado (tildes/case)
2. First+Last token
3. Token key (sorted set)
4. Last word único
5. Token overlap ≥ 2
6. **Surname contained**: todos los tokens no-iniciales del nombre abreviado (ej. "A. Amaimouni") están en el nombre del plantel, match único → usa ese fid. Maneja "A. Amaimouni" → "Ayoube Amaimouni-Echghouyab".

### Las 3 opciones de automatización

#### 🖥️ Opción "Compu" (local — ya funcionando)
- **Mecanismo**: Claude Code scheduled tasks (skill `/schedule`) en la máquina local
- **Tareas programadas**: `mundial-post-match` (kickoff+2h05), `mundial-post-match-b1` (+5min backup), `mundial-post-match-b2` (+10min backup)
- **Lógica backup**: cada tarea verifica si el partido ya fue procesado antes de actuar; si sí, termina sin hacer nada
- **Requiere**: compu encendida + Claude Code app abierta
- **Costo**: tokens del plan normal (~15k–30k tokens por partido estimado)
- **Token tracking**: registrar en tabla abajo

#### ☁️ Opción "Actions" (GitHub Actions — ya en prod)
- **Mecanismo**: `.github/workflows/mundial-match-stats.yml` con 52 crons pre-calculados (kickoff UTC + 2h20m grupos, +3h15m eliminatorias)
- **Pipeline**: fetch_mundial_fixtures → fetch_mundial_match --auto → scrape_fotmob_mundial --auto → fetch_mundial_standings → fetch_mundial_estado --force → git auto-commit
- **No usa IA** — scripts Python determinísticos corriendo en runners de GitHub
- **Requiere**: nada (funciona 24/7 sin compu)
- **Costo**: $0 (gratis en repos públicos)
- **Nota FotMob**: el scraper ahora baja los datos **por HTTP (urllib)**, no con el browser, así que el bloqueo de Playwright en la IP de GitHub ya no aplica. Si aun así FotMob fallara, el workflow continúa con stats de api-sports (sin stats individuales por jugador).

#### 🤖 Opción "Agente Cloud" (todavía no implementada)
- **Mecanismo**: servidor cloud (AWS Lambda / Render / Railway) + API de Anthropic corriendo Claude Code como agente autónomo
- **Ventaja**: puede razonar, reintentar, manejar errores inesperados, notificar si algo sale mal
- **Costo estimado**: $5–20/mes servidor + ~$0.50–2 por partido en tokens Claude Sonnet → **~$50–130 total para los 64 partidos del mundial**
- **Estado**: pendiente de evaluación. Se implementará si Opción Actions falla sistemáticamente.

### Registro de tokens por partido (para comparar opciones)

| Partido | Opción | Tokens input | Tokens output | Total | Resultado |
|---------|--------|-------------|---------------|-------|-----------|
| — | — | — | — | — | — |

*(Completar después de cada run de Opción Compu con el contador de tokens de la sesión)*

### Stats_id de partidos del Mundial

El `stats_id` en `mundial.json` es el nombre del archivo en `data/partidos/`. Se deriva del slug local-visitante.
Slugs especiales que requieren mapeo manual en `fetch_mundial_match.py → NOMBRE_A_SLUG`:
- `Bosnia and Herzegovina` → `bosniaandherzegovina`
- `South Korea` → `southkorea`
- `Czech Republic` / `Czechia` → `czechia`
- `Türkiye` → `turkiye` (evitar unicode en filename)
- `Congo DR` → `congodr`
- `Ivory Coast` → `ivorycoast`
- `Cape Verde Islands` → `capeverdeislands`
- `USA` / `United States` → `usa`
