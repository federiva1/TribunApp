# Campañas: integración y reglas vigentes

Estado al 31/10/2026: revisión en la rama `campanas`, sin merge a `master`.

## Campaña unificada

El usuario eligió reemplazar la elección de retos y el modo aleatorio por un único
recorrido por partido: **formación → bonus resultado → bonus goleadores**. El Apertura
2026 conserva sus 255 partidos y 30 clubes, más 24 campañas históricas de 12 clubes.
No hay login, sincronización ni clasificación pública.

La portada de Campañas conserva el título y los 30 escudos. Las tres imágenes explican
las etapas, no son opciones para elegir modos. Se elige campaña, club y recorrido;
“Jugar” abre esa selección compacta y recuerda la última campaña. La página principal
`index.html` de TribunApp no forma parte de este cambio.

### Etapas y protección de respuestas

1. **Formación:** completar el once del club elegido hace avanzar la campaña. Con
   todos los equipos se piden los 22 apellidos. Al abrir la formación, el resultado
   siempre queda oculto, incluso si hay partidas antiguas guardadas; tampoco
   se muestran metadatos que incluyan la tanda de penales. Las ayudas conservan sus
   reglas anteriores y se muestran dentro del input. El botón pequeño “Ver resultado”
   revela el marcador y registra ese bonus como jugado a 0 puntos. No termina la
   formación ni modifica sus ayudas, borradores o puntos. Si ya se había jugado ese
   bonus, se conserva la marca previa sin volver a sumar ni restar.
2. **Resultado, opcional:** sólo después de la formación. El marcador editable y
   su separador están centrados respecto del tablero. “Confirmar resultado” queda
   debajo y es más compacto. Durante este bonus no se repiten las planillas.
3. **Goleadores, opcional:** se ofrece después de responder u omitir el resultado.
   Omitirlo lo revela y guarda `skipped: true`, con 0 puntos, antes de mostrar los
   candidatos. No se puede volver a sumar por ese resultado ya revelado. Los 0–0
   y las fichas no aptas no ofrecen este bonus.

Al completar la formación, incluso a 0 puntos, la acción principal ofrece el bonus
de resultado o directamente goleadores si el marcador ya se reveló. “Siguiente
partido” aparece al terminar los bonus disponibles; se puede continuar antes mediante
la opción secundaria explícita “Continuar sin los bonus pendientes”.
Si no se revelaron sus respuestas, se pueden retomar desde el archivo. No se ofrecen
retos independientes ni enlaces para volver a una respuesta ya revelada. El archivo
oculta el marcador cuando sigue pendiente el bonus de resultado.

El encabezado muestra el total del partido. Cada cierre detalla los puntos de la
etapa y el acumulado, con desglose por formación/resultado/goleadores. Los aciertos
parciales usan un cierre neutro, no un anuncio verde de victoria total.

### Puntaje

- Formación: 3 puntos por jugador; primera ayuda 2, segunda 1, tercera y siguientes
  0. Revelar dos letras o la mitad de un apellido corto también deja 0. Revelación
  completa resuelve automáticamente sin sumar. Los errores no descuentan.
- Resultado: exacto +20; incorrecto u omitido 0. Nunca descuenta de la formación.
- Goleadores: máximo 20, reducido a 14/8/0 según ayudas. Se reparte proporcionalmente
  entre los goles acertados y se redondea al entero más cercano. Se comparan goles
  como un multiconjunto: un jugador con dos goles requiere dos selecciones.
  Un acierto y un error en un partido de dos goles da 10 puntos sin ayudas.
  Los errores no descuentan; una selección repetida no inventa un gol extra.

Las ayudas de goleadores siempre eliminan nuevos candidatos incorrectos; la tercera
revela los autores y deja el bonus en 0. Se retiran selecciones eliminadas con aviso.
Se muestran todos los suplentes ingresados únicamente cuando hubo un goleador suplente.

## Recorridos y progreso

- Expreso: un tercio redondeado hacia arriba, máximo cinco partidos.
- Clásico: la mitad redondeada hacia arriba.
- Completo: todos los partidos con formación jugable; excluye suspendidos.

Son duraciones, no dificultades. La selección es fija, anidada y cronológica:
prioriza final, inicio y puntos intermedios. Para 19 partidos ofrece 5/10/19.
Completar **la formación** hace avanzar la medalla; los bonus no son requisito.
Los tres recorridos comparten progreso. Cambiar el club no completa automáticamente
su once: `formationClub` conserva ese alcance. El caso opcional de ambos once de
Madrid 2018 sigue disponible antes de pedir ayudas o ver al rival.

“Mis campañas” incluye sólo las empezadas, incluso antes de terminar el primer
partido. El medallero conserva filtros y tres barras de avance; los recorridos
terminados se destacan en dorado. Los puntos suman la mejor marca por colección,
partido y etapa una sola vez, sin duplicarla por cambiar de equipo.

Apodo, preferencias y actividad se guardan en este navegador. Cambiar el apodo
renombra el mismo perfil; no crea otra cuenta. Si falla el almacenamiento, se avisa
y se permite seguir en memoria. Los borradores de formación no sobreviven a una
recarga; se retoma desde la última etapa terminada.

### Compatibilidad con partidas anteriores

Se conservan las claves y las marcas anteriores. Los registros nuevos llevan
`flowVersion: 2`; los de formación anteriores ya habían mostrado el resultado,
por lo que no vuelven a ofrecer ese bonus. Lo mismo sucede con los antiguos
registros de goleadores. Esa exposición se respeta incluso al cambiar de club.
Los resultados antiguos, por sí solos, no cuentan como una formación completada.
Las penalizaciones negativas antiguas se conservan en el almacenamiento original,
pero aportan 0 al total y al archivo de la campaña nueva; los bonus nuevos no restan.

Los campos internos de preferencias de modo antiguo se leen por compatibilidad.
Al iniciar se usa siempre formación, aunque el perfil hubiera guardado `random`,
`result` o `scorers`. No queda ningún selector ni sorteo de retos.

## Planillas y posiciones

“Ver rival” está sobre las planillas. En escritorio aparecen columnas de igual ancho
alineadas arriba; en celular se apilan. La referencia es gratuita y conserva el
borrador de respuesta. No se requieren los apellidos del rival.

El orden usa posición: arquero, defensa, medio, delantero, manteniendo los índices
originales para pistas/respuestas. Donde faltan posiciones se conserva el orden de
formación de origen, sin inferir roles por dorsal ni presuponer 4-4-2. Se corrigieron
28 registros de roles en Boca 2007, incluido Caranta. Fuentes e IDs están en
`scripts/campanas-position-overrides.json`; el importador conserva `sourcePos` y
`positionSource` mediante `scripts/apply-campanas-positions.cjs`.

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

## Validación y publicación

```powershell
node --test scripts/test-campanas.cjs scripts/test-historical-campaigns.cjs scripts/test-campanas-journeys.cjs scripts/test-campanas-random-order.cjs
node --check js/campanas-ui.js
node scripts/test-campanas-browser.cjs
node scripts/test-campanas-access-browser.cjs
node scripts/test-campanas-journeys-browser.cjs
node scripts/test-campanas-random-browser.cjs
python scripts/check_datos.py
```

Los nombres de pruebas que contienen `random` se conservan por compatibilidad;
ahora cubren la migración del flujo retirado, la secuencia de bonus y el orden.
Las pruebas de navegador usan Playwright/Chrome, una sesión aislada y recursos
locales. Cubren las 25 colecciones, 11/22 apellidos, ayudas, resultados sin revelar,
archivo tras recarga, centrado en móvil/escritorio, bonus parciales/omitidos/cero,
medallas, apodo, preferencias antiguas y almacenamiento bloqueado.

La previsualización está en `campanas`; no se cambia la configuración de Vercel ni
los workflows. El merge a `master` requiere el OK del usuario.
