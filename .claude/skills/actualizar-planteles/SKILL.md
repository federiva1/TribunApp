---
name: actualizar-planteles
description: Baja/actualiza los planteles de los 30 clubes de la Liga Profesional desde FotMob (num, name, fid, posición) y completa los dorsales faltantes con api-sports (backfill). Usar cuando el usuario pida actualizar, bajar o refrescar los planteles de los equipos de la liga.
allowed-tools: Bash(python scripts/fetch_planteles_liga.py*), Bash(git add*), Bash(git commit*), Bash(git push*), Bash(git status*), Bash(git diff*), Read
---

# Actualizar planteles de la Liga (FotMob)

Baja/actualiza los planteles de la Liga Profesional Argentina desde FotMob. **Fuente de
verdad = FotMob**; los IDs de equipo ya están en `scripts/scraper_planteles.py → EQUIPOS`
(slug con guión → la app usa sin guión, el script convierte).

Cada plantel es `data/planteles/{slug}.json`: lista de `{num, name, fid, nationality, position}`.

**Flujo integrado** (`fetch_planteles_liga.py` lo hace todo en un comando): scrapea FotMob →
los jugadores que quedan **sin dorsal** se completan con **api-sports** (`players/squads`, vía
`backfill_plantel_nums.fill_blanks`) → escribe **todos** los jugadores. Los que igual quedan sin
número (juveniles/reserva que ninguna fuente tiene, muy pocos) se **conservan en blanco** (ya no
se descartan). Los dorsales no cambian durante el torneo → se corre una vez, o ante altas/bajas.

## Pasos

1. **(Opcional) Dry-run** para ver los conteos sin escribir nada:
   ```
   python scripts/fetch_planteles_liga.py --dry-run
   ```

2. **Bajar los planteles**. Todos los clubes:
   ```
   python scripts/fetch_planteles_liga.py
   ```
   Clubes puntuales (slug del app, sin guiones):
   ```
   python scripts/fetch_planteles_liga.py velezsarsfield racingclub
   ```

3. **Revisar la salida**: jugadores por club + cuántos quedaron sin número. Si algún club
   dio `✗ ERROR` (FotMob no respondió), reintentá ese slug solo.

4. **Ver qué cambió** antes de commitear:
   ```
   git status --short data/planteles/
   git diff --stat data/planteles/
   ```

5. **Commitear y pushear** (con OK del usuario):
   ```
   git add data/planteles/ && git commit -m "Planteles: actualización desde FotMob" && git push origin HEAD:master
   ```

## Notas

- Algunos clubes traen la plantilla completa (reserva/juveniles), 40-52 jugadores. FotMob no
  distingue primer equipo; si el usuario quiere sólo el primer equipo, hay que agregar un filtro.
- **Backfill api-sports**: corre solo dentro de `fetch_planteles_liga.py`. También existe
  suelto (`python scripts/backfill_plantel_nums.py [--dry-run] [slug...]`) para completar
  dorsales en blanco de los planteles ya escritos sin re-scrapear FotMob.
- **Re-correr**: como los dorsales no cambian en el torneo, sólo hace falta re-correr ante
  altas/bajas o si api-sports registró jugadores que antes no tenía (ej. arranque de torneo).
- Las fotos NO se bajan (la UI usa kit chips por color de club). Si alguna vez se necesitan,
  `scripts/scraper_planteles.py` las descarga a `fotos/{slug}/{fid}.png`.
- Si FotMob cambia un ID de equipo, actualizarlo en `EQUIPOS` de `scripts/scraper_planteles.py`.
