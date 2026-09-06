---
name: exportar-datos
description: Exporta a CSV todos los datos de partidos, equipos y jugadores de TribunApp (más un README con el esquema y las trampas conocidas), para llevárselos a otra herramienta de análisis. Usar cuando el usuario pida exportar los datos, sacar los CSV, pasar las estadísticas a otra IA o hacer un backup de los datos.
allowed-tools: Bash(python scripts/exportar_datos.py*), Bash(cd*), Read, SendUserFile
---

# Exportar los datos a CSV

## Cómo se corre

Desde la **carpeta de producción** (ver [[deploy-dos-carpetas]] — el repo git está atrasado):

```bash
cd "C:/Users/feder/OneDrive/Escritorio/tribunapp-deploy/tribunappdeploy"
python scripts/exportar_datos.py --zip
```

- `--out <ruta>` para elegir carpeta (default `export/` dentro de la carpeta de producción).
- `--zip` arma además el `.zip` para mandárselo al usuario con `SendUserFile`.
- No necesita API key ni red: lee solo archivos locales.
- `export/` está en `.gitignore` y `.vercelignore`, así que no ensucia el repo ni el deploy.

Al terminar, **mandale el zip al usuario con SendUserFile** (display `attach`).

## Qué genera

| archivo | grano | se cruza por |
|---|---|---|
| `partidos.csv` | un partido, con stats de equipo de los dos lados | `partido_id`, `api_id` |
| `jugadores.csv` | un jugador en un partido (28 columnas de stats) | `partido_id`, `jugador_id` |
| `goles.csv` | un gol (minuto, asistencia, en contra) | `partido_id` |
| `planteles.csv` | un jugador de plantel | `club` + `jugador` |
| `fixture.csv` | todos los partidos del torneo, jugados o no | `api_id` |
| `README.md` | esquema + trampas de los datos | — |

## Verificar antes de entregar

El README explica las trampas, pero **conviene rehacer estos controles** después de
correrlo, porque los datos cambian y pueden aparecer casos nuevos:

1. **Huérfanos**: que ninguna fila de `jugadores.csv` ni `goles.csv` apunte a un
   `partido_id` que no esté en `partidos.csv`.
2. **Cuadre de goles**: `sum(jugadores.goles)` + goles en contra + no acreditados
   debe dar el total de los marcadores. Si no cierra, buscar el partido con la
   diferencia y explicarlo en el README (así se encontró el gol de Breno Bidon en
   `corinthians-rosariocentral`, que no se acredita porque a los equipos extranjeros
   de copa no se les sincronizan los contadores).
3. **Cobertura**: qué % de filas tiene los bloques de FotMob (venía ~89%).

## Trampas que el README ya documenta

- `fecha` es el día (`YYYY-MM-DD`), `fecha_num` es la jornada y **no es cronológico**.
- Los nombres **no son clave**: hay homónimos en el mismo plantel. Cruzar por `jugador_id`.
- Vacío = *no hay dato*, nunca cero.
- Las filas con `tipo = dt` son el entrenador: excluirlas de promedios.
- Solo entran los suplentes que ingresaron.
- Los votos de la gente (formaciones/puntajes) **no** están: viven en Supabase.
