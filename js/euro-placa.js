/* EUROTRIBUNAPP: imagen descargable de la formación (cancha + las 11 fichas con el kit del club).
   Se dibuja a mano en un <canvas>, sin librerías (html2canvas no pinta los degradados repetidos de los kits).
   Necesita js/kits.js, js/euro-kits.js y js/euro.js; los escudos salen de escudos/euro/ (mismo origen:
   no "contaminan" el canvas).

   EURO.placaFormacion({ club: {id, nombre, color}, rival, cuando, jugadores: [{num, nombre, x, y}] }) → Promise<Blob PNG>
   EURO.bajarPlaca(blob, nombre) · EURO.compartirPlaca(blob, titulo) */
(function () {
  const W = 1080, H = 1500, PX = 60, PY = 205, PW = 960, PH = Math.round(960 / 0.82);   // cancha con la proporción de la web (0,82)
  const NAVY = '#0d0d1a';

  function cargarImg(src) {
    return new Promise(res => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
  }

  // Kit dentro de un círculo: mismos patrones y proporciones que kitBackground() de js/kits.js
  function kit(ctx, k, cx, cy, r) {
    const d = r * 2, x0 = cx - r, y0 = cy - r, a = k.colors[0], b = k.colors[1] || '#ffffff';
    const w = Math.max(3, Math.round(d / (k.div || 6)));
    ctx.save();
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = a; ctx.fillRect(x0, y0, d, d);
    const franjas = (dir) => {                       // bastones alternados a/b
      for (let i = 0, p = 0; p < d; i++, p += w) {
        ctx.fillStyle = i % 2 ? b : a;
        if (dir === 'v') ctx.fillRect(x0 + p, y0, w, d); else ctx.fillRect(x0, y0 + d - p - w, d, w);   // los horizontales arrancan abajo (0deg)
      }
    };
    const degrade = (xa, ya, xb, yb, stops) => {
      const g = ctx.createLinearGradient(xa, ya, xb, yb);
      stops.forEach(([o, c]) => g.addColorStop(o, c)); ctx.fillStyle = g; ctx.fillRect(x0, y0, d, d);
    };
    switch (k.type) {
      case 'stripesV': franjas('v'); break;
      case 'stripesH': franjas('h'); break;
      case 'halves': ctx.fillStyle = b; ctx.fillRect(cx, y0, r, d); break;
      case 'band': ctx.fillStyle = b; ctx.fillRect(x0, y0 + d * 0.36, d, d * 0.28); break;
      case 'bandV': ctx.fillStyle = b; ctx.fillRect(x0 + d * 0.33, y0, d * 0.34, d); break;
      case 'sash': degrade(x0, y0 + d, x0 + d, y0, [[0, a], [0.42, a], [0.42, b], [0.58, b], [0.58, a], [1, a]]); break;
      case 'sashR': degrade(x0 + d, y0 + d, x0, y0, [[0, a], [0.42, a], [0.42, b], [0.58, b], [0.58, a], [1, a]]); break;
      default: break;
    }
    ctx.restore();
  }

  function cancha(ctx) {
    ctx.save();
    ctx.beginPath(); ctx.roundRect(PX, PY, PW, PH, 22); ctx.clip();
    for (let i = 0; i < 8; i++) { ctx.fillStyle = i % 2 ? '#2a7336' : '#2d7a3a'; ctx.fillRect(PX + i * PW / 8, PY, PW / 8, PH); }
    const sx = PW / 100, sy = PH / 122, X = v => PX + v * sx, Y = v => PY + v * sy;
    ctx.strokeStyle = 'rgba(255,255,255,0.6)'; ctx.lineWidth = 4;
    ctx.strokeRect(X(3), Y(3), 94 * sx, 116 * sy);
    ctx.beginPath(); ctx.moveTo(X(3), Y(61)); ctx.lineTo(X(97), Y(61)); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(X(50), Y(61), 11 * sx, 11 * sx, 0, 0, Math.PI * 2); ctx.stroke();
    [[25, 3, 50, 18], [38, 3, 24, 7], [25, 101, 50, 18], [38, 112, 24, 7]].forEach(([a, b, c, e]) => ctx.strokeRect(X(a), Y(b), c * sx, e * sy));
    ctx.restore();
    ctx.strokeStyle = 'rgba(255,255,255,0.25)'; ctx.lineWidth = 4; ctx.beginPath(); ctx.roundRect(PX, PY, PW, PH, 22); ctx.stroke();
  }

  function texto(ctx, t, x, y, fuente, color, align, borde) {
    ctx.font = fuente; ctx.textAlign = align || 'left'; ctx.textBaseline = 'middle';
    if (borde) { ctx.lineJoin = 'round'; ctx.lineWidth = borde; ctx.strokeStyle = 'rgba(0,0,0,0.65)'; ctx.strokeText(t, x, y); }
    ctx.fillStyle = color; ctx.fillText(t, x, y);
  }

  EURO.placaFormacion = async function (o) {
    try { await Promise.all([document.fonts.load('60px "Bebas Neue"'), document.fonts.load('600 40px "Barlow Condensed"')]); } catch (e) {}
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const ctx = cv.getContext('2d');
    const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#16192e'); g.addColorStop(1, NAVY);
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

    // Cabecera: escudo + título
    const escudo = await cargarImg(EURO.escudo(o.club.id));
    if (escudo) { const h = 110, w = escudo.width * h / escudo.height; ctx.drawImage(escudo, PX, 48, Math.min(w, 140), h); }
    const tx = PX + 160;
    texto(ctx, 'MI FORMACIÓN', tx, 70, '42px "Bebas Neue"', '#ffd54f', 'left');
    texto(ctx, `${o.club.nombre.toUpperCase()}${o.rival ? '  vs  ' + o.rival.toUpperCase() : ''}`, tx, 122, '64px "Bebas Neue"', '#ffffff', 'left');
    if (o.cuando) texto(ctx, o.cuando, tx, 168, '600 32px "Barlow Condensed"', 'rgba(255,255,255,0.65)', 'left');

    cancha(ctx);

    // Fichas
    const kitClub = EURO.kit(o.club.id, o.club.color), R = 50;
    for (const j of o.jugadores) {
      const cx = PX + PW * j.x / 100, cy = PY + PH * j.y / 100;
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.55)'; ctx.shadowBlur = 14; ctx.shadowOffsetY = 5;
      ctx.beginPath(); ctx.arc(cx, cy, R + 4, 0, Math.PI * 2); ctx.fillStyle = '#fff'; ctx.fill(); ctx.restore();
      kit(ctx, kitClub, cx, cy, R);
      texto(ctx, String(j.num != null ? j.num : ''), cx, cy + 3, '58px "Bebas Neue"', '#ffffff', 'center', 8);
      const nombre = EURO.apellido(j.nombre).toUpperCase();
      ctx.font = '600 31px "Barlow Condensed"';
      const tw = Math.min(190, ctx.measureText(nombre).width + 22);
      ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.beginPath(); ctx.roundRect(cx - tw / 2, cy + R + 8, tw, 40, 10); ctx.fill();
      ctx.save(); ctx.beginPath(); ctx.rect(cx - tw / 2, cy + R + 8, tw, 40); ctx.clip();
      texto(ctx, nombre, cx, cy + R + 29, '600 31px "Barlow Condensed"', '#ffffff', 'center');
      ctx.restore();
    }

    // Pie: marca
    const marca = await cargarImg('icon-192.png');
    if (marca) ctx.drawImage(marca, PX, H - 92, 62, 62);
    texto(ctx, 'TRIBUNAPP', PX + 78, H - 58, 'italic 800 44px "Barlow Condensed", sans-serif', '#ffffff', 'left');
    texto(ctx, 'tribunapp.com.ar', W - PX, H - 58, '600 34px "Barlow Condensed"', 'rgba(255,255,255,0.7)', 'right');

    return new Promise((res, rej) => cv.toBlob(b => b ? res(b) : rej(new Error('no se pudo generar la imagen')), 'image/png'));
  };

  EURO.bajarPlaca = function (blob, nombre) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = nombre || 'formacion-tribunapp.png';
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  };

  // Menú de compartir del celular (si el navegador lo permite con archivos); si no, la descarga
  EURO.compartirPlaca = async function (blob, titulo, nombre) {
    const f = new File([blob], nombre || 'formacion-tribunapp.png', { type: 'image/png' });
    try {
      if (navigator.canShare && navigator.canShare({ files: [f] })) { await navigator.share({ files: [f], title: titulo, text: titulo + ' · tribunapp.com.ar' }); return 'compartido'; }
    } catch (e) { if (e && e.name === 'AbortError') return 'cancelado'; }
    EURO.bajarPlaca(blob, nombre); return 'descargado';
  };
})();
