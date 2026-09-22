# Campañas históricas: primera tanda jugable

18/09/2026. Rama `campanas`; no implica publicación en `master`.

## Alcance

Dos campañas para cada uno de los 12 clubes nombrados por Fede: 24 colecciones.
El Apertura 2026 existente sigue disponible sin cambios en sus datos. Se entra por
el selector de torneo/campañas, se filtra por club y se elige cualquiera de los tres
retos. El archivo y las marcas se guardan por colección, partido y modo, en el
navegador. No hay login ni nuevos servicios de pago.

| Club | Campaña A | Campaña B |
| --- | --- | --- |
| Boca | Libertadores 2007 (14 partidos) | Liga Profesional 2022 (27) |
| River | Libertadores 2015 (14, uno suspendido) | Libertadores 2018 (14) |
| San Lorenzo | Inicial 2013 (19) | Libertadores 2014 (14) |
| Racing | Primera División 2014 (19) | Sudamericana 2024 (13) |
| Independiente | Sudamericana 2010 (10) | Sudamericana 2017 (12) |
| Rosario Central | Copa Argentina 2018 (6) | Copa de la Liga 2023 (17) |
| Newell’s | Final 2013 (19) | Sudamericana 2023 (8) |
| Argentinos Juniors | Clausura 2010 (19) | Libertadores 2023 (8) |
| Gimnasia LP | Copa Argentina 2018 (6) | Clausura 2025 (19) |
| Estudiantes LP | Libertadores 2009 (16, incluye clasificación) | Copa Argentina 2023 (6) |
| Huracán | Copa Argentina 2014 (6) | Sudamericana 2015 (10) |
| Lanús | Sudamericana 2013 (10) | Primera División 2016 (17) |

Se priorizaron títulos y recorridos recordados con fichas recuperables. No es una
selección definitiva de las dos mejores campañas de cada club. Se descartó para
esta tanda Newell’s 2004 porque la fuente consultada no aportaba sus alineaciones;
se eligió la Sudamericana 2023. Gimnasia 2018 y 2025, Huracán 2015 y Argentinos 2023
son recorridos destacados, no títulos.

323 apariciones de partidos dentro de las campañas (no necesariamente 323 encuentros
únicos: dos clubes pueden compartir un cruce). Disponibles: 322 en formación, 289
en goleadores y 322 en resultado. El Boca–River suspendido de 2015 queda documentado
pero fuera del juego. Los 0–0 no participan en goleadores. La tanda ofrece 933 retos
por colección/modo, además del Apertura existente.

## Fuentes y tratamiento

La base son las fichas públicas de ESPN: cada encuentro conserva `source`,
`sourceApi` y fecha de consulta. No se usaron planteles anuales para inventar onces.
Los goles en contra se asignan al autor real y al marcador beneficiado; los penales
de desempate no se suman al resultado ni al reto de goleadores. El tiempo extra sí.

Siete fichas sin XI en ESPN se completaron con síntesis posteriores al partido,
en `scripts/historical-lineup-overrides.json`. Sus URLs quedan en cada JSON:

- [Central–Juventud Antoniana 2018, organizador](https://www.copaargentina.org/es/partido/3104_Rosario-Central-vs-Juventud-Antoniana.html).
- [Gimnasia–Sportivo Belgrano 2018, síntesis](https://pisandolaredonda.blogspot.com/2018/07/sin-copa-argentina.html), contrastando el autor Lucas Licht con [FotMob](https://www.fotmob.com/matches/gimnasia-lp-vs-sportivo-belgrano/bhsfc8x).
- [Estudiantes–Independiente de Chivilcoy 2023](https://universofutbol.com/copa-argentina/2023/sintesis/32avos/estudiantes-la-plata-indepndiente-chivilcoy.php?res=255318).
- [Huracán–Crucero del Norte 2014](https://www.diariopopular.com.ar/futbol/copa-argentina-huracan-elimino-crucero-los-penales-n191208).
- [Boca–Huracán 2014](https://www.losandes.com.ar/miralo-en-vivo-en-san-juan-boca-se-prueba-ante-huracan).
- [Huracán–Central, final 2014](https://www.diariojornada.com.ar/112575/deportes/copa_argentina_huracan_se_corono_campeon).
- [Lanús–Racing, Sudamericana 2013](https://lanusatokio.blogspot.com/2013/08/), contrastado con [Fútbol Granate](https://futboldelgranate.blogspot.com/2013/).

Sólo se incorporan hechos de las síntesis: nombres, condición de titular/ingresado,
autores y minutos. No se reproducen las crónicas. Los números y posiciones faltantes
quedan nulos; el juego salta la ayuda del dorsal cuando no existe. Los suplentes
abreviados conservan la inicial publicada, sin completar nombres por suposición.
Las fuentes secundarias pueden tener errores: la validación estructural no reemplaza
una auditoría histórica independiente de cada dato. Las tarjetas/incidencias no
están garantizadas como exhaustivas y no habilitan un reto de expulsados.

Para las fichas antiguas de ESPN se eliminan eventos y jugadores duplicados. Cuando
las banderas de titular están dañadas, se usan las estadísticas del mismo encuentro
(`appearances=1`, `subIns=0`) únicamente si permiten identificar once jugadores.
La identidad de los clubes pedidos se resuelve por ID; no se confunde Independiente
de Chivilcoy con Independiente de Avellaneda por similitud de nombre.

## Archivos y reproducción

- `scripts/historical-campaigns.json`: selección, IDs, competiciones, fechas y conteos esperados.
- `scripts/import-historical-campaigns.cjs`: importador y controles por reto.
- `scripts/historical-lineup-overrides.json`: complementos editoriales con fuentes.
- `data/campanas/catalog.json`: índice liviano; cada colección se carga al elegirla.
- `data/campanas/<id>.json`: fichas compactas. No se suben respuestas crudas ni caché.

```powershell
node scripts/import-historical-campaigns.cjs --inventory
node scripts/import-historical-campaigns.cjs
node --test scripts/test-campanas.cjs scripts/test-historical-campaigns.cjs
node scripts/test-campanas-browser.cjs
python scripts/check_datos.py
```

El importador necesita red pública; no requiere API key. Cachea fuera del repositorio
en `%TEMP%/tribunapp-historical-espn-v1`; allí deja también `audit.json`. El test de
navegador requiere Playwright (o `PLAYWRIGHT_MODULE`) y Chrome. Usa un contexto
aislado e intercepta recursos locales: no envía votos ni toca la cuenta del usuario.

Se comprueban cantidad e identidad de campañas/partidos, once por lado, autores y
marcadores, ayudas, penales y suplemento editorial. La prueba de navegador inicia
los 72 pares campaña/modo, verifica el Apertura original, pista dentro del input,
reducción efectiva de candidatos y archivo/progreso independiente incluso con 0 puntos.
