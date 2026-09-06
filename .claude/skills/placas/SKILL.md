---
name: placas
description: Genera las placas de TribunApp para redes en los tres momentos de un partido — la previa (partido de hoy), las formaciones confirmadas (los 22 en una cancha) y el final del partido (resultado + goleadores). Usar cuando el usuario pida una placa, la previa, las formaciones, el cierre, o mande capturas con los once iniciales.
allowed-tools: Bash, Read, SendUserFile
---

# Las placas de TribunApp

Tres momentos, tres scripts. **Ninguno publica nada**: todos escriben en
`data/social/preview/`, que está en `.gitignore` y `.vercelignore`. El tweet lo
hace Fede a mano — el proyecto no tiene credenciales de X cargadas.

Todo se corre desde la **carpeta de producción**, nunca desde el repo git:

```bash
cd "C:/Users/feder/OneDrive/Escritorio/tribunapp-deploy/tribunappdeploy"
export API_SPORTS_KEY="$(tr -d '\r\n' < "C:/Users/feder/OneDrive/Escritorio/TribunApp/scripts/.apikey")"
```

Al terminar cada placa, **mandásela al usuario con SendUserFile** (`display: render`).

---

## 1. Previa — "Partido de hoy"

Una placa por partido: escudos grandes, hora y fecha. `social_fecha.py`.

```bash
python scripts/social_fecha.py --cada-uno --date 2026-09-06 --titulo "Partido de hoy"
```

- **`--cada-uno` es lo que quiere Fede**: una placa por partido. Sin ese flag hace
  una sola con la lista del día, que es otro formato.
- `--titulo`: usar **"Partido de hoy"** si se postea ese día y **"Próximo partido"**
  si se manda con anticipación (el subtítulo ya dice el día, así que "hoy" mentiría).
- Sale en `data/social/preview/fecha-{fecha}-{local}-{visitante}.png`.
- Para varios días, correr una vez por fecha.

---

## 2. Formaciones confirmadas — los 22 en una cancha

**Este es el formato que Fede quiere para las previas de formación**: `social_xi_cruce.py`,
los 22 enfrentados en una cancha apaisada. **No** las dos placas verticales de
`social_lineups.py` (una por equipo), que están descartadas.

```bash
python scripts/social_xi_cruce.py --lineups <json> --sub "Fecha 8 · 19:00"
```

El JSON es `[{slug, nombre, formacion, startXI}, ...]` (local, visitante), con
`startXI` en formato api-sports:

```json
{"player": {"id": null, "name": "M. Belmonte", "number": 8, "pos": null, "grid": "3:2"}}
```

`grid` es `"fila:columna"`: **fila 1 = arquero** y crece hacia el ataque; **columna 1 =
izquierda del equipo**. La placa espeja al visitante sola, así que "izquierda" es
siempre desde la perspectiva de cada equipo.

### La regla crítica: las listas vienen de derecha a izquierda

**Las placas oficiales de los clubes listan de derecha a izquierda.** Hay que
**invertir cada línea** antes de asignar las columnas. Confirmado varias veces
contra api-sports (la defensa invertida coincide exacta con su `grid`).

- Vale también cuando la placa del club está escrita en **filas** (San Lorenzo), no
  solo en lista vertical.
- **Excepción**: si la captura es un **dibujo posicional** en una cancha (Aldosivi,
  Tigre), se lee directo de izquierda a derecha — no invertir.
- Riestra agrupa distinto: arquero / 3 centrales / 2 laterales / 3 volantes / 2
  delanteros. La línea de 5 se arma metiendo los centrales entre los dos carrileros.

### Antes de generar

1. **Pedirle a Fede la formación de cada equipo** si no la dijo; el dibujo no siempre
   la deja clara (5-3-2 vs 3-5-2).
2. **Cruzar el once contra `data/planteles/{slug}.json`** por dorsal. Si un nombre no
   coincide, casi siempre es el plantel el que está viejo — verificar con api-sports
   `players/squads` y con `scraper_planteles.fetch_squad`, y corregir el plantel
   (ver la skill `actualizar-planteles`).
3. **Consultar api-sports** `fixtures/lineups?fixture={id}` aunque tengas las
   capturas: sirve para validar el orden y a veces tiene el once antes. Pero **si
   discrepa con la placa del club, gana la placa del club** (caso real: api-sports
   daba Estudiantes RC 3-1-4-2 cuando el club anunció 4-4-2, y le faltaba Sarmiento
   entero).

### Nombres

El script muestra solo el apellido y **respeta los compuestos** (Barros Schelotto,
González Pírez, Lima Morais). Si querés forzar un nombre puntual, pasalo **sin punto**
y con nombre de pila incluido: `"Rick Lima Morais"` → *Lima Morais*. Un nombre con
punto (`"R. Lima Morais"`) se resuelve contra el plantel y puede pisarse.

---

## 3. Cierre — "Final del partido"

Resultado, goleadores con minuto y estadio. `social_resultado.py`.

```bash
python scripts/social_resultado.py --check   # ¿hay candidatos?
python scripts/social_resultado.py           # genera
```

- Ventana: partidos que arrancaron hace **entre 100 y 300 minutos**.
- Toma el estado de api-sports por `fixtures?id=`, que marca FT al toque.
- Sale en `data/social/preview/ft-{api_id}-{local}-{visitante}.png`.
- Marca el partido como posteado en `data/social/resultados_posted.json`, así que no
  lo regenera. Para rehacerlo hay que sacar la entrada de ese archivo.
- **Ojo con el orden**: la placa invita a puntuar, así que conviene **cerrar el
  partido primero** (skill `actualizar-fecha`) para que los puntajes estén abiertos
  cuando la gente entre desde el link.

---

## Detalles que ya costaron una corrección

- **`env -u PYTHONIOENCODING`** al correr los scripts de social: algunos imprimen
  caracteres que rompen la consola de Windows si se fuerza otra codificación.
- Playwright tarda ~20 s por placa. Para 12 placas, dar timeout de 10 minutos.
- **Mirar la imagen antes de mandarla** (Read sobre el PNG). Los errores típicos —
  un jugador de más, un lateral del lado equivocado, un apellido cortado — solo se
  ven mirando.
- Si un club juega con un dorsal que no está en el plantel, el script muestra igual
  el nombre que le pasaste; pero conviene arreglar el plantel, porque ese dorsal
  también afecta la sección Formación de la web.
