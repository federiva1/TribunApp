// Mapa de calor de un jugador — dibujo propio de TribunApp.
//
// Entra una lista de acciones [[x, y], ...] en METROS sobre una cancha de 105×68
// (data/mapas/{id}.json, ver scripts/fetch_mapas.py: x=0 es el arco propio, el
// equipo ataca hacia x=105; y=0 es su banda izquierda) y sale un <canvas>:
// cancha oscura con líneas tenues y la densidad de acciones en la escala celeste
// de la página (una sola tinta, de transparente a casi blanco: más claro = más
// acciones). La densidad es un kernel gaussiano sobre una grilla de medio metro,
// normalizada al máximo de ese jugador.
//
// API: window.mcCanvas(puntos, { espejado, ancho }) → HTMLCanvasElement
//   espejado: rota 180° (el visitante en la cancha apaisada de Formaciones, que
//             ataca hacia la izquierda) para que el mapa coincida con donde está
//             el chip que se tocó.
//   ancho:    ancho CSS en px (el alto sale de 105×68).
(function () {
  var L = 105, A = 68;          // cancha en metros
  var CELDA = 0.5;              // grilla de densidad (m)
  var SIGMA = 4.2;              // radio del kernel (m)
  // Piso de la normalización. Una acción aislada vale 1 en su centro; sin piso,
  // un jugador que entró y tocó 6 pelotas se vería tan "caliente" como el que tocó
  // 80. Con piso, lo poco queda celeste tenue y el blanco exige acciones repetidas.
  var PISO = 2.5;

  // Escala secuencial de una sola tinta (celeste de la marca) sobre fondo oscuro:
  // [posición 0..1, r, g, b, alfa]. Lo poco denso queda casi transparente para que
  // se vea la cancha; lo más denso, casi blanco.
  var RAMPA = [
    [0.00,  14, 116, 144, 0.00],
    [0.12,  14, 116, 144, 0.30],
    [0.35,   6, 182, 212, 0.58],
    [0.65,  56, 189, 248, 0.82],
    [1.00, 224, 242, 254, 0.96],
  ];
  function color(t) {
    for (var i = 1; i < RAMPA.length; i++) {
      if (t <= RAMPA[i][0]) {
        var a = RAMPA[i - 1], b = RAMPA[i], f = (t - a[0]) / (b[0] - a[0]);
        return [a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f,
                a[3] + (b[3] - a[3]) * f, a[4] + (b[4] - a[4]) * f];
      }
    }
    var u = RAMPA[RAMPA.length - 1];
    return [u[1], u[2], u[3], u[4]];
  }

  // Densidad → canvas chico (una celda = un píxel); después se escala con suavizado.
  function capaCalor(puntos) {
    var W = Math.round(L / CELDA), H = Math.round(A / CELDA);
    var dens = new Float32Array(W * H), max = 0;
    var r = Math.ceil(3 * SIGMA / CELDA), k2 = 2 * SIGMA * SIGMA;
    puntos.forEach(function (p) {
      var cx = p[0] / CELDA, cy = p[1] / CELDA;
      var x0 = Math.max(0, Math.floor(cx - r)), x1 = Math.min(W - 1, Math.ceil(cx + r));
      var y0 = Math.max(0, Math.floor(cy - r)), y1 = Math.min(H - 1, Math.ceil(cy + r));
      for (var y = y0; y <= y1; y++) {
        for (var x = x0; x <= x1; x++) {
          var dx = (x + 0.5 - cx) * CELDA, dy = (y + 0.5 - cy) * CELDA;
          var v = (dens[y * W + x] += Math.exp(-(dx * dx + dy * dy) / k2));
          if (v > max) max = v;
        }
      }
    });
    max = Math.max(max, PISO);
    var cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    var ctx = cv.getContext('2d'), img = ctx.createImageData(W, H), d = img.data;
    for (var i = 0; i < W * H; i++) {
      if (!dens[i]) continue;
      var c = color(Math.min(1, dens[i] / max));
      d[i * 4] = c[0]; d[i * 4 + 1] = c[1]; d[i * 4 + 2] = c[2]; d[i * 4 + 3] = Math.round(c[3] * 255);
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
