# Flujo de TribunApp

Documento del ciclo de vida de cada fecha y de cómo funciona la sección de estadísticas. Complementa `CLAUDE.md` (que cubre arquitectura).

## Ciclo de una fecha

1. **Pre-partido** — La gente arma su formación ideal y la sube a Supabase (`formaciones`). Visible para todos (logueados y no logueados).
2. **Durante el partido** — La sección de puntajes está cerrada: todavía no existe `data/partidos/{id}.json` para ese partido.
3. **Final del partido (FT)** — `liga-match-stats.yml` (cada 3 h) genera `data/partidos/{id}.json` con el plantel que jugó. Con ese archivo presente, `applyGating()` en `club.html` abre los puntajes y la gente vota 1–10.
4. **Post-partido inmediato** — Se corre el scraping para popular las estadísticas reales:
   - `scrape_fotmob_partidos.py` baja `playerStats` de FotMob para AAAJ y el rival → `partidos[].jugadores` y `partidos[].jugadoresRival`.
   - `fetch_match_stats.py` baja stats globales de api-sports → `partidos[].stats_partido` (posesión, tiros, pases, faltas, córners, amarillas, rojas).
   - El xG de cada equipo se recomputa sumando el xG individual de los jugadores que jugaron (api-sports no provee xG consistente para LPF).
5. **24h después del kickoff** — Los puntajes se cierran solos: `applyGating()` deja de cumplir `within24h`. No hay cron ni archivo de estado; los datos quedan congelados para el acumulado. Para probar fuera de la ventana existe `?testpuntajes=1`.
6. **Lectura en la web** — Las estadísticas se muestran en la sección ESTADÍSTICAS (auth-gated): *Equipo* (datos reales del partido) y *Página* (tier list de formaciones + podio de puntajes).

Después se repite el ciclo para la siguiente fecha.

## Estado de automatización

### Automatizado (GitHub Actions, en `.github/workflows/`)

| Workflow | Cron | Qué hace |
|---|---|---|
| `update-fixtures.yml` | 9h y 21h UTC | Regenera `data/fixtures/{slug}.json` para los 30 clubes y las copas |
| `liga-match-stats.yml` | cada 3h | Genera `data/partidos/{id}.json` de los partidos FT de la liga (api-sports + FotMob). Es lo que abre los puntajes. |

Todos commitean con `[skip ci]` para evitar loops.

### Manual (por ahora)

| Script | Cuándo se corre | Notas |
|---|---|---|
| `scripts/scrape_fotmob_partidos.py` | Después de cada partido | Requiere Playwright + browser. Headless funciona. |
| `scripts/fetch_match_stats.py` | Después de cada partido | Solo `urllib`, ligero. Idealmente correrlo después del scrape (para usar el xG individual). |
| `scripts/fetch_proximos_partidos.py` | Antes de cada fecha | Actualiza `rivalActual` en `js/clubes.js`. |
| `scripts/excel_to_json.py` | Solo AAAJ (legacy) | Convierte el Excel histórico a JSON. Reemplazado por el FotMob scraper para fechas nuevas. |
| `scripts/migrar_votos_formaaajcion.py` | One-shot, ya ejecutado | Trajo los votos de Banfield, Indep. Rivadavia, Atl. Tucumán, Huracán de la Supabase legacy. **No volver a correr con `--execute`** (duplica filas). |

### Por automatizar

- **Generalización del scraper a 30 clubes**: hoy `scrape_fotmob_partidos.py` está hardcodeado para AAAJ (TEAM_ID 10086, lista de 4 partidos). Hay que cambiarlo para que tome `(slug, season)` y arme la lista de URLs desde `data/fixtures/{slug}.json` + el endpoint de FotMob `/api/data/teams?id=...`.

## Estructura de datos

### `data/estadisticas/{slug}.json`

Hoy solo existe para `argentinosjuniors`. Schema:

```json
{
  "club": "argentinosjuniors",
  "temporada": "Apertura 2026",
  "partidos": [
    {
      "fecha": 13,                       // del league.round de api-football
      "rival": "Banfield",
      "rivalId": 449,                    // api-sports id, para escudo
      "rivalSlug": "banfield",
      "date": "2026-04-06",
      "condicion": "Local",
      "resultado": "3 - 2",
      "stats_partido": {
        "equipo": { "posesion": 67, "xG": 1.07, "tiros": 17, "tirosAlArco": 7,
                    "pasesAcertados": 485, "pasesIntentados": 552,
                    "faltas": 9, "corners": 9, "amarillas": 1, "rojas": null },
        "rival":  { "posesion": 33, "xG": 0.69, ... }
      },
      "jugadores":      [ /* AAAJ — schema TribunApp (nombre, jugo, minutos, goles, ...) */ ],
      "jugadoresRival": [ /* mismo schema, para el rival */ ]
    }
  ],
  "acumulado": [ /* totales por jugador AAAJ del torneo */ ]
}
```

### Supabase (TribunApp)

- `formaciones(id, club, rival, match_date, jugadores, likes, dislikes, device_id, user_id, equipo_hincha)` — `jugadores` es un array `[{num, name, fid, ...}]`.
- `puntajes(id, club, rival, match_date, puntajes, user_id, equipo_hincha)` — `puntajes` es un object `{num: 1-10}`.
- `perfiles(id, equipo_hincha)`.

`match_date` es el campo canónico para identificar el partido (más confiable que `rival` por temas de tildes y abreviaciones entre fuentes).

## Sección ESTADÍSTICAS

Auth-gated. Hoy solo `argentinosjuniors` tiene datos cargados; otros clubes ven "próximamente".

Dos tabs:

### Tab "Equipo" (default — datos reales del partido)

- Scoreboard arriba: escudo AAAJ + resultado + escudo del rival + meta (Fecha · DD/MM · Local/Visitante).
- Bloque "Top estadísticas" estilo planilla, idéntico al diseño de la captura de referencia:
  - Posesión (barra horizontal proporcional con colores de cada club)
  - xG, Tiros totales, Disparos a puerta, Pases precisos (con %), Faltas, Saques de esquina, Tarjetas amarillas, Tarjetas rojas
  - Pill destacando al equipo con mayor valor
- Tabla de jugadores (AAAJ) — minutos, goles, asistencias, xG, xA, disparos, toques, pases, defensa.
- Selector de fecha (solo fechas con `stats_partido` cargado) + Acumulado (totales del torneo).

### Tab "Página" (votos de la gente)

- **Vista por fecha**: tier list de formaciones (5 niveles por % de votos) + podio de puntajes 1/2/4/4 estilo Formaaajcion.
- **Vista acumulada**: suma global de votos sobre todas las fechas con datos.
  - Tier list: % global = veces elegido / total formaciones del scope.
  - Podio: promedio sobre todos los puntajes individuales del scope.
  - **Cutoff**: un jugador aparece en el podio solo si fue puntuado en al menos `ceil(N/2)` partidos (50% del scope). Para 4 fechas → mín. 2.

### Filtros importantes que aplica el podio

1. **Solo jugadores que jugaron**: usa `partido.jugadores[].jugo === true` para saber si la persona realmente jugó esa fecha. Si alguien le puso puntaje a un jugador no convocado, ese voto se descarta.
2. **Identificación por nombre, no por num**: el squad de algunos clubes tiene `num` duplicados (Argentinos: #10 = Lescano y Florentín; #17 = Paredes y Ferreira; #33 = Riquelme y Pérez). El podio cruza con FotMob (`partido.jugadores[].nombre`) para identificar al jugador real que llevó ese num en ese partido. Así sale el name+fid correctos en cada caso.

## Lo que se hizo en la rama `stats`

Cambios respecto a `master`:

1. **Stats globales del partido**: nuevo script `fetch_match_stats.py` que toma posesión / xG / tiros / pases / faltas / córners / tarjetas de api-sports `/fixtures/statistics`. Inyecta en `data/estadisticas/argentinosjuniors.json`.
2. **Scraping de FotMob**: nuevo script `scrape_fotmob_partidos.py` con Playwright que extrae `playerStats` de los DOS equipos del partido. Recomputa `xG` del equipo y rival sumando individual.
3. **UI ESTADÍSTICAS rediseñada en `club.html`**:
   - Tabs renombrados a "Equipo" / "Página", default "Equipo".
   - Default fecha = última fecha jugada con datos.
   - Header tipo scoreboard con escudos.
   - Bloque "Top estadísticas" estilo planilla (idéntico a la captura).
   - Acumulado de página = suma global con cutoff 50%.
4. **Bugs históricos arreglados**:
   - Matching `formaciones`/`puntajes` ↔ partido vía `match_date` (antes fallaba por strings de rival inconsistentes entre api-sports y Supabase).
   - Squad lookup por nombre vía FotMob (antes el primer #23 pisaba al segundo).
   - `_renderStatsTabWeb` usa la global `squad` cargada por `initSquad()` (antes shadowing con `CLUB.squad` vacío → fotos rotas).
   - `Verón` movido a #9 (estaba como #23, conflicto con López).
   - Filtro de votos a no-convocados (antes Verón aparecía en el podio aunque no jugó).
5. **Migración de Huracán**: 14 formaciones + 19 puntajes que faltaban de la Supabase legacy.
6. **Toggle Apertura/Clausura en sección FIXTURE** (no es de stats pero quedó en esta rama): default al torneo en curso según el mes, filtra `league.round`.

## Cómo cargar una fecha nueva

Cuando se juega un partido nuevo de AAAJ:

```bash
# 1. Esperar ~30–60 min después del FT para que FotMob procese.

# 2. Agregar la URL del partido a PARTIDOS en scrape_fotmob_partidos.py
#    (la consigo de fotmob.com/teams/10086/fixtures o paso2_partidos.py)

# 3. Bajar player stats de ambos equipos
python scripts/scrape_fotmob_partidos.py --only YYYY-MM-DD

# 4. Bajar stats globales de api-sports + recomputar xG sumando individual
python scripts/fetch_match_stats.py

# 5. Commit y push
git add data/estadisticas/argentinosjuniors.json
git commit -m "data: stats fecha N vs <rival>"
git push
```

Cuando esto se automatice, los pasos 2–4 se vuelven un workflow.

## Para extender a otro club

1. Generar `data/estadisticas/{slug}.json` corriendo el scraper para ese club (hoy hardcodeado para AAAJ — refactorizar a `--club {slug}`).
2. Quitar el gate `if (CLUB_SLUG !== 'argentinosjuniors')` en `renderStats()` de `club.html`.
3. (Opcional) si hay votos previos en alguna Supabase, escribir un migrador parecido a `migrar_votos_formaaajcion.py`.

El UI ya soporta cualquier club — usa `escudos/{slug}.png` y `CLUBES_CONFIG[slug].color`.
