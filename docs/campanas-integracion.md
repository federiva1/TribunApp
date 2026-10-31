# Campañas: primera integración

Estado: implementación para revisión en la rama `campanas`, sin merge a `master`.

## Alcance acordado

Primer corte con el Apertura 2026 existente: 255 partidos, 30 clubes, tres modos,
filtro por club y archivo personal. Sin login, sincronización ni rankings públicos.
Se guarda la mejor marca por colección/partido/modo en este navegador, con cantidad
de intentos y fechas. Una respuesta incorrecta también termina el desafío; repetirlo
no multiplica la mejor marca. Abandonar o recargar una partida incompleta no la guarda.

Se agregaron 24 campañas históricas (dos por cada uno de los 12 clubes pedidos),
con selector de colección, carga diferida y progreso separado. Catálogo, cobertura,
fuentes y límites: `campanas-historicas.md`. Las otras propuestas del documento
`campanas-objetivos.md` siguen siendo objetivos editoriales, no datos publicados.

La portada conserva «¿Cuánto sabés de fútbol argentino?» y los 30 escudos. Primero
explica los tres retos con imágenes; debajo ofrece el Apertura 2026 (con filtro por
equipo) y las campañas históricas agrupadas en 12 tarjetas de clubes, cinco por fila
en escritorio y dos en celular. Elegir una campaña abre sus recorridos y retos.
El botón **Jugar** está arriba junto a **Mis campañas**, y también en el hero. Abre
una selección compacta de campaña, equipo (si corresponde), recorrido y reto; desde
allí se entra a la partida. Recuerda la última campaña jugada. Los textos de logros
históricos se retiraron de las tarjetas y de las cabeceras de campañas por club.

## Recorridos y medallero (31/10/2026)

- **Expreso:** un tercio redondeado hacia arriba, con un máximo de cinco partidos.
- **Clásico:** la mitad de los partidos, redondeada hacia arriba.
- **Completo:** todos los partidos jugables. Los suspendidos no entran.

Son duraciones, no dificultades: no cambian ayudas ni puntajes. Una campaña de 19
partidos ofrece 5/10/19; una de seis, 2/3/6. La selección es fija: prioriza el último
partido, el primero y puntos intermedios espaciados, en ese orden; se muestra en
orden cronológico. No es una selección editorial de «los mejores partidos».
Expreso está contenido en Clásico, y Clásico en Completo. Las tres vistas usan los
mismos registros existentes: cambiar de recorrido no borra ni duplica resultados.

Completar un reto disponible por partido alcanza para la medalla del recorrido.
Una respuesta errónea o asistida también termina ese reto: la medalla reconoce
haberlo recorrido; los puntos reflejan el desempeño. Otros retos del mismo partido
quedan como opcionales. Se priorizan partidos sin ningún reto terminado. Si sólo
quedan encuentros sin reto de goleadores (por ejemplo, 0–0), se ofrece explícitamente
formación o resultado para continuar; no se repiten goleadores indefinidamente.

**Mis campañas** muestra sólo las que el usuario empezó a jugar, con estados en
juego o completada y tres insignias (una por recorrido). Entrar a ver una campaña
no la agrega; empezar una partida sí, aunque todavía no se haya terminado. Se conserva
esa pertenencia al recargar. Los resultados anteriores también recuperan sus campañas.
La campaña completada tiene borde y brillo dorados. Los filtros de club, recorrido y
estado permiten revisar cada avance. El Apertura sólo aparece si se jugó y conserva
el equipo elegido: no se agregan automáticamente recorridos de sus rivales. Una misma
persona puede empezar recorridos del Apertura con distintos clubes o con todos.
Los puntos totales suman mejores marcas por colección/partido/reto una sola vez,
independientemente del filtro del medallero. Repetir no acumula esa marca de nuevo.

Al primer intento de jugar se pide un **apodo local**, sin email ni contraseña.
Se guarda en `tribunapp.campanas.profile.v1` junto con preferencias de recorrido y
reto. Cambiarlo renombra el mismo perfil y conserva el progreso anterior; no crea
varios usuarios. No identifica al usuario en otros dispositivos ni recupera datos
borrados. Si el almacenamiento está bloqueado, se avisa y se puede jugar en memoria.
Las partidas incompletas siguen sin guardarse: se retoma desde el último reto terminado.
`tribunapp.campanas.activity.v1` registra las campañas empezadas, su equipo y última
configuración, sin guardar respuestas parciales ni crear una cuenta.

## Formación del club y rival de referencia

En campañas históricas y en el torneo filtrado por club, sólo se piden los **once
jugadores del club elegido**, tanto de local como de visitante. Completar esos once
termina el reto; los puntos y pistas mantienen la misma regla por jugador (máximo 33).
El tablero sigue mostrando rival, marcador, fecha y estadio. **Ver rival** muestra
su once completo como referencia, sin inputs, sin pistas, sin puntos adicionales y
sin borrar lo que el usuario está escribiendo. Se puede volver a ocultar.

Con **Todos los equipos** se mantienen ambos once (22 apellidos, máximo 66). En la
final de Madrid de 2018 (`espn-528144`) se ofrece explícitamente jugar ambos once,
antes de responder, pedir pistas o revelar al rival; sigue siendo opcional.
Goleadores y resultado conservan las planillas y reglas previas.

El progreso nuevo de formación guarda `formationClub`; resolver el once de Boca no
marca como resuelto el de su rival ni el desafío de ambos equipos en el Apertura.
Los registros anteriores sin ese campo representan los 22 apellidos y siguen siendo
válidos. `playClub` conserva el equipo con el que se jugó. Los puntos globales usan la
mejor marca por colección/partido/reto, sin sumar otra vez por cambiar de equipo.

Las tres fotografías se generaron con ElevenLabs (`gpt-image-2.5-sunburst`) en el
flujo `KqC3C4D8huEO80H9Pwwq`: formación `MYJPIJ6R7GUCvA1Qn8oi`, goleadores
`oiv8nW2pgMjrqPKxe6iK`, resultado `x2VmfJcIz44uJXdxA5GR`. Son ilustraciones
fotográficas genéricas, no imágenes documentales de partidos. Se sirven localmente
desde `assets/campanas/` en WebP de 768×432: aproximadamente 110 KB entre las tres.

## Arquitectura

- `campanas.html`: página estática con navegación nativa. `/campanas` tiene rewrite.
- `css/campanas.css`: presentación aislada; sin framework ni build nuevo.
- `css/campanas-nav.css`: adaptación del header existente a cinco accesos.
- `js/campanas-core.js`: reglas puras, aliases, elegibilidad, goleadores y puntajes.
- `js/campanas-progress.js`: almacenamiento versionado y tolerancia a JSON corrupto,
  datos incompletos, duplicados o almacenamiento bloqueado.
- `js/campanas-ui.js`: vistas y eventos; no llamadas a Supabase ni a APIs deportivas.
- `data/campanas/recorridos.json`: índice sin respuestas con IDs, clubes y retos
  disponibles; permite calcular medallas sin descargar todas las formaciones.
- `scripts/build-campanas-journeys.cjs`: regenera ese índice después de cualquier
  importación o corrección de colecciones. La prueba detecta índices desactualizados.
- `data/campanas/apertura-2026.json`: colección con fuentes, slugs, versión y calidad.
- `scripts/import-campanas.mjs`: conversión reproducible del prototipo local; usa
  los overrides que realmente aplicaba `page.tsx` por fecha (10), no todos los seeds.
- `scripts/test-campanas.cjs`: pruebas de reglas, contenido y persistencia.

La clave de progreso es `tribunapp.campanas.progress.v1`. No se migra automáticamente
`la-planilla-archive`: vive en otro origen y sus puntajes acumulativos no representan
una marca independiente por partido. No se usan IPs, cuentas ni IDs de voto existentes.

## Datos y límites editoriales

Los 255 partidos se conservan en formación y resultado. Hay 220 partidos con goles,
pero sólo 193 desafíos de goleadores están habilitados: quedan fuera aquellos con
autores ausentes del XI/banco o identidad ambigua. Se evitan así candidatos inventados
y pistas involuntarias que revelarían la respuesta. `scorerAmbiguous`,
`scorerIncomplete`, `qualityWarnings` y `quality` documentan las razones.

Los nombres originales permanecen intactos. `accepted_answers` agrega nombres
completos para abreviaturas que se pudieron resolver con datos del mismo equipo/dorsal;
la UI usa esos nombres para las pistas. No es una auditoría histórica independiente.
El jugador `Max` de Gimnasia (#16) necesita verificación editorial. Las fichas se
podrán corregir y volver a importar sin alterar sus IDs estables.

Las respuestas están en JSON público, igual que en el prototipo. El puntaje es
recreativo y local: no constituye una clasificación competitiva validada por servidor.

## Reproducción y validación

```powershell
node scripts/import-campanas.mjs "C:\ruta\a\mvp-la-planilla"
node scripts/build-campanas-journeys.cjs
node --test scripts/test-campanas.cjs scripts/test-historical-campaigns.cjs scripts/test-campanas-journeys.cjs
node --check js/campanas-ui.js
node --check js/campanas-progress.js
python scripts/check_datos.py
python -m http.server 8765 --bind 127.0.0.1
```

En servidor estático visitar `/campanas.html`; `/campanas` requiere Vercel.
La primera colección no depende del proxy de Vercel.

Pruebas manuales realizadas en navegador: formación completa con 22 respuestas y
una ayuda (65 puntos), resultado correcto (+20), resultado incorrecto (-5), goleadores
con selección/deshacer y ayuda (+14), persistencia tras recarga, archivo, filtro por
club, ocultamiento de los 22 dorsales después de dos partidos de un club y revelación
del dorsal mediante pista. Revisar de nuevo luego de cambios funcionales.

## Antes de integrar a producción

### Revisión de ayudas y archivo (18/09/2026)

Las letras reemplazan el placeholder dentro del propio input del apellido, sin una
pista debajo. Al escribir se muestra la respuesta del usuario; al vaciar el campo
vuelve la pista. Pedir otra ayuda no borra lo escrito. Cada jugador vale 3 puntos
sin ayuda, 2 tras la primera, 1 tras
la segunda y 0 desde la tercera; revelar dos letras o la mitad de un apellido corto
también anula los puntos. Una revelación completa resuelve automáticamente sin sumar.
Si falta el dorsal, la primera pista pasa directamente a la longitud del apellido.

Las ayudas de goleadores siempre eliminan candidatos nuevos; la última deja sólo
autores reales y vale 0 puntos. Las selecciones de jugadores descartados se retiran
con un aviso; las ayudas sin candidatos para eliminar se deshabilitan sin penalizar.
Se indica cuánto vale acertar antes de confirmar. Los errores siguen restando 5.

El archivo agrupa por partido y ofrece modos pendientes, incluso cuando el reto
anterior terminó con 0 o puntaje negativo. Al completar también se ofrecen esos
modos; el reto adicional guarda su propia marca. Sólo cuando no quedan pendientes
se ofrece repetir explícitamente. Formación y resultado no revelan los goleadores
en su cierre para permitir intentar el reto pendiente.

Revisar el diseño con Fede, resolver observaciones de juego y realizar el control
adicional solicitado con Cloud. El push a `campanas` puede generar un preview de
Vercel; producción sigue en `master`. Merge y publicación definitiva requieren el
OK del usuario. No habilitar ni modificar workflows automáticos.

Pruebas de navegador: `scripts/test-campanas-browser.cjs` cubre los 72 inicios de
modo históricos, las pistas y el archivo; `scripts/test-campanas-journeys-browser.cjs`
verifica medallas, rutas, filtros, apodo, progreso anterior, transición desde
goleadores cuando quedan 0–0, vistas móviles y almacenamiento bloqueado. Se usa un
navegador aislado, sin tocar los resultados reales del usuario.
`scripts/test-campanas-access-browser.cjs` prueba el acceso visible, la selección
rápida, campañas personales vacías y empezadas, cierre con once apellidos, referencia
gratuita del rival, borradores de respuesta y opción de 22 jugadores en Madrid.

### Planillas, medallero y retos aleatorios (31/10/2026)

- “Ver rival” pasa a una barra sobre las planillas. En escritorio, ambos once
  empiezan a la misma altura y tienen igual ancho; en celular se apilan. Consultar
  al rival sigue siendo gratuito y conserva las respuestas en curso.
- Todos los retos ordenan por posición: arquero, defensa, medio y delantero.
  Los índices originales se conservan para que respuestas y pistas sigan apuntando
  al mismo jugador. Donde faltan posiciones (Apertura y suplementos editoriales)
  se mantiene el orden de formación de la fuente, sin deducir roles por dorsal
  ni presuponer un 4-4-2.
- Se corrigen roles erróneos de Boca 2007, incluido Caranta como mediocampista.
  `scripts/campanas-position-overrides.json` registra IDs y fuentes. El importador
  usa `apply-campanas-positions.cjs`, que conserva `sourcePos` y `positionSource`.
  No cambian las identidades, los integrantes del once ni las incidencias.
- “Retos aleatorios” es un botón dentro de la campaña y una opción del acceso
  rápido, sin cuarta tarjeta. Sortea partido y reto entre los disponibles del club
  y recorrido elegidos; prioriza partidos sin terminar, evita repetir el recién
  saltado si hay otro pendiente y excluye goleadores en 0–0 o fichas no aptas.
- El azar es una preferencia, no un cuarto tipo de puntaje: archivo y medallas
  guardan el reto real. “Siguiente” mantiene el azar; elegir un reto fijo sale de
  él. Al completar el recorrido se abre el medallero como en los modos fijos.
- El medallero reemplaza los óvalos I/II/III por tres filas con nombre, partidos
  completados y barra. Los recorridos terminados se destacan en dorado.

Pruebas adicionales: `node --test scripts/test-campanas-random-order.cjs` y
`node scripts/test-campanas-random-browser.cjs` (Playwright). Cubren orden e identidad
en todas las colecciones, Caranta, elegibilidad, persistencia del reto real,
siguiente/saltar, acceso rápido y alineación en escritorio/celular.
