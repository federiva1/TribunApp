---
name: actualizar-fecha
description: Actualiza la web de TribunApp después de un partido de Liga (o antes de una fecha) y la publica en www.tribunapp.com.ar con Vercel CLI, sin GitHub. Usar cuando el usuario diga "terminó X partido", "actualizá", "cerrá el partido", "publicá" o "refrescá el fixture".
---

# Actualizar una fecha y publicar (circuito sin GitHub)

## Reglas de oro
1. **Carpeta de producción = `C:\Users\feder\OneDrive\Escritorio\tribunapp-deploy\tribunappdeploy`**.
   Todo se corre y se publica DESDE AHÍ. **Nunca** `vercel --prod` desde el repo git
   (`Escritorio\TribunApp`): está un mes atrasado y subiría `scripts/.apikey` a la web.
2. La API key se pasa como **variable de entorno**, nunca se escribe en la carpeta de producción
   (esa carpeta se publica entera). Sale de `Escritorio\TribunApp\scripts\.apikey`.
3. Antes de publicar: `vercel deploy --dry` y `git diff --stat` (la carpeta tiene git local).
4. Nunca pisar datos: si un diff borra archivos de `data/partidos/` o achica `liga.json`, parar y avisar.

## Preparar el entorno (una vez por sesión)
```bash
export API_SPORTS_KEY="$(tr -d '\r\n' < "C:/Users/feder/OneDrive/Escritorio/TribunApp/scripts/.apikey")"
cd "C:/Users/feder/OneDrive/Escritorio/tribunapp-deploy/tribunappdeploy"
```
(En cada llamada al Bash tool repetir el `export` + `cd`: el estado del shell no persiste.)

## A) "Terminó el partido" — cierre rápido (abre los puntajes)
```bash
python scripts/cierre_rapido.py --check     # ¿hay candidatos? (100–210 min desde el kickoff, sin API)
python scripts/cierre_rapido.py             # marca FT en liga.json + genera data/partidos/{id}.json + tabla xG
```
- `cierre_rapido` imprime el **link para compartir** de cada partido cerrado
  (`https://www.tribunapp.com.ar/puntuar/newells-velez`): pasárselo al usuario junto con el resultado.
- Si FotMob todavía no tiene `playerStats`, el archivo sale con la base de api-sports (min/goles/asist).
  Se auto-repara volviendo a correr más tarde: `python scripts/fetch_liga_partidos.py --torneo clausura`
  y después `python scripts/build_tabla_xg.py`.
- Pasadas las 3,5 h del kickoff `cierre_rapido` ya no lo toma: usar directo
  `python scripts/fetch_liga_partidos.py --torneo clausura --date YYYY-MM-DD` + `build_tabla_xg.py`.
- Si api-sports está caído: `python scripts/cerrar_partido_fotmob.py --api-id <api_id>` (solo FotMob) + `build_tabla_xg.py`.
- Copas: `python scripts/fetch_liga_partidos.py --competicion copas`.

## B) Antes de una fecha / cada tanto — refrescar fixtures
```bash
python scripts/fetch_liga_fixtures.py       # liga.json (1 llamada)
python scripts/fetch_copas_fixtures.py      # copas.json
python scripts/fetch_fixtures.py            # los 30 data/fixtures/{slug}.json (41 llamadas, ~5 min por los sleeps)
python scripts/build_tabla_xg.py
```

## C) Publicar
```bash
git status --short && git diff --stat                  # qué cambió (git LOCAL de la carpeta)
vercel deploy --dry --format=json | head -c 600         # ver que no suba nada raro
vercel --prod --yes                                     # publica en www.tribunapp.com.ar
git add -A && git commit -q -m "data: <qué se actualizó>" # snapshot local para poder volver atrás
curl -s -o /dev/null -w "%{http_code}\n" https://www.tribunapp.com.ar/data/fixtures/liga.json
```
Volver atrás si algo salió mal: `vercel rollback` (Vercel guarda todas las versiones publicadas).

## Redes (opcional, no forma parte del circuito)
`social_lineups.py` / `social_resultado.py` / `social_fecha.py` generan placas en `data/social/preview/`.
Sin credenciales de X corren en modo ensayo (no tuitean). Necesitan PIL; no correrlos salvo que el usuario lo pida.
