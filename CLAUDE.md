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
# Actualizar los planteles de los 30 clubes de la liga desde FotMob (num/name/fid/posición).
# Flujo integrado: scrapea FotMob → completa los dorsales faltantes con api-sports (backfill) →
# escribe TODOS los jugadores; los que igual quedan sin número se conservan en blanco.
# Es la fuente recomendada — empaquetado como skill /actualizar-planteles.
python scripts/fetch_planteles_liga.py                 # todos los clubes
python scripts/fetch_planteles_liga.py --dry-run       # previsualiza sin escribir
python scripts/fetch_planteles_liga.py velezsarsfield  # slugs puntuales (del app, sin guión)

# Rellenar los dorsales en blanco de los planteles cruzando con api-sports (players/squads).
# FotMob a veces no lista el número de un jugador (queda ''); api-sports sí lo tiene para el
# plantel actual. Solo completa vacíos, nunca pisa números existentes (matching por nombre).
python scripts/backfill_plantel_nums.py --dry-run      # previsualiza
python scripts/backfill_plantel_nums.py                # aplica a todos
python scripts/backfill_plantel_nums.py independiente  # slugs puntuales

# (Legacy) Scrapear planteles + fotos (escribe slugs con guión; usar fetch_planteles_liga en su lugar)
python scripts/scraper_planteles.py

# Generar js/club-colors.js — color primario + alternativo de cada club (del escudo, con PIL)
python scripts/extract_club_colors.py                  # todos (edita OVERRIDES para casos b/n)

# Update rivalActual for each club in js/clubes.js (reads next fixtures from API)
python scripts/fetch_proximos_partidos.py

# Generate data/fixtures/{slug}.json for all 30 clubs (Liga) + copa files
python scripts/fetch_fixtures.py          # liga + copas
python scripts/fetch_fixtures.py --liga   # only liga
python scripts/fetch_fixtures.py --copas  # only copa files

# Tabla xG ("tabla moral") → data/tabla_xg.json. Resultado de cada partido = parte
# entera del xG de cada equipo (0.98 vs 0.57 = 0-0; 0.98 vs 1.02 = 0-1). Solo lee
# data/partidos (sin APIs); la corren update-fixtures.yml y liga-match-stats.yml,
# y la consume el tab "Tabla xG" de tablas.html.
python scripts/build_tabla_xg.py

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
      "jugadores":      [ /* schema TribunApp: nombre, jugo, minutos, goles, asistencias, xG, xA, accDefensivas, disparos, toques, pasesAcertados/Intentados + set ampliado opcional: tiros, grandesOcasiones, toquesArea, regates(+regatesTotal), pasesUltimoTercio, entradas, intercepciones, recuperaciones, despejes, duelosGanados/Perdidos, faltas, faltasRecibidas */ ],
      "jugadoresRival": [ /* mismo schema, para el rival */ ]
    }],
    "acumulado": [ /* totales por jugador AAAJ del torneo */ ]
  }
  ```
  El `fecha` viene del `league.round` de api-football (parseado del string "Apertura - 14"). Cuando el partido todavía no se jugó, `stats_partido` y `resultado` no están presentes (header básico solamente). `xG` se rellena sumando el xG individual cuando api-sports no lo provee (común en LPF).
- **Player squads**: static JSON at `data/planteles/{slug}.json`. Fields: `num`, `name`, `fid`, `nationality`, `position`. **Pueden tener `num` duplicados** (ej AAAJ #10 = Lescano y Florentín) porque más de un jugador comparte número; la sección ESTADÍSTICAS desambigua cruzando con `partido.jugadores[].nombre` de FotMob. Se actualizan con `python scripts/fetch_planteles_liga.py` (skill `/actualizar-planteles`). Flujo: scrapea FotMob → **backfill** de dorsales faltantes con api-sports (`backfill_plantel_nums.fill_blanks`, integrado en la skill) → escribe TODOS; los que igual quedan sin número (juveniles/reserva que ninguna fuente tiene, ~pocos) se conservan **en blanco** (ya NO se descartan). Ojo: FotMob trae la plantilla completa (algunos clubes 40-52, incluye reserva/juveniles). **Dorsal faltante**: FotMob a veces no da el número → queda `num: ''` (antes un bug escribía el string `'None'`, corregido en `scraper_planteles.py` con `str(... or '')`). `scripts/backfill_plantel_nums.py` también corre solo para completar vacíos. Los dorsales no cambian en el torneo → se corre una vez (o ante altas/bajas). El frontend de stats descarta `''`/`'None'` y cae al número del partido.
- **Player photos**: `fotos/{slug}/{fid}.png` — legacy. La UI actual usa **kit chips** (círculo con el patrón/color del club, ver `js/kits.js`), no fotos, así que `fetch_planteles_liga.py` no las descarga.
- **Community data**: read/written to Supabase. The `club` column (slug) differentiates the 30 teams.
- **Puntajes gate**: no hay archivo de estado. Se calcula client-side en `applyGating()` (`club.html`) — ver "Puntajes gate (liga)" abajo.

### Módulos JS compartidos (frontend liga)
- **`js/kits.js`** — fuente ÚNICA de los kits (kit chips): `KITS` (patrón por club), `clubKit(slug)` (fallback = sólido con color de escudo), `kitBackground(kit, size)`, `NUM_OUTLINE`. La usan `club.html` (formación/puntajes) y `estadisticas.html` (avatares). `type`: solid | stripesV | stripesH | halves | band (franja horizontal) | bandV (franja vertical) | sash (diagonal ↘) | sashR (diagonal ↙) | svg (patrón vectorial embebido, ej. la 'V' de Vélez, con `center/100%`). `div` opcional = grosor de bastón (más alto = más finos). El número siempre blanco con contorno. **`kits-preview.html`** renderiza los 30 kits para revisarlos.
- **`js/club-colors.js`** — `window.CLUB_COLORS = {slug:{primary,alt}}` (color de identidad de cada club, del escudo). Generado por `scripts/extract_club_colors.py`. Lo usa la barra de posesión del desplegable de stats en `fixture.html` con resolución de colisión (si los dos `primary` se parecen, usa el `alt` del visitante). **NO** es `CLUBES_CONFIG.color` (que es placeholder `#003087` en casi todos).
- **`js/match-live.js`** — motor de la **ficha en vivo**: `window.buildPayloadLive(apiId)` fetchea api-sports (`fixtures?id` + `fixtures/lineups|events|statistics?fixture=`) y arma el MISMO schema que `data/partidos/{id}.json`. Slugs vía `ESCUDO_MAP[teamId]`. Regla de oro: **una sola fuente por momento** (en vivo = api-sports, al terminar = FotMob) para que los números coincidan.

### fixture.html — ficha + stats inline por partido
Cada card de partido que arrancó tiene **dos pestañas en la misma línea** que despliegan INLINE (comparten un `.ficha-panel`): **① "Ficha del partido"** (jugadores: titulares + "Ingresaron" con `▲min`, salidas `▼min`, goles arriba) y **② "Ver estadísticas del partido"** (stats globales: posesión con barra por color de club + xG/tiros/córners/pases). Estado en `_secOpen[fid]`, payload cacheado en `_fichaCache[fid]`, y `render()` reabre la sección activa con `_restoreSections()` (el poll en vivo de 60s no la cierra). `estadisticas.html` es la página completa (global + individual); `loadMatchData()` decide fuente (en curso/sin JSON → api-sports; terminado con JSON → FotMob). **Bug fix**: `actualizarEnVivo` cierra los partidos que figuran EN_CURSO pero ya salieron de `live=all` (traen su estado final por `fixtures?id=`), así no quedan "jugándose" para siempre.

### Proxy api-sports — cache (`api/apisports.js`)
El proxy pone `Cache-Control: no-store` a las queries de **fixtures en vivo** (`live`, `id` o `fixture` en la query) para que el CDN de Vercel no sirva datos viejos; el resto (standings/teams/players/listados) cachea 60s. Verificar con `curl -D -`: live = `no-store` + `X-Vercel-Cache: MISS`. **Lag de api-sports**: al terminar un partido el endpoint por-`id` marca FT al toque, pero los agregados (`league=`/`team=`) tardan — se los vio devolviendo `"1H 0-0"` más de 10 min después del final, en cuatro fechas seguidas. Como `liga.json` sale del agregado, el gate de puntajes no abría. **Ya está resuelto**: `fetch_liga_fixtures.reparar_estados()` completa esos partidos con lo que haya en `data/partidos/{id}.json` (que viene del endpoint por-`id`). Solo corrige hacia "terminado", nunca pisa un partido que la API ya da por finalizado, y valida que los slugs de local y visitante coincidan antes de aplicar. Ya no hace falta parchear `liga.json` a mano.

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
- **Formación**: el rival y el `match_date` salen del **primer partido sin resultado** del fixture por-club (el archivo se regenera cada 2 h, así que al avanzar de ronda el rival entra solo; `rivalLibertadores`/`rivalSudamericana` de clubes.js quedan como fallback inicial). El string de rival es el nombre api-sports — el mismo que va a la columna `rival` de Supabase.
- **Puntajes (mismo gate de 24 h que la liga)**: `resolveCopaScoresContext()` toma el último partido con kickoff pasado de `data/fixtures/copas.json` (trae `utcTime`) y busca el archivo en `data/partidos` por club + competición + día (tolerancia 1 día; el rival extranjero no tiene slug). El gate NO mira el `short`/`finished` de copas.json a propósito (sale del agregado de api-sports, que se atrasa): kickoff pasado + archivo del partido presente = abierto. Los tiles del home en copa los arma `updateCopaTiles()` (`fillTiles` hace early-return con `COPA`, si no mostraría los partidos de liga).

#### FIXTURE — toggle Apertura/Clausura
Para liga, una sola llamada a api-sports trae todos los partidos del año. El toggle filtra por `league.round` (busca "apertura"/"clausura" case-insensitive) con fallback al mes (≤6 = Apertura, ≥7 = Clausura). Default = torneo en curso según el mes de hoy. El toggle no aparece en contexto de copa.

#### ESTADÍSTICAS (`renderStats()` en club.html)
Sin gate por club — intenta cargar el JSON correspondiente; si no existe, muestra "próximamente" (no es un error). Dos tabs:
- **Equipo** (default — datos reales del partido) — scoreboard con escudos + rival + resultado, bloque "Top estadísticas" estilo planilla (posesión / xG / tiros / disparos / pases con % / faltas / córners / tarjetas, con pill destacando al equipo con mayor valor), y **tabla ancha scrolleable tipo FotMob con 3 filtros**:
  - **Fechas (multi-select que suma)** — toggles `stats-fecha-tog` + botón "Todas". Se activan varias fechas y los jugadores que jugaron en más de una muestran stats **sumadas** (`_statsAggregate` agrupa por nombre normalizado, suma `STATS_SUM_KEYS`, agrega columna `PJ`). Con **una sola** fecha activa se muestran también scoreboard + Top estadísticas; con varias, solo la tabla.
  - **Jugadores** — chips `stats-pchip` (Todos/Ninguno) que ocultan filas (`eq.hiddenPlayers`).
  - **Columnas** — chips `stats-col-chip` que prenden/apagan cada stat (`eq.hiddenCols`).
  - La tabla es **data-driven**: `STATS_COLS` es el catálogo maestro (set actual + set ampliado FotMob); solo se renderiza una columna si algún jugador del scope tiene valor no-nulo. Así AAAJ (~10 stats) e Independiente (~22 stats) usan el mismo render sin ramas. Columna Jugador sticky a la izquierda (`.stats-wide td.name-col`), ordenable por header.
- **Página** (votos de Supabase) — vista por fecha: tier list de formaciones (5 tiers por % de votos: 81-100, 61-80, 41-60, 21-40, 0-20) + podio de puntajes 1/2/4/4 con medallas. Vista acumulada: suma global de votos sobre todas las fechas con datos. Mantiene su propio selector de fecha single-select (`_statsRenderWebFechaBar`).

Estado del módulo: global `_stats = { data, formaciones, puntajes, tab, fechaSel, sortKey, sortAsc, eq: { fechas:Set, hiddenPlayers:Set, hiddenCols:Set, sortKey, sortAsc } }`. `fechaSel` es solo del tab Página; `eq` es el sub-estado del tab Equipo. Las tres fuentes (JSON, formaciones, puntajes) se cargan secuencialmente (JSON primero — si no existe, fallback a "próximamente") y quedan cacheadas en memoria.

**Filtros importantes del podio de puntajes** (`_statsRenderPodio`):
1. **Solo jugadores que jugaron** — usa `partido.jugadores[].jugo === true` para excluir votos a no-convocados. Si alguien le puso puntaje a un jugador que no jugó, ese voto se descarta.
2. **Lookup por nombre, no por num** — los planteles tienen `num` duplicados; la función `_statsMatchSquad(j.nombre, squad)` busca el squad entry por nombre normalizado (tildes/case-insensitive), con fallback por primer+último apellido o solo apellido. Así el name+fid del podio sale del jugador real, no del primer match por num.
3. **Cutoff acumulado** — un jugador aparece en el podio acumulado solo si fue puntuado en al menos `Math.ceil(N/2)` de los partidos del scope (50%+). Para 4 fechas → mín. 2. Una fecha con solo votos S/P no cuenta como puntuada.
4. **Orden por promedio ajustado (estilo IMDb)** — el podio se ORDENA por `(avg·nFechas + C·M)/(nFechas + C)` con `C=2` y `M` = promedio general del scope (fallback 5.5): con pocas fechas puntuadas el jugador gravita hacia M, así una gran fecha aislada no supera a un rendimiento sostenido. El promedio que se MUESTRA es el real, junto con la cantidad de fechas. `tribunapp-equipo.html` (`calcPuntajes`) aplica el mismo cutoff + orden en su acumulado.
5. **S/P (unificado en toda la app)** — los suplentes pueden recibir "sin puntaje" (`null` en el JSON de `puntajes`). El S/P NO cuenta para el promedio: ni suma ni entra al denominador, ni como voto ni como fecha puntuada. Rige igual en la liga (`club.html`), en Est. TribunApp (`tribunapp-equipo.html`) y en el Mundial (`equipo.html`, donde antes el S/P valía 0 o 2 según el % — regla eliminada). Todos los cálculos descartan `null`/`''` explícitamente (ojo: `Number(null) === 0`, no NaN). Filas legacy sin `match_date` cuentan como una pseudo-fecha (`'__sinfecha'`) para no desaparecer del acumulado por el cutoff.

`_renderStatsTabWeb` usa la global `squad` cargada por `initSquad()` (no `CLUB.squad`, que nunca se completa). El tier list de formaciones prioriza `j.name` y `j.fid` del snapshot del vote sobre la lookup en squad por la misma razón de duplicados.

### Puntajes gate (liga) — client-side, sin archivo de estado

No hay `data/estado.json`: se borró junto con `update_estado.py`, `close_puntajes.py` y los
workflows `match-monitor.yml` / `close-puntajes.yml` (tenían el cron comentado desde junio 2026
y el frontend ya no los leía). El gate se calcula solo, en `applyGating()` de `club.html`:

```js
PUNTAJES_OPEN = override || (hasData && within24h);
```
- `hasData` — existe `data/partidos/{id}.json` con jugadores del club (lo genera `liga-match-stats.yml`).
- `within24h` — pasaron menos de 24 h desde el **kickoff** del último partido de `liga.json`.
- `override` — `?testpuntajes=1` en la URL, para probar fuera de la ventana.

El contexto (rival, `match_date`, plantel que jugó) lo arma `resolveMatchContext()` /
`resolveScoresContext()` leyendo `liga.json` + `data/partidos/index.json`. El Mundial sí conserva
su propio gate por archivo (`data/estado_mundial.json`, ver más abajo).

Workflows programados que quedan en `.github/workflows/`:
- **`update-fixtures.yml`** — corre `fetch_fixtures.py` para mantener los JSON de fixtures al día.
- **`liga-match-stats.yml`** — cada 3 h, genera `data/partidos/{id}.json` de los FT de la liga.
- **`update-mundial-fixtures.yml`** / **`mundial-match-stats.yml`** — el pipeline del Mundial.
- **`lineups-social.yml`** — cada 5 min con guard barato (`social_lineups.py --check`, solo lee
  `data/fixtures`): si hay un partido nuestro (liga o copa) que arranca dentro de los próximos
  32 min y no se posteó (≈6 intentos: 30/25/20/15/10/5 min antes; **nunca después del kickoff**,
  el primero que lo logra marca el partido y los demás lo saltean),
  pide `fixtures/lineups` a api-sports y, con los dos XI confirmados, genera una imagen
  por equipo (cancha vertical estilo placa: kit chips de `js/kits.js`, nombres del plantel por
  dorsal, escudo + formación) y tuitea desde @tribunAppFutbol. Sin los secrets
  `X_API_KEY`/`X_API_SECRET`/`X_ACCESS_TOKEN`/`X_ACCESS_TOKEN_SECRET` corre en **modo ensayo**:
  commitea las imágenes en `data/social/preview/` sin tuitear. Estado anti-duplicados en
  `data/social/lineups_posted.json`. Test manual:
  `python scripts/social_lineups.py --test-fixture {api_id} --test-lineups stub.json`.
- **`resultado-social.yml`** — cada 10 min, mismo esquema (`social_resultado.py --check`): si un
  partido nuestro arrancó hace entre 100 y 300 min y no se posteó, pregunta el estado al endpoint
  **por-id** de api-sports (marca FT al toque, a diferencia de los agregados) y, si terminó, genera
  la placa "FINAL DEL PARTIDO" (logo, escudos + marcador, goleadores con minuto y escudo, estadio)
  y tuitea invitando a puntuar. Estado en `data/social/resultados_posted.json`. Test manual sin API:
  `python scripts/social_resultado.py --test-partido sanlorenzo-union` (lee `data/partidos/{id}.json`).

Usan `stefanzweifel/git-auto-commit-action@v5` con `[skip ci]` en el mensaje para evitar loops, y
requieren el secret `API_SPORTS_KEY` en GitHub → Settings → Secrets.

### copas.html
Hardcoded arrays `LIBERTADORES_SLUGS` and `SUDAMERICANA_SLUGS` define Argentine participants. Groups fetched live from api-sports (Libertadores: `league=13`, Sudamericana: `league=11`).

### index.html — hoy es la home del Mundial 2026
`index.html` es la landing del Mundial (title "TribunApp — Mundial 2026"), **no** un índice de clubes argentinos (el viejo simulador `FIXTURE_T`/`tSimState` fue removido). Ver "Mundial 2026 Module → index.html (bracket de eliminatorias)". Las páginas de clubes argentinos (`club.html`, `copas.html`) siguen en el repo pero ya no cuelgan de `index.html`. La sección Selección (`seleccion.html`) fue removida — no se usa por ahora.

## Mundial 2026 Module

Módulo separado del flujo de clubes argentinos. Todas las páginas del Mundial son standalone (no dependen de `js/clubes.js` ni Supabase).

### Páginas

- **`index.html`** — Home del Mundial. Header + partido en vivo + toggle **ELIMINATORIA (default) / FASE DE GRUPOS**. Ver "index.html (bracket de eliminatorias)" abajo.
- **`fixture.html`** — Fixture del Mundial. Muestra amistosos + todas las fases (Fase de Grupos, **Dieciseisavos** (round `1/32`), Octavos, Cuartos, Semis, Final). Los tabs de fase se muestran solos cuando esa ronda tiene partidos en `mundial.json`, y abre en la más avanzada disponible (`FASES` con `visible` recalculado al cargar). Partidos definidos por penales muestran "Pen X-Y" bajo el marcador y marcan al ganador vía `p.winner`. Datos en `data/fixtures/mundial.json`. La pill "Estadísticas" del header apunta a `estadisticas-torneo.html`.
- **`estadisticas-torneo.html`** — Landing de estadísticas. **Repurposada a clubes de Liga** (ya no selecciones): la grilla inferior lista los 30 clubes leídos de **`data/equipos.json`** (`[{slug, nombre}]`); los que tienen partido en `data/partidos/index.json` muestran "Ver stats" y linkan a `equipo.html?c={slug}&s=estadisticas`. El nombre a mostrar sale de `equipos.json` (helper `nomEquipo`/`nomBySlug`, no del map de selecciones `nbSlug`). Sección superior: goleadores/asistidores globales computados leyendo todos los `data/partidos/*.json`.
- **`equipo.html`** — Perfil de equipo. **Ahora club-aware**: incluye `js/clubes.js` y `init()` soporta tanto el plantel de club (array `[{num,name,fid,position}]`) como el del Mundial (`{equipo,grupo,jugadores:[{numero,nombre,...}]}`); color/nombre salen de `CLUBES_CONFIG` (fallback a `COLORES_EQUIPO`/`NAMES_ES`). La sección "estadísticas" (`loadPartidosStats` → `renderEqStats`) es una **tabla FotMob ancha agregada con filtros**: selector de partidos multi-toggle que **suma** (`aggregateEq`, agrupa por jugador vía `matchPlantel` para unificar grafías entre partidos como "Rodrigo Rey"/"R. Rey", columna PJ), chips de jugador (`hiddenPlayers`) y de columna (`hiddenCols`), catálogo `EQ_COLS` del schema rico (`top/ataque/defensa/duelos` aplanados), columna Jugador sticky, ordenable. Data-driven: solo se muestran columnas con algún valor. Deep-link `?s=estadisticas` abre la sección directo. (El viejo card-list + overlay Acumulado quedaron sin uso.)
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
    "partido": { "local", "visitante", "goles_local", "goles_visitante", "fecha", "estadio", "competicion", "goles_detalle": { "local": [...], "visitante": [...] }, "formacion": { "{slug-local}": "4-3-3", "{slug-visitante}": "5-3-2" } },
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
    "pos": { "x": 61.0, "y": 79.0 },   // solo titulares: posición REAL en la cancha
    "top":    { "tiros_totales", "disparos_puerta", "oport_creadas", "grandes_oport", "acc_defensivas", "pases_precisos" },
    "ataque": { "toques", "toques_area", "regates", "pases_ultimo_tercio", "tiros_largos", "perdida_balon" },
    "defensa": { "acc_defensivas", "entradas", "interceptaciones", "recuperaciones", "despejes", "bloqueos", "regateado" },
    "duelos":  { "ganados", "perdidos", "terrestres", "aereos", "faltas", "faltas_recibidas" },
    "portero_stats": null  // o { "paradas", "goles_contra", "goles_evitados" } para porteros
  }
  ```
  Campos opcionales son `null` cuando FotMob no reporta el valor (se muestran como `—`). `regates` y `terrestres`/`aereos` son strings fracción (`"2/5"`). Los jugadores están ordenados por minutos desc.

  **`pos` + `partido.formacion` (formación real)** — salen del `lineup` de FotMob (`horizontalLayout`, normalizado 0..1 sobre la cancha **apaisada con el arquero a la izquierda**, que es justo la orientación de la placa → se guardan como % sin transformar). Los captura `scrape_fotmob_mundial._lineup_por_equipo()` / `_aplicar_lineup()`, así que entran solos en cada corrida del pipeline. El match FotMob ↔ api-sports es **por dorsal** (único dentro de un XI), con fallback por nombre y por token del apellido — hace falta porque api-sports abrevia ("D. Fernandez") y en los apellidos compuestos cada fuente elige una parte distinta ("Hernán López Muñoz"). Para backfillear partidos viejos: `python scripts/backfill_formaciones.py` (solo FotMob, **no** necesita la API key; idempotente, `--force` recalcula).

  Lo usa la placa de puntajes en `club.html` (`_shPosiciones()`): si al menos el 70 % de los titulares tiene `pos`, dibuja la formación real y ubica el resto con el layout por líneas; si no, cae entero a `_shPorLineas()`. Ojo: ese fallback agrupa por el puesto **genérico del plantel**, no por cómo se jugó el partido (un carrilero cae en la línea de defensores, un volante que en el plantel figura como delantero se dibuja arriba) — por eso la posición real se prefiere siempre que esté.

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
- **Nunca ordenar/elegir partidos por número de fecha — siempre por fecha REAL (`status.utcTime`).** El número de fecha (`fecha` en `liga.json`, `fecha_num` en `data/partidos`) NO es cronológico: una postergación deja p.ej. la F2 a jugarse *después* de la F3 (caso real: Estudiantes F2 vs Boca movido entre F3 y F4). Cualquier lógica de "próximo partido", "fecha actual" o listado cronológico debe sortear por `status.utcTime` (liga.json) o por el `fecha`-string de día (`data/partidos`/fixtures per-club), no por el número. Ya corregido en `fixture.html` (lista por equipo + fecha auto-abierta), `club.html` (`clubLigaMatches` próximo, selector Est.TribunApp, default de stats). Ojo: `fecha` significa cosas distintas según el archivo — en `liga.json` es el **número** de fecha (el día está en `status.utcTime`), mientras que en `data/partidos/*.json` y `data/fixtures/{slug}.json` es un **string de día** `YYYY-MM-DD` (el número está en `fecha_num`/`num`). Los datos se auto-sincronizan: `update-fixtures.yml` regenera `liga.json` desde api-sports cada 2 h, así que una postergación reflejada en la API entra sola (parche manual a `liga.json` solo si la API tarda).
- El gate de puntajes de la liga se calcula client-side (`applyGating()` en `club.html`): 24 h desde el kickoff + que exista `data/partidos/{id}.json`. Ya no hay `data/estado.json`. Para probar fuera de la ventana: `?testpuntajes=1`.
- `data/estadisticas/{slug}[_copa].json` se genera con `fetch_match_stats.py` + `scrape_fotmob_partidos.py` (en ese orden — el segundo recomputa el `xG` sumando individual). Para fechas viejas de AAAJ existe `excel_to_json.py` (deprecado pero mantenido).
- `fetch_match_stats.py` y `scrape_fotmob_partidos.py` aceptan `--slug --copa --date` y resuelven IDs vía `clubes_map.py`. Para clubes nuevos hay que agregar el `fotmob` ID a ese archivo.
- `match_date` es el matching canónico para Supabase ↔ JSON. Nunca matchear por `rival` string.
- Los planteles pueden tener `num` duplicados (real). El frontend de stats desambigua via lookup por nombre con FotMob.
- `scripts/migrar_votos_formaaajcion.py` es one-shot. Ya se ejecutó (107 formaciones + 114 puntajes para Banfield/IndRiv/AtlTuc; después se sumaron 14+19 de Huracán). **No volver a correr con `--execute` — duplica filas.**
- Los scripts leen la API key **solo** de `scripts/apikey.py → get_api_key()` (env var `API_SPORTS_KEY` que usan los GitHub Actions, o archivo local gitignored `scripts/.apikey`). **Ya NO hay key hardcodeada** en ningún script (se sacó por seguridad); si falta, `get_api_key()` aborta con mensaje claro. El frontend nunca toca la key (usa el proxy `/api/apisports`).
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

**Partidos de Liga en `data/partidos/` — batch recomendado**: `scripts/fetch_liga_partidos.py` procesa **todos los partidos FT de la Liga** de una (base api-sports + jugadores FotMob), idempotente:
```bash
python scripts/fetch_liga_partidos.py                 # FT de Clausura no procesados
python scripts/fetch_liga_partidos.py --force         # reprocesa también los hechos
python scripts/fetch_liga_partidos.py --date 2026-07-26
python scripts/fetch_liga_partidos.py --limit 3       # probar
```
Resuelve la URL de FotMob por `fotmob_id` del club (los 30 están en `scripts/clubes_map.py`, sacados de la tabla FotMob de la liga). El id de salida es `{local_slug}-{visitante_slug}` con los slugs de `js/clubes.js` (ojo: Argentinos = `argentinosjuniors`, no `argentinos`). Automatizado por el workflow **`.github/workflows/liga-match-stats.yml`** (cada 3h; se auto-repara si FotMob todavía no tenía `playerStats`). El enrich mapea local/visitante por **fotmob_id** (robusto para clubes; evita bugs de grafía como "Newell's").

Para casos puntuales/manuales siguen sirviendo `fetch_mundial_match.py --fixture-id ... --local ... --visitante ...` + `scrape_fotmob_mundial.py --url ... --id ...`. Partidos viejos de FotMob pueden no traer `playerStats` (el enrich queda con `top/ataque/... = null`, pero el lineup api-sports con min/goles/asist igual sirve para la tabla agregada).

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
