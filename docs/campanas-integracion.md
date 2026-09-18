# Campañas: primera integración

Estado: implementación para revisión en la rama `campanas`, sin merge a `master`.

## Alcance acordado

Primer corte con el Apertura 2026 existente: 255 partidos, 30 clubes, tres modos,
filtro por club y archivo personal. Sin login, sincronización ni rankings públicos.
Se guarda la mejor marca por colección/partido/modo en este navegador, con cantidad
de intentos y fechas. Una respuesta incorrecta también termina el desafío; repetirlo
no multiplica la mejor marca. Abandonar o recargar una partida incompleta no la guarda.

Las siguientes colecciones se decidirán después de revisar este juego. Las 60
opciones de `campanas-objetivos.md` son objetivos editoriales, no datasets producidos.

## Arquitectura

- `campanas.html`: página estática con navegación nativa. `/campanas` tiene rewrite.
- `css/campanas.css`: presentación aislada; sin framework ni build nuevo.
- `css/campanas-nav.css`: adaptación del header existente a cinco accesos.
- `js/campanas-core.js`: reglas puras, aliases, elegibilidad, goleadores y puntajes.
- `js/campanas-progress.js`: almacenamiento versionado y tolerancia a JSON corrupto,
  datos incompletos, duplicados o almacenamiento bloqueado.
- `js/campanas-ui.js`: vistas y eventos; no llamadas a Supabase ni a APIs deportivas.
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
node --test scripts/test-campanas.cjs
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

Revisar el diseño con Fede, resolver observaciones de juego y realizar el control
adicional solicitado con Cloud. El push a `campanas` puede generar un preview de
Vercel; producción sigue en `master`. Merge y publicación definitiva requieren el
OK del usuario. No habilitar ni modificar workflows automáticos.
