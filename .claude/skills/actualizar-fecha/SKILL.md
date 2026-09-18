---
name: actualizar-fecha
description: Actualiza la web de TribunApp después de un partido de Liga o copa (o antes de una fecha) y la publica en www.tribunapp.com.ar haciendo push a master en GitHub (Vercel publica solo). Usar cuando el usuario diga "terminó X partido", "actualizá", "cerrá el partido", "publicá" o "refrescá el fixture".
---

# Actualizar una fecha y publicar (circuito por GitHub)

Desde el 2026-09-18 **publicar = push a `master`**. Vercel está conectado al repo: cada
commit en `master` sale a www.tribunapp.com.ar en ~1 minuto. Funciona igual desde la compu
de Fede y desde una sesión en la nube.

## Reglas de oro
1. **Lo que se pushea, sale.** No hay paso intermedio: validar ANTES de commitear con
   `python scripts/check_datos.py`. Si falla, no se commitea — se avisa al usuario.
2. **Datos → directo a `master`. Código → rama + PR** (el PR genera un preview de Vercel para
   mirar antes). Un cierre de partido es datos; tocar `club.html` es código.
3. **Un solo camino.** NO usar más `vercel --prod` desde la carpeta
   `Escritorio\tribunapp-deploy\tribunappdeploy`: quedó como respaldo congelado. Si se publica
   por los dos lados gana el último y la web puede retroceder.
4. **Arrancar siempre con `git pull --rebase`**: otra sesión (la nube, otra compu) puede haber
   pusheado un cierre hace cinco minutos.
5. **La API key nunca va a un commit.** Sale de la variable de entorno `API_SPORTS_KEY` (nube)
   o de `scripts/.apikey` (compu, ignorado por git). `scripts/apikey.py` resuelve las dos.
6. **Actions está apagado y los crons comentados a propósito** (ver CLAUDE.md). No reactivarlos
   para "automatizar" esto sin que Fede lo pida.

## Preparar
```bash
git checkout master && git pull --rebase origin master
git status --short        # tiene que estar limpio antes de empezar
```

## A) "Terminó el partido" — cierre rápido (abre los puntajes)
```bash
python scripts/cierre_rapido.py --check     # ¿hay candidatos? (100–210 min desde el kickoff, sin API)
python scripts/cierre_rapido.py             # FT en liga.json + data/partidos/{id}.json + tabla xG
```
- Imprime el **link para compartir** de cada partido cerrado
  (`https://www.tribunapp.com.ar/puntuar/newells-velez`): pasárselo al usuario con el resultado.
- Si FotMob todavía no tiene `playerStats`, la ficha sale con la base de api-sports. Se
  auto-repara corriendo más tarde `python scripts/fetch_liga_partidos.py --torneo clausura`
  y `python scripts/build_tabla_xg.py`.
- Pasadas las 3,5 h del kickoff `cierre_rapido` ya no lo toma (genera la ficha pero NO marca
  FT en `liga.json`): usar `python scripts/fetch_liga_partidos.py --torneo clausura --date YYYY-MM-DD`
  y después `python scripts/fetch_liga_fixtures.py` + `build_tabla_xg.py`.
- api-sports caído: `python scripts/cerrar_partido_fotmob.py --api-id <api_id>` + `build_tabla_xg.py`.
- Copas: las toma el mismo `cierre_rapido`; después `python scripts/fetch_copas_fixtures.py`
  (el agregado de copas tarda en marcar FT).

## B) Antes de una fecha / cada tanto — refrescar fixtures
```bash
python scripts/fetch_liga_fixtures.py       # liga.json (1 llamada)
python scripts/fetch_copas_fixtures.py      # copas.json
python scripts/fetch_fixtures.py            # los 30 data/fixtures/{slug}.json (~5 min por los sleeps)
python scripts/build_tabla_xg.py
```

## C) Validar, publicar y verificar
```bash
python scripts/check_datos.py               # OBLIGATORIO. exit 1 = no commitear
git status --short && git diff --stat       # que solo haya cambiado lo esperado
git add -A
git commit -m "data: cierre Boca 3-1 Central Córdoba (Clausura F9)"
git push origin master                      # ← esto PUBLICA
```
Si el push es rechazado (alguien pusheó mientras tanto): `git pull --rebase origin master`,
volver a correr `check_datos.py origin/master` y pushear de nuevo. Nunca `--force` a `master`.

Verificar en producción. El deploy tarda ~1 min, así que se espera a que aparezca el dato:
```bash
until curl -s "https://www.tribunapp.com.ar/data/partidos/{id}.json?nc=$(date +%s)" | grep -q '"partido"'; do sleep 10; done
curl -s "https://www.tribunapp.com.ar/data/fixtures/liga.json?nc=$(date +%s)" | python -c "import json,sys; l=json.load(sys.stdin); print('FT:', sum(1 for x in l if x['status']['finished']))"
curl -s -o /dev/null -w "%{http_code}\n" https://www.tribunapp.com.ar/puntuar/{alias}-{alias}
```
Si a los 3-4 minutos no apareció, mirar el deploy: `gh api repos/federiva1/TribunApp/deployments?per_page=3`
(o el panel de Vercel). Reportar el fallo al usuario; no "arreglarlo" publicando por CLI.

## Volver atrás
```bash
git revert <sha> && git push origin master   # publica el estado anterior, deja historial
```
Urgente y sin tocar git: *Instant Rollback* desde el panel de Vercel (lo hace Fede).

## Redes (opcional, no forma parte del circuito)
Ver la skill `placas`. Escriben en `data/social/preview/`, que está en `.gitignore`: las
imágenes no se commitean ni se publican.
