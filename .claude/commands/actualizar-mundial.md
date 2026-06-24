---
description: Actualiza la web con los resultados de los partidos del Mundial 2026 que ya terminaron y todavía no fueron procesados (stats globales + jugadores FotMob + standings + puntajes + commit/push).
---

Actualizá la web de TribunApp con las estadísticas de los partidos del Mundial 2026 que **ya terminaron (FT)** y todavía **NO** fueron procesados. Trabajás en el repo actual (Windows, usá Bash o PowerShell).

Si el usuario pasó argumentos en `$ARGUMENTS`, son una pista de qué partido espera (ej. "arabia uruguay") — igual procesá cualquier otro FT pendiente que encuentres.

## Pasos

0. **Sincronizar repo** — `git pull --rebase` antes de todo. Esto evita conflictos cuando otra sesión (celu/compu) ya procesó un partido y lo pusheó — el script de fixtures preserva los `stats_id` existentes, pero solo si el archivo local ya los tiene.

1. **Fixtures** — `python scripts/fetch_mundial_fixtures.py`. Actualiza `data/fixtures/mundial.json` (estados y scores).

2. **Detectar partidos FT sin procesar** — leé `data/fixtures/mundial.json` y buscá los partidos con `status.finished === true` que **no** tengan `stats_id`. Para cada uno, seteá `stats_id = "{home.slug}-{away.slug}"` y guardá el JSON.
   - Los slugs salen del nombre en minúsculas sin espacios. Verificá contra `data/planteles/` que el slug exista.
   - Los nombres pueden traer tildes/caracteres no-ASCII (ej. `Curaçao`) — **normalizá con NFD y sacá los diacríticos** antes de slugificar, si no el filename queda roto (`curaao`).
   - Slugs especiales (ver `scripts/fetch_mundial_match.py → NOMBRE_A_SLUG`): `Bosnia and Herzegovina`→`bosniaandherzegovina`, `South Korea`→`southkorea`, `Czech Republic`/`Czechia`→`czechia`, `Türkiye`→`turkiye`, `Congo DR`/`DR Congo`→`drcongo` (⚠️ NO `congodr` — el plantel es `drcongo.json`), `Ivory Coast`→`ivorycoast`, `Cape Verde Islands`→`capeverdeislands`, `Curaçao`→`curacao`, `USA`/`United States`→`usa`.
   - Si no hay ningún FT sin `stats_id`, **terminá acá** e informá que no hay partidos nuevos para procesar.

3. **Stats globales (api-sports)** — `python scripts/fetch_mundial_match.py --auto`. Genera `data/partidos/{stats_id}.json` (lineup, eventos, stats globales) para cada FT sin archivo. Deduplica jugadores por ID automáticamente.

4. **Stats individuales (FotMob, Playwright)** — `python scripts/scrape_fotmob_mundial.py --auto`.
   - ⚠️ **Bug conocido**: el modo `--auto` suele fallar con `'str' object has no attribute 'get'`, PERO antes de fallar imprime `URL resuelta: https://www.fotmob.com/...`. Si falla para un partido, copiá esa URL y corré `python scripts/scrape_fotmob_mundial.py --url "<URL>" --id <stats_id>` (esa variante sí funciona). Repetí por cada partido pendiente.

5. **Standings** — `python scripts/fetch_mundial_standings.py`.

6. **Puntajes** — `python scripts/fetch_mundial_estado.py --force` (abre/cierra puntajes, ventana 24h desde el FT).

7. **Verificar** cada partido nuevo:
   - Resultado correcto (goles local/visitante coinciden con el fixture).
   - **Sin jugadores duplicados** en `data/partidos/{stats_id}.json → jugadores[slug]`.
   - El DT (`tipo: "dt"`) está presente en el dato (es correcto: lo usa la votación de puntajes). El frontend ya lo filtra en la sección estadísticas — **no lo saques del JSON**.
   - Que los jugadores tengan stats (que el DT y algún suplente no tengan datos de FotMob es normal).

8. **Commit + push**:
   ```
   git add data/partidos/ data/fixtures/mundial.json data/estado_mundial.json data/estado_torneo.json
   git commit -m "chore: update mundial data - {Local} vs {Visitante} [skip ci]"
   git push
   ```
   Si el push es rechazado (remoto adelantado): `git stash; git pull --rebase; git stash pop; git push`. Si hay conflicto en `mundial.json`, resolvé quedándote con la versión que tiene los `stats_id` que acabás de setear.

## Notas

- `data/partidos/` puede tener archivos sin trackear de clubes argentinos / fotos que **no** son parte de este flujo — agregá al commit solo los archivos de este pipeline (los 4 paths del paso 8), no uses `git add -A`.
- La foto de cada jugador usa el `fid` del plantel (`data/planteles/{slug}.json`), no el `id` del partido. El frontend ya resuelve esto por nombre.

## CSS de puntajes en `equipo.html` — estado correcto

El layout de cada fila de jugador en la sección puntajes (`#scores-list`) debe verse así en mobile:

```
[ foto ]  Apellido / #num
[ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ][ 7 ][ 8 ][ 9 ][ 10 ][ S/P ]
```

Los botones van en la **segunda fila** (debajo del nombre), no al lado. Si ves solo `#num` sin nombre, el CSS está mal. El CSS correcto en `equipo.html`:

```css
.score-player-row {
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px 10px;
  /* flex-wrap: wrap permite que los botones bajen a la segunda fila */
}
.score-player-info { flex: 1; min-width: 80px; }
/* min-width: 80px garantiza espacio para el nombre aunque los botones sean muchos */
.score-btns { display: flex; gap: 3px; flex-wrap: wrap; width: 100%; justify-content: flex-start; }
/* width: 100% fuerza a los botones a ocupar toda la fila propia */
```

El bug que se corrigió: `.score-player-info` tenía `flex: 1` (flex-basis: 0) sin `min-width`, y los 11 botones (~316px) consumían todo el ancho disponible en mobile, dejando el nombre con 0px.
