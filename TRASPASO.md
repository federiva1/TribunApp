# TRASPASO — TribunApp

Notas de traspaso al **27/09/2026**. Cubre lo que **no** está en `CLAUDE.md` ni en
`PROYECTO.md`: decisiones tomadas sobre la marcha, pendientes, problemas conocidos y
procedimientos que no son obvios. Para entender el proyecto, leer primero `PROYECTO.md`
(la foto completa) y `CLAUDE.md` (la guía técnica). Esto es el delta.

No contiene claves ni credenciales. La key de api-sports sale de `scripts/apikey.py`
(variable de entorno o archivo local gitignored); nunca va a un commit.

---

## 1. Estado al momento del traspaso

- **`master` limpio y publicado.** No hay cambios sin subir ni commits sin pushear. El
  último commit es `248dd82` (cierre Lanús 2-1 Estudiantes), del 22/09.
- **Producción al día**: `liga.json` marca **150 partidos finalizados** de 240, y los
  30 clubes tienen 10 PJ en la tabla xG, o sea que la **fecha 10 está cerrada completa**.
- **No hay partidos pendientes de cerrar.** Verificado contra api-sports: no hubo
  partidos de liga entre el 22/09 y hoy. **La liga vuelve el 2/10** con Independiente -
  Instituto (19:15), primera de la fecha 11.

---

## 2. Decisiones tomadas que no están documentadas

### 2.1 Desde la nube, publicar es PR + merge. Sin excepción.

`CLAUDE.md` ya lo decía; el 18/09 quedó **confirmado con evidencia**, y de una manera
que conviene conocer porque es engañosa:

Un push directo a `master` desde una sesión en la nube **sí entra a GitHub** (el ref se
actualiza, `git push` reporta éxito) pero **Vercel no genera ningún deployment**. El
commit `5f08530` quedó en `master` con **cero statuses** y producción siguió sirviendo la
versión anterior. El mismo cambio, por PR + squash-merge, deployó normalmente.

O sea: que el push funcione **no** significa que se publicó. Verificar siempre en
producción (ver §5.3).

### 2.2 Contraste derivado del color del club (`equipo.html`)

El color del club se usaba de dos maneras opuestas y ninguna servía para los 30. Se
reemplazó el `color:#fff` fijo por tres variables derivadas del propio color, con reglas
de contraste WCAG (mínimo AA 4.5). El criterio, por si hay que tocarlo:

- `--acento-fondo` — el color como fondo de chip. Se aclara si no se despega del fondo
  de la página (mínimo **2.2**) y se corrige si su texto no llega a 4.5.
- `--acento-texto` — blanco, salvo que el negro sea **claramente** mejor (umbral de
  1.3×). Ese umbral existe para **no dar vuelta los rojos**, donde blanco (4.23) y negro
  (4.12) andan parecido y el blanco es lo esperable; el que sí se da vuelta es el
  amarillo (1.63 → 11.33).
- `--acento-light` — el color aclarado hasta que se lee sobre el fondo oscuro.

**La decisión de fondo**: derivar del color en vez de mantener una lista de excepciones
por club. Un club nuevo o un cambio de color queda legible solo.

### 2.3 S/P para el titular que no completó el primer tiempo (`club.html`)

`SP_MIN_TITULAR = 45`: el titular con `min < 45` recibe el botón S/P, además de los
suplentes que ingresaron. La fila aclara "salió 6'". El voto se guarda como `null` y los
promedios lo descartan, igual que el S/P de siempre — **no cambió ningún cálculo**.

Disparador: River-Huracán F10, con Almada saliendo a los 6' y Andrada a los 36'.

### 2.4 Tope del arquero en la placa vertical de puntajes (`club.html`)

`SH_Y_MAX = 89, SH_Y_MAX_GK = 93`. El tope de 89 existe para que el cartel con el
apellido no toque el borde; para el arquero quedaba mal porque **el área chica va del 91%
al 100%**, así que quedaba fuera del área con 41px muertos abajo. A 93 entra en el área y
al cartel le quedan ~11px. Si alguien quiere bajarlo más: **94 es el límite** (4px de
margen).

### 2.5 El export a Excel es solo de escritorio

`.eqt-export-bar` oculto en ≤720px. Razón: en el celular el archivo no tiene con qué
abrirse y el botón ocupa lugar en una pantalla ya angosta.

### 2.6 Mateo Mendoza (Argentinos, #23) vive solo en los overrides

No figura **ni en FotMob ni en api-sports** (`players/squads` y `players/profiles` dan
vacío): debe ser un juvenil recién subido. Está en `data/planteles/argentinosjuniors.json`
y en `data/planteles_overrides.json` con `fid: 0` y `position: "defenders"`.

La posición **no** sale de ninguna fuente: la confirmó Fede (defensor central, llegó de
Godoy Cruz). Si algún día FotMob lo incorpora con otra posición, **el override sigue
ganando** — hay que decidir a mano si se lo deja seguir a FotMob.

---

## 3. Pendientes

Ordenados por lo que más rinde primero.

1. **`club.html` tiene el mismo defecto de contraste que se arregló en `equipo.html`.**
   Hay ~18 lugares con texto blanco sobre `--club-color` (tabs, botones de puntaje,
   burbujas). Para Rosario Central y Defensa y Justicia (amarillo `#f5c518`) el contraste
   es **1.63**: ilegible. No se tocó porque es la pantalla principal y no era lo que se
   estaba mirando. El arreglo es mecánico: llevar las tres variables de §2.2.
   `club.html` ya define `--club-color2` (el `colorSecundario` de `clubes.js`), que para
   Rosario Central es `#1a1a1a` — o sea que la materia prima ya está.

2. **Sacar la marca `deploy-check` de `index.html`** (línea 3). Es un comentario HTML
   inerte que se puso para verificar que el deploy llegaba a producción. Ya cumplió.

3. **Automatizar la elección del camino de cierre.** Ver §4.1: `cierre_rapido.py` solo
   toma partidos de 100-210 minutos, y pasaron **tres seguidos** que quedaron afuera y
   necesitaron el camino largo. Un guard que elija solo según los minutos desde el
   kickoff evitaría el paso manual y el error de fecha UTC.

4. **`equipo.html`: el S/P se decide por grupo, no por jugador** (`renderGroup(..., true)`
   para los suplentes). Es la pantalla del Mundial y hoy no se usa para puntuar, pero si
   se recicla para la liga hay que llevarle la regla de §2.3.

5. **Dos decisiones abiertas sobre la regla de S/P**, las dos consecuencia de cómo quedó
   escrita:
   - Un titular **expulsado** antes del 45' también recibe S/P. Es coherente con el
     criterio (jugó muy poco), pero se puede discutir: hay quien dirá que una roja
     temprana merece puntaje bajo, justamente.
   - Un cambio hecho **exactamente al 45'** (entretiempo) **no** lleva S/P, porque
     completó el primer tiempo. Si se prefiere incluirlo, es cambiar `< 45` por `<= 45`.

6. **Limpieza de ramas.** En `origin` hay 13 ramas, varias muertas: `claude/actualizar-mundial-8zkunx`,
   `claude/actualizar-mundial-zcpo3f`, `claude/mobile-stats-players-scroll-ghvz7n`,
   `claude/urls-cortas-standby`, `claude/tribunapp-http-status-zftt22` (la de esta sesión,
   ya toda mergeada), `feature/auth`, `feature/automation`, `stats`, `test`, `campanas`.
   `pizarra` y `video` **sí siguen existiendo** y están documentadas en `CLAUDE.md`
   (`video` es la que nunca hay que mergear). Borrar ramas necesita OK de Fede.

---

## 4. Problemas conocidos

### 4.1 La ventana de `cierre_rapido.py` es angosta (100-210 min)

Es el problema operativo más frecuente. Pasado ese rango, el script **genera la ficha
pero no marca el FT en `liga.json`**, y sin el FT el gate de puntajes no abre. Como el
script no avisa ("sin partidos por cerrar"), es fácil creer que no había nada que hacer.

Camino largo, ya usado cuatro veces:

```bash
python scripts/fetch_liga_partidos.py --torneo clausura --date AAAA-MM-DD
python scripts/fetch_liga_fixtures.py     # reparar_estados completa el FT
python scripts/build_tabla_xg.py
```

**Trampa de la fecha**: `--date` es la fecha **UTC** del kickoff, no la argentina. Un
partido de las 21:15 del domingo es `00:15` del lunes en UTC, así que va `--date` del
**lunes**. Verificar siempre el `status.utcTime` del fixture antes de correrlo, y después
confirmar que quedó `finished=True` en `liga.json`.

### 4.2 Vercel puede trabarse y dejar la cola parada

El 18/09 un build quedó colgado **más de 40 minutos** y bloqueó todo lo que venía atrás,
previews incluidos. Terminó en `failure` y la cola se destrabó sola; el siguiente commit
deployó bien.

Cómo diagnosticarlo, que es lo importante:

- **Mirar el status del commit**, no la lista de deployments:
  `GET https://api.github.com/repos/federiva1/TribunApp/commits/{sha}/status`.
  El status dice `pending` con `"Vercel is deploying your app"` y trae el `target_url` del
  build; la lista de deployments **tarda en aparecer** y hace creer que no pasó nada.
- Un commit **sin ningún status** es otra cosa: ahí Vercel ni se enteró (ver §2.1).
- Producción sirviendo viejo se ve en los headers: `x-vercel-cache: HIT` con un `age`
  alto y un `last-modified` anterior al merge.

Cancelar un build colgado se hace desde el panel de Vercel; no hay CLI ni token en el
entorno de la nube.

### 4.3 api-sports se equivoca en las formaciones y en los onces

Dos casos reales del mismo partido (Racing-Sarmiento, F10):

- Daba Racing en **4-4-2** con Zaracho de volante. Era **5-3-2** con Zaracho de carrilero.
  Lo confirmó FotMob al cerrar el partido.
- Ponía a **Lucas Suárez** en el once de Sarmiento. Jugó **Nicolás Pasquini**.

La regla del proyecto (ya en la skill `placas`) se sostuvo en los dos casos: **ante
discrepancia, gana la placa del club**. Y la regla de leer las listas de los clubes **de
derecha a izquierda** se validó de nuevo: la defensa invertida de Sarmiento coincidió
exacta con el `grid` de api-sports.

### 4.4 Nombres de FotMob inconsistentes en las placas

En la placa de cierre de Racing-Sarmiento salió **"ADRIAN MARTINEZ"** completo y sin
tilde, mientras los otros tres goleadores iban abreviados (`G. ESCUDERO`, `J. MARABEL`).
Viene así del dato de FotMob. Se corrige a mano en `data/partidos/{id}.json` y
**regenerando la placa**, que requiere sacar antes la entrada del partido de
`data/social/resultados_posted.json` (si no, el script lo saltea).

Es el mismo problema que `CLAUDE.md` ya documenta para los apellidos mal escritos: un
reproceso con `--force` reintroduce el error.

### 4.5 Errores míos en mensajes de commit (los datos están bien)

Para que no confundan a quien lea el historial:

- Tres cierres quedaron etiquetados **F11** cuando en realidad eran de la **fecha 10**:
  PR #158 (Aldosivi), #159 (Barracas) y #160 (Lanús). El dato está bien en todos lados
  (`fecha=10` en `liga.json`, `fecha_num: 10` en las fichas); **solo el texto del commit
  y del PR está mal**.
- El PR #159 publicó un link de puntuar inexistente
  (`/puntuar/barracas-independienterivadavia`). El alias real, el que sale de
  `clubes_map.puntuar_url()`, es **`/puntuar/barracas-indrivadavia`**.

Moraleja operativa: **sacar los links de `clubes_map.puntuar_url()`, nunca escribirlos a
mano**, y verificar el número de fecha en `liga.json` antes de redactar.

---

## 5. Procedimientos especiales

### 5.1 El entorno de la nube necesita dos parches para las placas

Ninguno toca el repo; hay que rehacerlos en cada sesión nueva:

```bash
pip install pillow          # los generadores de placas lo importan
```

Y el Chromium: el Playwright que instala `pip` espera una revisión distinta a la que trae
el entorno. En vez de correr `playwright install` (que está desaconsejado y además el
proxy lo bloquea), enlazar la que ya está:

```bash
mkdir -p /opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64
ln -sf /opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell \
       /opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
```

(Los números de revisión cambian: el error de Playwright dice cuál espera.) Para scripts
propios de Playwright conviene pasar
`executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome'`.

### 5.2 Probar cambios de frontend antes de publicar

No hay tests. Lo que funciona:

```bash
node --check   # sobre cada bloque <script> inline extraído del HTML
python3 -m http.server 3031    # y abrir club.html?c=...  (las URLs amigables no andan en local)
```

Para cambios visuales, **mirar la página en un navegador real y medir**, no confiar en el
cálculo. Los dos arreglos de esta etapa (contraste y posición del arquero) se validaron
así: renderizando la página con Chromium, leyendo los valores computados y comparando
antes/después. El del arquero se decidió midiendo píxeles reales, no estimando.

Deep-links útiles para probar fuera de ventana: `?testpuntajes=1`, `?testformacion=1`,
`?testestado=pre|vivo|post`, `?testpuntuar=1`.

### 5.3 Verificar en producción, siempre

El merge no alcanza como prueba (§2.1 y §4.2). El deploy normal tarda ~30 s:

```bash
curl -s "https://www.tribunapp.com.ar/data/partidos/{id}.json?nc=$(date +%s)" | grep -q '"partido"'
curl -s "https://www.tribunapp.com.ar/data/fixtures/liga.json?nc=$(date +%s)" \
  | python3 -c "import json,sys; print(sum(1 for x in json.load(sys.stdin) if x['status']['finished']))"
curl -s -o /dev/null -w "%{http_code}\n" https://www.tribunapp.com.ar/puntuar/{alias}-{alias}
```

Para un cambio de código, buscar en el HTML publicado una constante nueva del commit
(por ejemplo `grep -q SP_MIN_TITULAR`). Es la forma más directa de saber si el deploy
llegó de verdad.

### 5.4 Placas: lo que hay que recordar

- Ninguna publica nada: todo va a `data/social/preview/`, que está en `.gitignore` y en
  `.vercelignore`. El tuit lo manda Fede a mano.
- `social_resultado.py` marca cada partido en `data/social/resultados_posted.json` (ese sí
  se commitea) y **no lo regenera**. Para rehacer una placa, borrar la entrada primero.
- Corre con la ventana de **100 a 300 minutos**, así que una corrida puede generar placas
  de otros partidos del día "de yapa". No es un error.
- La placa de cierre invita a puntuar: **cerrar el partido antes** de generarla, para que
  el link ya tenga los puntajes abiertos.
- Los tuits con 5 partidos y sus links **no entran en 280 caracteres** (X cuenta cada link
  como 23). Con cuenta Premium sale igual; si no, hay que acortar.

### 5.5 Si se agrega un archivo interno nuevo en la raíz

Sumarlo a `.vercelignore`, si no se publica en la web. **Este archivo ya está agregado.**

---

## 6. Cambios sin subir

**Ninguno.** El árbol de trabajo está limpio, `master` local coincide con `origin/master`
y todo lo de esta etapa está publicado.

Un detalle de higiene que se arregló y conviene no repetir: en una corrida quedó un commit
hecho sobre `master` local que se pusheó con `HEAD:claude/…`, y eso además dejó a `master`
**siguiendo a la rama `claude/…`** en lugar de a `origin/master`. El contenido llegó igual
a producción por el PR, pero el commit quedó huérfano. Si aparece un "commit sin pushear"
en `master`, antes de tocar nada comparar contra `origin/master` (`git diff origin/master`):
si el diff está vacío, el contenido ya está publicado y alcanza con `git reset --hard
origin/master` y `git branch --set-upstream-to=origin/master master`.
