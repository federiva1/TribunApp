// ══════════════════════════════════════════════════════════════════════════
// DEMO PARA GRABAR UN VIDEO — vive SOLO en la rama `video`. NO MERGEAR A MASTER.
// ══════════════════════════════════════════════════════════════════════════
// Simula EN VIVO un partido real ya jugado (Rosario Central 1-2 Gimnasia LP,
// Fecha 7 del Clausura, 29/8) y abre sus puntajes:
//
//  · index.html  → aparece en la tira "EN JUEGO" con el reloj arrancando en el
//    minuto 25 y avanzando solo. Al desplegarlo, Formaciones y Estadísticas salen
//    de la ficha real (data/partidos/rosariocentral-gimnasialp.json) recortada al
//    minuto: goles, cambios y estadísticas hasta ese momento.
//  · club.html   → en Gimnasia LP y Rosario Central los puntajes apuntan a ese
//    partido y quedan abiertos. Lo que se envía NO se guarda en Supabase (cada
//    toma del video sumaría un voto falso a los datos reales) ni en localStorage,
//    así se puede repetir la toma.
//
// Reloj: se guarda por pestaña (sessionStorage), así navegar index → club → index
// no lo reinicia. Pestaña nueva = arranca de nuevo en el 25'.
//   ?demomin=NN  reinicia el reloj en el minuto NN (ej. ?demomin=40, ?demomin=58)
//   ?demo=0      apaga la demo en esa carga
//
// Resguardo: en el dominio de producción (tribunapp.com.ar) no hace NADA, así que
// un merge accidental no mostraría el partido falso. Funciona en los previews de
// Vercel y en localhost.
(function () {
  if (/(^|\.)tribunapp\.com\.ar$/i.test(location.hostname)) return;
  var qs = new URLSearchParams(location.search);
  if (qs.get('demo') === '0') return;

  var D = {
    id: 'rosariocentral-gimnasialp', apiId: '1493103',
    local: 'rosariocentral', visitante: 'gimnasialp',
    homeId: 437, awayId: 434,
    minutoInicial: 25,
  };

  // ── Reloj ────────────────────────────────────────────────────────────────
  // "ko" = instante del pitazo inicial. Minutos reales desde ahí → minuto del
  // partido: 0-45 primer tiempo, 15 de entretiempo, después segundo tiempo.
  var K = 'tribunappDemoVideoKo';
  var realDe = function (min) { return min <= 45 ? min : min + 15; };
  var ko = null;
  var pedido = parseInt(qs.get('demomin'), 10);
  try { ko = parseInt(sessionStorage.getItem(K), 10) || null; } catch (e) {}
  if (!ko || !isNaN(pedido)) {
    var min0 = isNaN(pedido) ? D.minutoInicial : Math.max(0, Math.min(90, pedido));
    ko = Date.now() - realDe(min0) * 60000;
    try { sessionStorage.setItem(K, String(ko)); } catch (e) {}
  }
  D.estado = function () {
    var r = (Date.now() - ko) / 60000;
    if (r < 45) return { short: '1H', elapsed: Math.floor(r), minuto: Math.floor(r) };
    if (r < 60) return { short: 'HT', elapsed: 45, minuto: 45 };
    var m = Math.min(90, Math.floor(r) - 15);
    return { short: '2H', elapsed: m, minuto: m };
  };

  // ── Ficha real, recortada al minuto ──────────────────────────────────────
  var _fetch = window.fetch.bind(window);
  var _json = null;
  function cargarJson() {
    if (!_json) _json = _fetch('data/partidos/' + D.id + '.json', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    return _json;
  }
  var norm = function (s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim(); };

  function golesHasta(p, m) {
    var gd = p.goles_detalle || {};
    var f = function (l) { return (l || []).filter(function (g) { return g && typeof g === 'object' && g.min != null && g.min <= m; }); };
    return { local: f(gd.local), visitante: f(gd.visitante) };
  }
  // Estadísticas de equipo prorrateadas al minuto (la posesión y los % quedan
  // como terminaron). Tarjetas redondeadas hacia abajo: al 25' no hay ninguna.
  function statsHasta(top, m) {
    var f = Math.min(m, 90) / 90;
    return (top || []).map(function (s) {
      var o = Object.assign({}, s);
      if (s.tipo === 'posesion') return o;
      var tarj = /tarjeta/i.test(s.label || '');
      ['local', 'visitante'].forEach(function (lado) {
        var v = s[lado];
        if (typeof v === 'number') {
          var x = v * f;
          o[lado] = Number.isInteger(v) ? (tarj ? Math.floor(x) : Math.round(x)) : Math.round(x * 100) / 100;
          o[lado + '_val'] = o[lado];
        } else if (typeof v === 'string') {
          var mm = /^(\d+)\s*\((\d+%)\)$/.exec(v.trim());        // "489 (84%)"
          if (mm) o[lado] = Math.round(+mm[1] * f) + ' (' + mm[2] + ')';
        }
      });
      return o;
    });
  }
  // Jugadores al minuto m: titulares (▼ si ya salieron), suplentes solo si ya
  // entraron (▲), goles y asistencias solo los ya convertidos. La ficha guarda los
  // minutos jugados: el titular con min < 90 salió en ese minuto y el suplente con
  // N minutos entró en el 90 - N (aproximado, alcanza para el video).
  function jugadoresHasta(data, m) {
    var p = data.partido, gd = golesHasta(p, m), out = {};
    [p.local, p.visitante].forEach(function (slug) {
      var lado = slug === p.local ? 'local' : 'visitante';
      var js = ((data.jugadores || {})[slug] || []).map(function (j) {
        var c = Object.assign({}, j, { goles: 0, asist: 0, amarilla: null, roja: null });
        delete c.min_sale; delete c.min_in;
        if (j.tipo === 'titular' && j.min != null && j.min < 90 && m >= j.min) c.min_sale = j.min;
        if (j.tipo === 'suplente') {
          if (!(j.min > 0)) return null;
          var entra = 90 - j.min;
          if (m < entra) return null;
          c.min_in = entra;
        }
        return c;
      }).filter(Boolean);
      gd[lado].forEach(function (g) {
        if (g.en_contra) return;
        var gol = js.find(function (x) { return norm(x.nombre) === norm(g.jugador); });
        if (gol) gol.goles++;
        if (g.asist) { var a = js.find(function (x) { return norm(x.nombre) === norm(g.asist); }); if (a) a.asist++; }
      });
      out[slug] = js;
    });
    return out;
  }
  function payloadHasta(data, m) {
    var gd = golesHasta(data.partido, m);
    var partido = Object.assign({}, data.partido, {
      goles_local: gd.local.length, goles_visitante: gd.visitante.length, goles_detalle: gd,
    });
    return { partido: partido, top_stats: statsHasta(data.top_stats, m), jugadores: jugadoresHasta(data, m) };
  }

  // ── El partido en la respuesta de live=all (formato api-sports) ──────────
  function evGol(g, teamId) {
    return { type: 'Goal', detail: g.en_contra ? 'Own Goal' : 'Normal Goal', team: { id: teamId },
             player: { name: g.jugador }, time: { elapsed: g.min, extra: null } };
  }
  function fixtureFalso(data) {
    var est = D.estado(), gd = golesHasta(data.partido, est.minuto);
    return {
      fixture: { id: +D.apiId, status: { short: est.short, elapsed: est.elapsed } },
      league: { id: 128 },
      teams: { home: { id: D.homeId, name: 'Rosario Central' }, away: { id: D.awayId, name: 'Gimnasia L.P.' } },
      goals: { home: gd.local.length, away: gd.visitante.length },
      events: gd.local.map(function (g) { return evGol(g, D.homeId); })
        .concat(gd.visitante.map(function (g) { return evGol(g, D.awayId); })),
    };
  }
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : ((input && input.url) || '');
    if (url.indexOf('/api/apisports/fixtures?live=all') < 0) return _fetch(input, init);
    // Lo que haya en vivo de verdad (en local el proxy no existe → nada) + el simulado.
    return Promise.all([
      _fetch(input, init).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
      cargarJson(),
    ]).then(function (res) {
      var real = res[0] || {}, data = res[1];
      var resp = (real.response || []).filter(function (r) { return String(r.fixture && r.fixture.id) !== D.apiId; });
      if (data) resp.unshift(fixtureFalso(data));
      return new Response(JSON.stringify(Object.assign({}, real, { response: resp, results: resp.length })),
        { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
  };

  // La ficha desplegable pide buildPayloadLive(apiId) (js/match-live.js): para el
  // partido simulado se arma desde la ficha real, sin tocar api-sports.
  function envolver() {
    var orig = window.buildPayloadLive;
    if (!orig || orig.__demo) return;
    var w = function (apiId) {
      if (String(apiId) !== D.apiId) return orig.apply(this, arguments);
      return cargarJson().then(function (data) {
        if (!data) return null;
        var est = D.estado();
        return { data: payloadHasta(data, est.minuto), short: est.short, elapsed: est.elapsed };
      });
    };
    w.__demo = true;
    window.buildPayloadLive = w;
  }
  envolver();
  document.addEventListener('DOMContentLoaded', envolver);

  // ── Puntajes (los usa club.html) ──────────────────────────────────────────
  D.puntajesDe = function (slug) { return slug === D.local || slug === D.visitante; };
  D.esPartido = function (id) { return id === D.id; };

  window.DEMO_VIDEO = D;
  try { console.info('[demo video] activo: ' + D.id + ' simulado en vivo — ?demomin=NN reinicia el reloj, ?demo=0 lo apaga'); } catch (e) {}
})();
