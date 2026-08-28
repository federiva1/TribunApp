// Cancha de la ficha del partido — módulo compartido (fixture.html + index.html).
// Dibuja las dos formaciones como en las placas: kit chips (js/kits.js) ubicados
// por el grid del lineup de api-sports ("fila:col", fila 1 = arquero, col 1 =
// izquierda — misma convención que social_lineups), nombre en pastilla, marcas de
// goles/asistencias/tarjetas y ▼min del que salió; abajo "Ingresaron" con el kit
// chip del que entró y su ▲min. Requiere js/kits.js (clubKit/kitBackground/NUM_OUTLINE).
//
// API: window.fcCanchaHTML(data, opts) → HTML de las dos canchas, o null si algún
// lineup no tiene grid confirmado (el caller decide su fallback). data = schema de
// match-live.js / data/partidos. opts.nomFn(slug, nombreApi) resuelve la etiqueta.
(function () {
  var CSS = ''
    + '.fc-teams{display:grid;grid-template-columns:repeat(2,minmax(0,260px));justify-content:center;gap:10px 22px;align-items:start}'
    + '@media (max-width:560px){.fc-teams{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 8px}}'
    + '.fc-hdr{display:flex;align-items:center;gap:6px;margin-bottom:4px}'
    + '.fc-hdr img{width:17px;height:17px;object-fit:contain}'
    + ".fc-hdr .fc-nom{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:rgba(255,255,255,.7);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
    + ".fc-hdr .fc-form{margin-left:auto;font-family:'Barlow Condensed',sans-serif;font-size:11px;letter-spacing:1px;color:rgba(255,255,255,.42);flex-shrink:0}"
    + '.fc-pitch{position:relative;width:100%;aspect-ratio:100/126;border-radius:8px;overflow:hidden;'
    +   'border:1px solid rgba(255,255,255,.08);'
    +   'background:repeating-linear-gradient(0deg,rgba(255,255,255,.04) 0 12.5%,transparent 12.5% 25%),linear-gradient(160deg,#12492a,#0a2f1a)}'
    + '.fc-l{position:absolute;border:1.5px solid rgba(255,255,255,.16);pointer-events:none}'
    + '.fc-l-line{left:0;right:0;top:50%;border-width:1.5px 0 0 0}'
    + '.fc-l-circle{left:50%;top:50%;width:24%;aspect-ratio:1;transform:translate(-50%,-50%);border-radius:50%}'
    + '.fc-l-area-b{left:24%;right:24%;bottom:-2px;height:13%;border-bottom:none}'
    + '.fc-l-area-t{left:24%;right:24%;top:-2px;height:13%;border-top:none}'
    + '.fc-spot{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;gap:1px;width:25%}'
    + '.fc-kit{display:inline-flex;align-items:center;justify-content:center;border-radius:50%;'
    +   'border:1.5px solid rgba(255,255,255,.75);box-shadow:0 2px 5px rgba(0,0,0,.45);flex-shrink:0}'
    + ".fc-kit span{font-family:'Barlow Condensed',sans-serif;font-weight:700;color:#fff;line-height:1}"
    + ".fc-nm{display:flex;align-items:center;gap:3px;max-width:100%;font-family:'Barlow Condensed',sans-serif;font-size:10px;line-height:1.15;"
    +   'color:#fff;background:rgba(10,16,28,.72);border-radius:6px;padding:1px 5px}'
    + '.fc-nm i{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-style:normal}'
    + '.fc-out{color:#ef9a9a;font-size:9px;flex-shrink:0}'
    + '.fc-in-tag{color:#81c784;font-size:10px;flex-shrink:0}'
    + '.fc-mk{font-size:9px;line-height:1;text-shadow:0 1px 2px rgba(0,0,0,.6)}'
    + ".fc-subhdr{font-family:'Barlow Condensed',sans-serif;font-size:10px;letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,.32);margin:6px 0 2px}"
    + '.fc-in{display:flex;flex-direction:column;gap:2px;margin-top:2px}'
    + ".fc-in-row{display:flex;align-items:center;gap:6px;font-family:'Barlow Condensed',sans-serif;font-size:12px;color:rgba(255,255,255,.88)}"
    + '.fc-in-row .fc-kit span{font-size:9px}'
    + '.fc-in-nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'
    // layout horizontal: una sola cancha apaisada con los dos equipos enfrentados
    + '.fc-h{max-width:640px;margin:0 auto}'
    + '.fc-h-hdr{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px}'
    + '.fc-h-hdr .fc-hdr{margin-bottom:0;min-width:0}'
    + '.fc-h-hdr .fc-hdr.away{flex-direction:row-reverse}'
    + '.fc-h-hdr .fc-hdr .fc-form{margin-left:0}'
    + '.fc-pitch-h{position:relative;width:100%;aspect-ratio:16/9.6;border-radius:8px;overflow:hidden;'
    +   'border:1px solid rgba(255,255,255,.08);'
    +   'background:repeating-linear-gradient(90deg,rgba(255,255,255,.04) 0 12.5%,transparent 12.5% 25%),linear-gradient(160deg,#12492a,#0a2f1a)}'
    + '.fc-pitch-h .fc-l-line{left:50%;top:0;bottom:0;right:auto;border-width:0 0 0 1.5px}'
    + '.fc-pitch-h .fc-l-area-l{top:26%;bottom:26%;left:-2px;width:9%;border-left:none}'
    + '.fc-pitch-h .fc-l-area-r{top:26%;bottom:26%;right:-2px;width:9%;border-right:none}'
    + '.fc-pitch-h .fc-l-circle{width:14%}'
    + '.fc-pitch-h .fc-spot{width:12%}'
    + '.fc-pitch-h .fc-nm{font-size:9px;padding:1px 3px}'
    + '.fc-h-in{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px;align-items:start;margin-top:4px}'
    + '@media (max-width:520px){.fc-pitch-h .fc-nm{font-size:8px;padding:0 2px}.fc-pitch-h .fc-spot{width:13%}}'
    // stats globales del partido (mismo look que el desplegable del fixture)
    + '.fc-st{max-width:360px;margin:0 auto}'
    + ".fc-st-hdr{display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:10px;font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;letter-spacing:.5px;text-transform:uppercase}"
    + '.fc-st-hdr .fc-st-vs{color:rgba(255,255,255,.3);font-weight:400;font-size:11px;letter-spacing:1px}'
    + '.fc-st-poss{margin-bottom:9px}'
    + '.fc-st-poss-bar{display:flex;height:22px;border-radius:4px;overflow:hidden}'
    + ".fc-st-poss-bar>div{display:flex;align-items:center;font-family:'Bebas Neue',sans-serif;font-size:13px;padding:0 7px;box-sizing:border-box}"
    + '.fc-st-poss-bar>div:first-child{justify-content:flex-start}'
    + '.fc-st-poss-bar>div:last-child{justify-content:flex-end}'
    + ".fc-st-poss-lbl{text-align:center;font-family:'Barlow Condensed',sans-serif;font-size:10px;letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,.35);margin-top:3px}"
    + '.fc-st-row{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,.05)}'
    + ".fc-st-val{font-family:'Bebas Neue',sans-serif;font-size:17px;line-height:1}"
    + '.fc-st-row .fc-st-val:first-child{text-align:left}'
    + '.fc-st-row .fc-st-val:last-child{text-align:right}'
    + ".fc-st-lbl{font-family:'Barlow Condensed',sans-serif;font-size:12px;letter-spacing:.4px;color:rgba(255,255,255,.55);padding:0 12px;white-space:nowrap}"
    + ".fc-st-empty{text-align:center;padding:12px;font-family:'Barlow Condensed',sans-serif;font-size:12px;letter-spacing:1px;color:rgba(255,255,255,.3)}";

  function inject() {
    if (document.getElementById('fc-css')) return;
    var st = document.createElement('style');
    st.id = 'fc-css';
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function marks(j) {
    var out = '';
    for (var i = 0; i < (j.goles || 0); i++) out += '⚽';
    if (j.asist > 0) out += '🅰';
    if (j.roja) out += '🟥'; else if (j.amarilla) out += '🟨';
    return out;
  }
  function kitChip(slug, num, size) {
    var kit = clubKit(slug);
    return '<span class="fc-kit" style="width:' + size + 'px;height:' + size + 'px;background:' + kitBackground(kit, size) + '">'
      + '<span style="font-size:' + Math.round(size * 0.44) + 'px;text-shadow:' + NUM_OUTLINE + '">' + esc(num || '') + '</span></span>';
  }
  function shortName(n) {
    n = String(n || '');
    if (n.length <= 16) return n;
    var parts = n.split(/\s+/);
    return parts.length > 1 ? parts.slice(1).join(' ') : n;
  }

  function pitchHTML(slug, tit, sub) {
    var rows = {};
    tit.forEach(function (j) {
      var m = /^(\d+):(\d+)$/.exec(j.grid || '');
      if (!m) return;
      (rows[+m[1]] = rows[+m[1]] || []).push({ j: j, c: +m[2] });
    });
    var filas = Object.keys(rows).map(Number).sort(function (a, b) { return a - b; });
    var maxF = filas[filas.length - 1];
    var chips = [];
    filas.forEach(function (f) {
      var arr = rows[f].sort(function (a, b) { return a.c - b.c; });
      var y = f === 1 ? 89 : (maxF > 2 ? 73 - (f - 2) * (60 / (maxF - 2)) : 40);
      arr.forEach(function (e, i) {
        var x = (i + 1) / (arr.length + 1) * 100;
        var j = e.j;
        var sale = j.min_sale ? '<span class="fc-out">▼' + j.min_sale + "'</span>" : '';
        var mk = marks(j);
        chips.push('<div class="fc-spot" title="' + esc(j.nombre) + '" style="left:' + x + '%;top:' + y + '%">' + kitChip(slug, j.num, 28)
          + '<span class="fc-nm"><i>' + esc(shortName(j.nombre)) + '</i>' + sale + '</span>'
          + (mk ? '<span class="fc-mk">' + mk + '</span>' : '') + '</div>');
      });
    });
    var ingresaron = sub.length
      ? '<div class="fc-subhdr">Ingresaron</div><div class="fc-in">' + sub.map(function (j) {
          var mk = marks(j);
          return '<div class="fc-in-row">' + kitChip(slug, j.num, 20)
            + '<span class="fc-in-tag">▲ ' + (j.min_in ? j.min_in + "'" : '') + '</span>'
            + '<span class="fc-in-nm">' + esc(j.nombre) + '</span>'
            + (mk ? '<span class="fc-mk">' + mk + '</span>' : '') + '</div>';
        }).join('') + '</div>'
      : '';
    return '<div class="fc-pitch"><i class="fc-l fc-l-line"></i><i class="fc-l fc-l-circle"></i>'
      + '<i class="fc-l fc-l-area-t"></i><i class="fc-l fc-l-area-b"></i>' + chips.join('') + '</div>' + ingresaron;
  }

  // Chip de un titular en la cancha apaisada. lado: 'local' (arquero a la
  // izquierda, ataca a la derecha) o 'visitante' (espejado). La col 1 del grid
  // (izquierda de la placa vertical) queda arriba para el local y abajo para el
  // visitante, así los mismos carriles reales quedan enfrentados.
  function spotH(slug, j, x, y) {
    var sale = j.min_sale ? '<span class="fc-out">▼' + j.min_sale + "'</span>" : '';
    var mk = marks(j);
    return '<div class="fc-spot" title="' + esc(j.nombre) + '" style="left:' + x + '%;top:' + y + '%">' + kitChip(slug, j.num, 24)
      + '<span class="fc-nm"><i>' + esc(shortName(j.nombre)) + '</i>' + sale + '</span>'
      + (mk ? '<span class="fc-mk">' + mk + '</span>' : '') + '</div>';
  }

  function chipsHorizontales(slug, tit, lado) {
    var rows = {};
    tit.forEach(function (j) {
      var m = /^(\d+):(\d+)$/.exec(j.grid || '');
      if (!m) return;
      (rows[+m[1]] = rows[+m[1]] || []).push({ j: j, c: +m[2] });
    });
    var filas = Object.keys(rows).map(Number).sort(function (a, b) { return a - b; });
    // Sin grid (partidos terminados de data/partidos): posición REAL de FotMob
    // (j.pos, % sobre cancha apaisada con el arquero a la izquierda, por equipo).
    // Cada equipo se comprime en su mitad; el visitante se rota 180°.
    if (!filas.length) {
      return tit.filter(function (j) { return j.pos; }).map(function (j) {
        var x = lado === 'local' ? 2.5 + j.pos.x * 0.465 : 97.5 - j.pos.x * 0.465;
        var y = lado === 'local' ? j.pos.y : 100 - j.pos.y;
        return spotH(slug, j, x, Math.max(8, Math.min(92, y)));
      }).join('');
    }
    var maxF = filas[filas.length - 1];
    var chips = [];
    filas.forEach(function (f) {
      var arr = rows[f].sort(function (a, b) { return a.c - b.c; });
      var prof = f === 1 ? 6 : (maxF > 2 ? 17 + (f - 2) * (28 / (maxF - 2)) : 30);   // % desde el arco propio
      var x = lado === 'local' ? prof : 100 - prof;
      arr.forEach(function (e, i) {
        var frac = (i + 1) / (arr.length + 1);
        var y = lado === 'local' ? frac * 100 : (1 - frac) * 100;
        chips.push(spotH(slug, e.j, x, y));
      });
    });
    return chips.join('');
  }

  function ingresaronHTML(slug, sub) {
    if (!sub.length) return '';
    return '<div><div class="fc-subhdr">Ingresaron</div><div class="fc-in">' + sub.map(function (j) {
      var mk = marks(j);
      return '<div class="fc-in-row">' + kitChip(slug, j.num, 20)
        + '<span class="fc-in-tag">▲ ' + (j.min_in ? j.min_in + "'" : '') + '</span>'
        + '<span class="fc-in-nm">' + esc(j.nombre) + '</span>'
        + (mk ? '<span class="fc-mk">' + mk + '</span>' : '') + '</div>';
    }).join('') + '</div></div>';
  }

  // ── Stats globales del partido ──────────────────────────────────────────────
  // Colores de identidad por club (js/club-colors.js): texto legible sobre fondo
  // oscuro con accent; sobre la barra de posesión con textOn. En colisión de
  // predominantes se usa el alt del visitante.
  function _accent(hex) {
    if (!/^#[0-9a-f]{6}$/i.test(hex)) return hex;
    var r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    var lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    if (lum >= 0.42) return hex;
    var mix = function (v) { return Math.round(v + (255 - v) * 0.5); };
    return '#' + [mix(r), mix(g), mix(b)].map(function (v) { return v.toString(16).padStart(2, '0'); }).join('');
  }
  function _textOn(hex) {
    if (!/^#[0-9a-f]{6}$/i.test(hex)) return '#fff';
    var r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.62 ? '#15202b' : '#ffffff';
  }
  function _colDist(h1, h2) {
    var p = function (h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; };
    var a = p(h1), b = p(h2);
    return Math.sqrt(Math.pow(a[0] - b[0], 2) + Math.pow(a[1] - b[1], 2) + Math.pow(a[2] - b[2], 2));
  }
  function _matchColors(local, visit) {
    var CC = window.CLUB_COLORS || {};
    var cl = (CC[local] && CC[local].primary) || '#38bdf8';
    var cv = (CC[visit] && CC[visit].primary) || '#fb923c';
    if (_colDist(cl, cv) < 70) {
      var altV = CC[visit] && CC[visit].alt;
      if (altV && _colDist(cl, altV) >= 70) cv = altV;
      else {
        var altL = CC[local] && CC[local].alt;
        if (altL && _colDist(cv, altL) >= 70) cl = altL;
        else cv = '#fb923c';
      }
    }
    return [cl, cv];
  }
  window.fcStatsHTML = function (data, opts) {
    inject();
    opts = opts || {};
    var p = data.partido || {};
    var nomFn = opts.nomFn || function (slug, nombre) { return nombre || slug; };
    var cols = _matchColors(p.local, p.visitante), cl = cols[0], cv = cols[1];
    var al = _accent(cl), av = _accent(cv);
    var hdr = '<div class="fc-st-hdr"><span style="color:' + al + '">' + esc(nomFn(p.local, p.local_nombre))
      + '</span><span class="fc-st-vs">vs</span><span style="color:' + av + '">' + esc(nomFn(p.visitante, p.visitante_nombre)) + '</span></div>';
    var rows = (data.top_stats || []).map(function (s) {
      if (s.tipo === 'posesion') {
        return '<div class="fc-st-poss"><div class="fc-st-poss-bar">'
          + '<div style="width:' + s.local_val + '%;background:' + cl + ';color:' + _textOn(cl) + '">' + esc(s.local) + '</div>'
          + '<div style="width:' + s.visitante_val + '%;background:' + cv + ';color:' + _textOn(cv) + '">' + esc(s.visitante) + '</div>'
          + '</div><div class="fc-st-poss-lbl">' + esc(s.label) + '</div></div>';
      }
      return '<div class="fc-st-row"><span class="fc-st-val" style="color:' + al + '">' + esc(s.local) + '</span>'
        + '<span class="fc-st-lbl">' + esc(s.label) + '</span>'
        + '<span class="fc-st-val" style="color:' + av + '">' + esc(s.visitante) + '</span></div>';
    }).join('');
    return '<div class="fc-st">' + hdr + (rows || '<div class="fc-st-empty">Sin estadísticas todavía</div>') + '</div>';
  };

  // opts.layout: 'vertical' (default — una cancha por equipo, como las placas) |
  // 'horizontal' (una sola cancha apaisada con los dos equipos enfrentados; ocupa
  // mucho menos alto — la usa la tira EN JUEGO del index).
  window.fcCanchaHTML = function (data, opts) {
    inject();
    opts = opts || {};
    var p = data.partido || {};
    var nomFn = opts.nomFn || function (slug, nombre) { return nombre || slug; };
    var formaciones = p.formacion || {};
    var teams = [[p.local, (data.jugadores || {})[p.local] || [], p.local_nombre],
                 [p.visitante, (data.jugadores || {})[p.visitante] || [], p.visitante_nombre]];
    var ok = teams.every(function (t) {
      return t[1].filter(function (j) { return j.tipo === 'titular' && (j.grid || j.pos); }).length >= 7;
    });
    if (!ok) return null;
    var hdrDe = function (t, extraCls) {
      var slug = t[0];
      var form = formaciones[slug] ? '<span class="fc-form">' + esc(formaciones[slug]) + '</span>' : '';
      return '<div class="fc-hdr' + (extraCls ? ' ' + extraCls : '') + '"><img src="escudos/' + esc(slug) + '.png" alt="" onerror="this.style.display=\'none\'">'
        + '<span class="fc-nom">' + esc(nomFn(slug, t[2])) + '</span>' + form + '</div>';
    };
    var titDe = function (t) { return t[1].filter(function (j) { return j.tipo === 'titular'; }); };
    var subDe = function (t) { return t[1].filter(function (j) { return j.tipo === 'suplente'; }); };

    if (opts.layout === 'horizontal') {
      var cancha = '<div class="fc-pitch-h"><i class="fc-l fc-l-line"></i><i class="fc-l fc-l-circle"></i>'
        + '<i class="fc-l fc-l-area-l"></i><i class="fc-l fc-l-area-r"></i>'
        + chipsHorizontales(teams[0][0], titDe(teams[0]), 'local')
        + chipsHorizontales(teams[1][0], titDe(teams[1]), 'visitante') + '</div>';
      // Cada equipo conserva SU columna aunque el otro no tenga cambios (sin el
      // placeholder, el bloque del visitante se corría a la columna del local).
      var insL = ingresaronHTML(teams[0][0], subDe(teams[0]));
      var insV = ingresaronHTML(teams[1][0], subDe(teams[1]));
      var ins = (insL || insV)
        ? '<div class="fc-h-in">' + (insL || '<div></div>') + (insV || '<div></div>') + '</div>'
        : '';
      return '<div class="fc-h"><div class="fc-h-hdr">' + hdrDe(teams[0]) + hdrDe(teams[1], 'away') + '</div>'
        + cancha + ins + '</div>';
    }

    var html = teams.map(function (t) {
      var slug = t[0];
      var body = pitchHTML(slug, titDe(t), subDe(t));
      return '<div class="fc-team">' + hdrDe(t) + body + '</div>';
    }).join('');
    return '<div class="fc-teams">' + html + '</div>';
  };
})();
