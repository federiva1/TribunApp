// Mapa de calor de un jugador — dibujo propio de TribunApp.
//
// Entra una lista de acciones [[x, y], ...] en METROS sobre una cancha de 105×68
// (data/mapas/{id}.json, ver scripts/fetch_mapas.py: x=0 es el arco propio, el
// equipo ataca hacia x=105; y=0 es su banda izquierda) y sale un <canvas>:
// cancha azul noche con líneas tenues y la densidad de acciones en escala de
// calor: crema/amarillo (pocas) → naranja → rojo (muchas). Sobre el azul, los
// cálidos dan el contraste máximo y se leen como "calor" sin explicación. La
// intensidad se calcula como la de FotMob (ver abajo), en absoluto.
//
// API: window.mcCanvas(puntos, { espejado, ancho }) → HTMLCanvasElement
//   espejado: rota 180° (el visitante en la cancha apaisada de Formaciones, que
//             ataca hacia la izquierda) para que el mapa coincida con donde está
//             el chip que se tocó.
//   ancho:    ancho CSS en px (el alto sale de 105×68).
(function () {
  var L = 105, A = 68;          // cancha en metros
  var CELDA = 0.5;              // grilla de densidad (m)

  // Mismo modelo que el mapa de FotMob, para que la intensidad cuente lo mismo:
  // cada acción es un disco de RADIO metros con un degradé radial (opacidad 0.54
  // en el centro → 0 en el borde), los discos se APILAN como capas semitransparentes
  // (1 − Π(1 − a), así la intensidad satura y no crece sin techo), se desenfoca la
  // capa (σ = BLUR m) y el color sale de esa intensidad ABSOLUTA. No se normaliza
  // al máximo de cada jugador: un toque aislado queda como una mancha amarilla
  // chica y el rojo exige varias acciones en el mismo lugar. Antes normalizábamos
  // por jugador con un kernel más ancho, y un delantero con 19 toques se veía
  // tan "caliente" como un volante con 80.
  var RADIO = 7.5, BLUR = 1.5;
  var DEGRADE = [[0, 0.54], [0.2, 0.378], [0.4, 0.243], [0.6, 0.135], [0.8, 0.054], [1, 0]];
  var OPACIDAD = 0.88;          // de toda la capa, sobre la cancha

  // Escala de calor por intensidad 0..1: [posición, r, g, b]. Los cortes son los
  // de la escala de FotMob (su menta→verde es nuestro crema→amarillo claro; su
  // amarillo, naranja y rojo caen en el mismo lugar): un toque aislado queda
  // amarillo claro y el rojo exige varias acciones en el mismo lugar.
  var RAMPA = [
    [0.00, 254, 243, 199],
    [0.31, 253, 230, 138],
    [0.63, 250, 204,  21],
    [0.78, 251, 146,  60],
    [0.92, 239,  68,  68],
    [1.00, 220,  38,  38],
  ];
  // La mancha aparece entre DESDE y HASTA y de ahí es opaca: semitransparentes
  // sobre el azul daban un verde oliva sucio. El halo tenue de FotMob (menta
  // sobre césped verde) casi no se ve; sobre el azul sí, por eso el corte es
  // más adentro y las manchas miden lo mismo que en FotMob.
  var DESDE = 0.10, HASTA = 0.22;
  function color(t) {
    for (var i = 1; i < RAMPA.length; i++) {
      if (t <= RAMPA[i][0]) {
        var a = RAMPA[i - 1], b = RAMPA[i], f = (t - a[0]) / (b[0] - a[0]);
        return [a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f];
      }
    }
    var u = RAMPA[RAMPA.length - 1];
    return [u[1], u[2], u[3]];
  }
  function degrade(f) {
    for (var i = 1; i < DEGRADE.length; i++) {
      if (f <= DEGRADE[i][0]) {
        var a = DEGRADE[i - 1], b = DEGRADE[i];
        return a[1] + (b[1] - a[1]) * (f - a[0]) / (b[0] - a[0]);
      }
    }
    return 0;
  }

  // Desenfoque gaussiano separable sobre la grilla.
  function desenfocar(v, W, H, sigma) {
    var r = Math.ceil(3 * sigma), k = [], s = 0, i, x, y;
    for (i = -r; i <= r; i++) { k.push(Math.exp(-i * i / (2 * sigma * sigma))); s += k[k.length - 1]; }
    for (i = 0; i < k.length; i++) k[i] /= s;
    var tmp = new Float32Array(W * H), out = new Float32Array(W * H);
    for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
      var acc = 0;
      for (i = -r; i <= r; i++) { var xx = x + i; if (xx >= 0 && xx < W) acc += v[y * W + xx] * k[i + r]; }
      tmp[y * W + x] = acc;
    }
    for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
      var acc2 = 0;
      for (i = -r; i <= r; i++) { var yy = y + i; if (yy >= 0 && yy < H) acc2 += tmp[yy * W + x] * k[i + r]; }
      out[y * W + x] = acc2;
    }
    return out;
  }

  // Intensidad → canvas chico (una celda = un píxel); después se escala con suavizado.
  function capaCalor(puntos) {
    var W = Math.round(L / CELDA), H = Math.round(A / CELDA);
    var trans = new Float32Array(W * H).fill(1);      // Π(1 − a)
    var r = Math.ceil(RADIO / CELDA);
    puntos.forEach(function (p) {
      var cx = p[0] / CELDA, cy = p[1] / CELDA;
      var x0 = Math.max(0, Math.floor(cx - r)), x1 = Math.min(W - 1, Math.ceil(cx + r));
      var y0 = Math.max(0, Math.floor(cy - r)), y1 = Math.min(H - 1, Math.ceil(cy + r));
      for (var y = y0; y <= y1; y++) {
        for (var x = x0; x <= x1; x++) {
          var dx = (x + 0.5 - cx) * CELDA, dy = (y + 0.5 - cy) * CELDA;
          var f = Math.sqrt(dx * dx + dy * dy) / RADIO;
          if (f < 1) trans[y * W + x] *= 1 - degrade(f);
        }
      }
    });
    for (var i = 0; i < W * H; i++) trans[i] = 1 - trans[i];
    var inten = desenfocar(trans, W, H, BLUR / CELDA);
    var cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    var ctx = cv.getContext('2d'), img = ctx.createImageData(W, H), d = img.data;
    for (i = 0; i < W * H; i++) {
      var t = Math.min(1, inten[i]);
      if (t <= DESDE) continue;
      var c = color(t), al = Math.min(1, (t - DESDE) / (HASTA - DESDE)) * OPACIDAD;
      d[i * 4] = c[0]; d[i * 4 + 1] = c[1]; d[i * 4 + 2] = c[2]; d[i * 4 + 3] = Math.round(al * 255);
    }
    ctx.putImageData(img, 0, 0);
    return cv;
  }

  // Líneas reglamentarias (medidas FIFA), en metros.
  function lineas(ctx, s) {
    ctx.strokeStyle = 'rgba(255,255,255,.22)';
    ctx.lineWidth = Math.max(1, s * 0.22);
    var R = function (x, y, w, h) { ctx.strokeRect(x * s, y * s, w * s, h * s); };
    R(0, 0, L, A);
    ctx.beginPath(); ctx.moveTo(L / 2 * s, 0); ctx.lineTo(L / 2 * s, A * s); ctx.stroke();
    ctx.beginPath(); ctx.arc(L / 2 * s, A / 2 * s, 9.15 * s, 0, 2 * Math.PI); ctx.stroke();
    var ya = (A - 40.32) / 2, yc = (A - 18.32) / 2;
    R(0, ya, 16.5, 40.32); R(L - 16.5, ya, 16.5, 40.32);   // áreas grandes
    R(0, yc, 5.5, 18.32);  R(L - 5.5, yc, 5.5, 18.32);     // áreas chicas
    // medialunas: solo el arco fuera del área
    var ang = Math.acos((16.5 - 11) / 9.15);
    ctx.beginPath(); ctx.arc(11 * s, A / 2 * s, 9.15 * s, -ang, ang); ctx.stroke();
    ctx.beginPath(); ctx.arc((L - 11) * s, A / 2 * s, 9.15 * s, Math.PI - ang, Math.PI + ang); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,.3)';
    [[L / 2, A / 2], [11, A / 2], [L - 11, A / 2]].forEach(function (p) {
      ctx.beginPath(); ctx.arc(p[0] * s, p[1] * s, Math.max(1.2, s * 0.3), 0, 2 * Math.PI); ctx.fill();
    });
  }

  window.mcCanvas = function (puntos, opts) {
    opts = opts || {};
    var ancho = opts.ancho || 420, alto = ancho * A / L;
    var dpr = Math.min(window.devicePixelRatio || 1, 3);
    var cv = document.createElement('canvas');
    cv.width = Math.round(ancho * dpr); cv.height = Math.round(alto * dpr);
    cv.style.width = '100%'; cv.style.maxWidth = ancho + 'px'; cv.style.aspectRatio = L + '/' + A;
    cv.style.display = 'block';
    var ctx = cv.getContext('2d'), s = cv.width / L;

    // césped: azul noche con franjas apenas marcadas
    var g = ctx.createLinearGradient(0, 0, cv.width, cv.height);
    g.addColorStop(0, '#13213a'); g.addColorStop(1, '#0c1628');
    ctx.fillStyle = g; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = 'rgba(255,255,255,.025)';
    for (var i = 0; i < 10; i += 2) ctx.fillRect(i * L / 10 * s, 0, L / 10 * s, cv.height);

    if (opts.espejado) { ctx.save(); ctx.translate(cv.width, cv.height); ctx.rotate(Math.PI); }
    if (puntos && puntos.length) {
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(capaCalor(puntos), 0, 0, cv.width, cv.height);
    }
    if (opts.espejado) ctx.restore();
    lineas(ctx, s);                      // las líneas van encima del calor
    return cv;
  };
})();
