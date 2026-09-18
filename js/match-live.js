// Motor compartido: arma la ficha de un partido EN VIVO desde api-sports, con el
// mismo schema que data/partidos/{id}.json. Lo usan fixture.html (desplegable inline)
// y estadisticas.html (página completa). Requiere ESCUDO_MAP global (js/clubes.js).
//
// Regla de oro: una sola fuente por momento — en vivo = api-sports; al terminar el
// partido, el enriquecimiento de FotMob pisa el JSON. Así los números coinciden.
(function () {
  var EN_CURSO = ['1H', 'HT', '2H', 'ET', 'BT', 'P', 'SUSP'];

  function norm(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }
  function toInt(v) {
    if (v == null || v === '') return null;
    var n = parseInt(String(v).replace('%', ''), 10);
    return isNaN(n) ? null : n;
  }
  function slugOf(teamId, teamName) {
    if (typeof ESCUDO_MAP !== 'undefined' && ESCUDO_MAP[teamId]) return ESCUDO_MAP[teamId];
    return norm(teamName || '').replace(/[^a-z0-9]/g, '') || String(teamId || '');
  }

  function transformLive(fx, lineups, events, stats) {
    var home = fx.teams.home, away = fx.teams.away, homeId = home.id, awayId = away.id;
    var localSlug = slugOf(homeId, home.name), visitSlug = slugOf(awayId, away.name);
    var goals = fx.goals, fixture = fx.fixture;
    var fecha = (fixture.date || '').slice(0, 10);
    var estadio = (fixture.venue && fixture.venue.name) || '';
    if (fixture.venue && fixture.venue.city) estadio = estadio ? (estadio + ', ' + fixture.venue.city) : fixture.venue.city;
    var competicion = (fx.league && fx.league.name) || 'Liga Profesional';

    // ── eventos: goles + cambios + tarjetas ──
    var evInfo = {};
    function getEv(pid) { return (evInfo[pid] = evInfo[pid] || { goles: 0, asist: 0, amarilla: false, roja: false, minSale: null }); }
    var subsIn = {}, golesLocal = [], golesVisit = [];
    (events || []).forEach(function (ev) {
      var etype = ev.type || '', detail = ev.detail || '';
      var minute = toInt(ev.time && ev.time.elapsed);
      var teamId = ev.team && ev.team.id, player = ev.player || {}, assist = ev.assist || {};
      var pid = player.id, aid = assist.id;
      if (etype === 'Goal') {
        if (detail === 'Missed Penalty') return;
        if (!pid) return;
        var entry = { min: minute, jugador: player.name || '', asist: assist.name || null };
        if (detail === 'Own Goal') { entry.asist = null; entry.en_contra = true; }
        else { if (pid) getEv(pid).goles++; if (aid) getEv(aid).asist++; }
        if (teamId === homeId) golesLocal.push(entry); else golesVisit.push(entry);
      } else if (etype === 'Card') {
        if (pid) { var e = getEv(pid); if (detail.indexOf('Red') >= 0) e.roja = true; else e.amarilla = true; }
      } else if (etype === 'subst') {
        if (pid) getEv(pid).minSale = minute;
        if (aid && teamId != null) { (subsIn[teamId] = subsIn[teamId] || []).push({ id: aid, name: assist.name || '', minIn: minute }); }
      }
    });

    // ── lineups ──
    var luByTeam = {};
    (lineups || []).forEach(function (lu) { luByTeam[lu.team.id] = lu; });
    function buildPlayers(teamId, isLocal) {
      var lu = luByTeam[teamId] || {}, golesRecibidos = (isLocal ? goals.away : goals.home) || 0, fullNameById = {}, numById = {};
      (lu.startXI || []).concat(lu.substitutes || []).forEach(function (p) { var pl = p.player || {}; if (pl.id) { fullNameById[pl.id] = pl.name || ''; numById[pl.id] = pl.number; } });
      var outp = [];
      (lu.startXI || []).forEach(function (p) {
        var pl = p.player || {}, pid = pl.id, isGk = (pl.pos === 'G'), ev = evInfo[pid] || {};
        outp.push({
          nombre: pl.name || '', id: pid, tipo: 'titular', portero: isGk, mvp: false,
          grid: pl.grid || null,   // "fila:col" del lineup (fila 1 = arquero) — lo usa la cancha de la ficha
          num: String(pl.number || ''), min: ev.minSale || 90, min_in: null, min_sale: ev.minSale || null,
          goles: ev.goles || 0, asist: ev.asist || 0, amarilla: ev.amarilla || false, roja: ev.roja || false,
          top: null, ataque: null, defensa: null, duelos: null,
          portero_stats: isGk ? { paradas: null, goles_contra: golesRecibidos, goles_evitados: null } : null
        });
      });
      (subsIn[teamId] || []).forEach(function (s) {
        var ev = evInfo[s.id] || {};
        outp.push({
          nombre: fullNameById[s.id] || s.name, id: s.id, tipo: 'suplente', portero: false, mvp: false,
          num: String(numById[s.id] || ''), min: s.minIn ? (90 - s.minIn) : null, min_in: s.minIn || null, min_sale: ev.minSale || null,
          goles: ev.goles || 0, asist: ev.asist || 0, amarilla: ev.amarilla || false, roja: ev.roja || false,
          top: null, ataque: null, defensa: null, duelos: null, portero_stats: null
        });
      });
      var coach = lu.coach || {};
      if (coach && coach.name) {
        outp.push({ nombre: coach.name, id: coach.id, tipo: 'dt', portero: false, mvp: false, num: '', min: null, min_in: null, min_sale: null, goles: 0, asist: 0, amarilla: false, roja: false, top: null, ataque: null, defensa: null, duelos: null, portero_stats: null });
      }
      var seen = {}, ded = [];
      outp.forEach(function (e) { if (e.id && seen[e.id]) return; if (e.id) seen[e.id] = 1; ded.push(e); });
      return ded;
    }
    var localJugs = buildPlayers(homeId, true), visitJugs = buildPlayers(awayId, false);

    // ── top stats globales ──
    var statsByTeam = {};
    (stats || []).forEach(function (ts) { statsByTeam[ts.team.id] = ts.statistics || []; });
    function statVal(tid, key) { var arr = statsByTeam[tid] || []; for (var i = 0; i < arr.length; i++) if (arr[i].type === key) return arr[i].value; return null; }
    var STAT_MAP = [
      ['Ball Possession', 'Posesion', 'posesion'], ['expected_goals', 'xG', 'numero'],
      ['Total Shots', 'Tiros totales', 'numero'], ['Shots on Goal', 'Tiros al arco', 'numero'],
      ['Shots insidebox', 'Toques en area rival', 'numero'], ['Corner Kicks', 'Corners', 'numero'],
      ['Fouls', 'Faltas', 'numero'], ['Yellow Cards', 'Tarjetas amarillas', 'numero'], ['Red Cards', 'Tarjetas rojas', 'numero']
    ];
    var topStats = [];
    STAT_MAP.forEach(function (row) {
      var key = row[0], label = row[1], tipo = row[2], hv = statVal(homeId, key), av = statVal(awayId, key);
      if (hv == null && av == null) return;
      if (tipo === 'posesion') { var h = toInt(hv) || 0, a = toInt(av) || 0; topStats.push({ label: label, local: h, visitante: a, tipo: tipo, local_val: h, visitante_val: a }); }
      else if (key === 'expected_goals') {
        var sx = function (v) { if (v == null || v === '') return null; var n = parseFloat(String(v)); return isNaN(n) ? null : Math.round(n * 100) / 100; };
        var xh = sx(hv), xa = sx(av);
        topStats.push({ label: label, local: xh == null ? '—' : xh, visitante: xa == null ? '—' : xa, tipo: tipo, local_val: xh || 0, visitante_val: xa || 0 });
      } else { var nh = hv != null ? toInt(hv) : 0, na = av != null ? toInt(av) : 0; topStats.push({ label: label, local: nh, visitante: na, tipo: tipo, local_val: nh, visitante_val: na }); }
    });
    var hpAcc = toInt(statVal(homeId, 'Passes accurate')), hpTot = toInt(statVal(homeId, 'Total passes'));
    var apAcc = toInt(statVal(awayId, 'Passes accurate')), apTot = toInt(statVal(awayId, 'Total passes'));
    if (hpAcc != null) {
      var hpPct = hpTot ? Math.round(hpAcc / hpTot * 100) : 0, apPct = (apTot && apAcc != null) ? Math.round(apAcc / apTot * 100) : 0;
      topStats.push({ label: 'Pases precisos', local: hpAcc + ' (' + hpPct + '%)', visitante: (apAcc != null ? apAcc : 0) + ' (' + apPct + '%)', tipo: 'texto', local_val: hpPct, visitante_val: apPct });
    }

    return {
      partido: {
        local: localSlug, visitante: visitSlug, goles_local: goals.home, goles_visitante: goals.away,
        // Nombres api-sports para mostrar: en copa el rival extranjero no está en
        // CLUBES_CONFIG y su slug derivado ("deportivorecoleta") no sirve de etiqueta.
        local_nombre: home.name || '', visitante_nombre: away.name || '',
        fecha: fecha, estadio: estadio, competicion: competicion, api_id: String(fixture.id),
        goles_detalle: { local: golesLocal, visitante: golesVisit },
        formacion: (function () {
          var f = {};
          f[localSlug] = (luByTeam[homeId] || {}).formation || '';
          f[visitSlug] = (luByTeam[awayId] || {}).formation || '';
          return f;
        })()
      },
      top_stats: topStats,
      jugadores: (function () { var o = {}; o[localSlug] = localJugs; o[visitSlug] = visitJugs; return o; })()
    };
  }

  // ── Fallback FotMob (vía /api/fotmob) cuando api-sports no publica lineups ──
  // Caso real: IndRiv-Racing F7 del Clausura, fixtures/lineups devolvía response:[]
  // con el partido en juego, mientras FotMob tenía los dos XI. Regla asentada:
  // demora/hueco de api-sports ⇒ FotMob tapa el agujero. api-sports sigue siendo
  // la fuente primaria — esto solo actúa si faltan titulares o posiciones.
  function _fmMatchNombre(abrev, lista) {
    // "S. Sosa" (api-sports) vs "Santiago Sosa" (FotMob): mismo último token +
    // primer token igual o inicial coincidente. Devuelve el jugador o null.
    var a = norm(abrev).replace(/\./g, '').split(/\s+/).filter(Boolean);
    if (!a.length) return null;
    var hits = lista.filter(function (j) {
      var n = norm(j.nombre).split(/\s+/).filter(Boolean);
      if (!n.length || n[n.length - 1] !== a[a.length - 1]) return false;
      return a.length < 2 || n[0] === a[0] || (a[0].length === 1 && n[0].charAt(0) === a[0]);
    });
    return hits.length === 1 ? hits[0] : null;
  }
  function _fmAplicar(data, slug, info, esLocal, ev) {
    if (!info || !(info.titulares || []).length) return;
    var jug = data.jugadores[slug] || (data.jugadores[slug] = []);
    var tit = jug.filter(function (j) { return j.tipo === 'titular'; });
    if (tit.length >= 7) {
      // api-sports trajo el XI pero sin grid: solo completar posiciones.
      var porNum = {}, lista = info.titulares.filter(function (t) { return t.pos; });
      lista.forEach(function (t) { if (t.num) porNum[t.num] = t.pos; });
      tit.forEach(function (j) {
        if (j.grid || j.pos) return;
        var xy = porNum[String(j.num || '')] || (function () {
          var m = _fmMatchNombre(j.nombre, lista); return m && m.pos;
        })();
        if (xy) j.pos = xy;
      });
    } else {
      // Sin XI de api-sports: se arma entero desde FotMob. Goles/asistencias se
      // marcan cruzando con goles_detalle (que sí viene, de fixtures/events).
      var goles = (data.partido.goles_detalle || {})[esLocal ? 'local' : 'visitante'] || [];
      var golesRecibidos = esLocal ? data.partido.goles_visitante : data.partido.goles_local;
      var nuevos = info.titulares.map(function (t) {
        return {
          nombre: t.nombre, id: null, tipo: 'titular', portero: !!t.portero, mvp: false,
          pos: t.pos || null, num: t.num || '', min: 90, min_in: null, min_sale: null,
          goles: 0, asist: 0, amarilla: false, roja: false,
          top: null, ataque: null, defensa: null, duelos: null,
          portero_stats: t.portero ? { paradas: null, goles_contra: golesRecibidos || 0, goles_evitados: null } : null
        };
      });
      goles.forEach(function (g) {
        if (g.en_contra) return;
        var j = _fmMatchNombre(g.jugador || '', nuevos); if (j) j.goles++;
        if (g.asist) { var a = _fmMatchNombre(g.asist, nuevos); if (a) a.asist++; }
      });
      // Tarjetas y salidas de los titulares, cruzadas por nombre con los eventos
      // (el XI de FotMob no tiene los ids de api-sports).
      ((ev || {}).cards || []).forEach(function (c) {
        var j = _fmMatchNombre(c.nombre, nuevos);
        if (j) { if (c.roja) j.roja = true; else j.amarilla = true; }
      });
      ((ev || {}).salidas || []).forEach(function (s) {
        var j = _fmMatchNombre(s.nombre, nuevos);
        if (j) { j.min_sale = s.min; j.min = s.min || j.min; }
      });
      data.jugadores[slug] = nuevos.concat(jug.filter(function (j) { return j.tipo !== 'titular'; }));
    }
    if (info.formacion && !data.partido.formacion[slug]) data.partido.formacion[slug] = info.formacion;
  }
  async function _fmFallback(data, fx, events) {
    // Stats globales EN VIVO: FotMob primario SIEMPRE, no solo cuando api-sports
    // viene vacío — la auditoría de la F7 mostró que api-sports sirve snapshots
    // congelados de mitad de partido indistinguibles de datos reales (Boca-Lanús
    // FT con xG 0.36 cuando el real era 1.16). Misma política que el pipeline
    // post-partido: api-sports queda de fallback si FotMob no tiene el partido.
    var p = data.partido;
    var res = await fetch('/api/fotmob?home=' + encodeURIComponent(p.local) +
      '&away=' + encodeURIComponent(p.visitante) + '&date=' + encodeURIComponent(p.fecha));
    if (!res.ok) return;
    var body = (await res.json()) || {};
    if ((body.top_stats || []).length) data.top_stats = body.top_stats;
    var fm = body.lineup;
    if (!fm) return;
    function evSide(tid) {
      var cards = [], salidas = [];
      (events || []).forEach(function (ev) {
        if (!ev.team || ev.team.id !== tid || !ev.player || !ev.player.name) return;
        var min = toInt(ev.time && ev.time.elapsed);
        if (ev.type === 'Card') cards.push({ nombre: ev.player.name, roja: (ev.detail || '').indexOf('Red') >= 0, min: min });
        else if (ev.type === 'subst') salidas.push({ nombre: ev.player.name, min: min });
      });
      return { cards: cards, salidas: salidas };
    }
    _fmAplicar(data, p.local, fm[p.local], true, evSide(fx.teams.home.id));
    _fmAplicar(data, p.visitante, fm[p.visitante], false, evSide(fx.teams.away.id));
  }

  // Fetchea api-sports y devuelve { data, short, elapsed } (o null si falla / no existe).
  async function buildPayloadLive(apiId) {
    var base = '/api/apisports/', opt = { cache: 'no-store' };
    var res = await Promise.all([
      fetch(base + 'fixtures?id=' + apiId, opt),
      fetch(base + 'fixtures/lineups?fixture=' + apiId, opt),
      fetch(base + 'fixtures/events?fixture=' + apiId, opt),
      fetch(base + 'fixtures/statistics?fixture=' + apiId, opt)
    ]);
    if (!res[0].ok) return null;
    var fx = (((await res[0].json()).response) || [])[0];
    if (!fx) return null;
    var lineups = res[1].ok ? (((await res[1].json()).response) || []) : [];
    var events = res[2].ok ? (((await res[2].json()).response) || []) : [];
    var stats = res[3].ok ? (((await res[3].json()).response) || []) : [];
    var data = transformLive(fx, lineups, events, stats);
    try { await _fmFallback(data, fx, events); } catch (e) { /* FotMob caído ≠ ficha rota */ }
    return { data: data, short: fx.fixture.status.short, elapsed: fx.fixture.status.elapsed };
  }

  window.buildPayloadLive = buildPayloadLive;
  window.mlTransformLive = transformLive;
  window.mlIsEnCurso = function (s) { return EN_CURSO.indexOf(s) >= 0; };
})();
