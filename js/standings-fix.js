// Corrección de posiciones con los partidos que api-sports todavía no contabilizó.
//
// El endpoint /standings se actualiza con lag: tras IndRiv 3-1 Racing (F7) seguía
// dando a IndRiv con 6 PJ y 8 pts horas después del final, así que el index y
// tablas.html mostraban la tabla vieja. `data/fixtures/liga.json` sí tiene el
// resultado (lo cierra el workflow cierre-rapido, con reparación por FotMob), así
// que se completan las filas con los FT que la API aún no cuenta.
//
// Cuando la API se pone al día no hay diferencia de PJ y esto no toca nada —
// misma regla de siempre: api-sports es la fuente primaria, esto solo tapa el hueco.
//
// API: window.sfCorregirGrupos(groups, liga) → muta y devuelve los grupos.
(function () {
  function _norm(s) { return (s || '').toLowerCase(); }

  // "Clausura - Group B" → 'clausura' | ''
  function _torneoDeGrupo(nombre) {
    var m = _norm(nombre).match(/apertura|clausura/);
    return m ? m[0] : '';
  }

  // Partidos FT de liga.json de un equipo en ese torneo, cronológicos.
  function _ftDe(liga, teamId, torneo) {
    var id = String(teamId), out = [];
    (liga || []).forEach(function (m) {
      var st = m.status || {};
      if (!st.finished) return;
      if (torneo && _norm(m.round).indexOf(torneo) < 0) return;
      var esLocal = String((m.home || {}).id) === id;
      if (!esLocal && String((m.away || {}).id) !== id) return;
      if (m.home_score == null || m.away_score == null) return;
      out.push({
        utc: st.utcTime || '',
        gf: esLocal ? m.home_score : m.away_score,
        gc: esLocal ? m.away_score : m.home_score
      });
    });
    out.sort(function (a, b) { return a.utc < b.utc ? -1 : a.utc > b.utc ? 1 : 0; });
    return out;
  }

  function _aplicar(row, partidos) {
    var a = row.all || (row.all = {});
    a.goals = a.goals || { for: 0, against: 0 };
    var forma = '';
    partidos.forEach(function (p) {
      a.played = (a.played || 0) + 1;
      a.goals.for = (a.goals.for || 0) + p.gf;
      a.goals.against = (a.goals.against || 0) + p.gc;
      if (p.gf > p.gc) { a.win = (a.win || 0) + 1; row.points = (row.points || 0) + 3; forma += 'W'; }
      else if (p.gf === p.gc) { a.draw = (a.draw || 0) + 1; row.points = (row.points || 0) + 1; forma += 'D'; }
      else { a.lose = (a.lose || 0) + 1; forma += 'L'; }
    });
    row.goalsDiff = (a.goals.for || 0) - (a.goals.against || 0);
    // La forma se lee de izquierda (más viejo) a derecha, como la manda la API.
    if (forma) row.form = ((row.form || '') + forma).slice(-5);
  }

  // groups: standings de api-sports (array de grupos). liga: data/fixtures/liga.json.
  function sfCorregirGrupos(groups, liga) {
    if (!groups || !liga || !liga.length) return groups;
    (groups || []).forEach(function (g) {
      if (!g || !g.length) return;
      var torneo = _torneoDeGrupo(g[0] && g[0].group);
      var tocado = false;
      g.forEach(function (row) {
        var id = row.team && row.team.id;
        if (id == null) return;
        var ft = _ftDe(liga, id, torneo);
        var faltan = ft.length - ((row.all && row.all.played) || 0);
        if (faltan > 0) { _aplicar(row, ft.slice(-faltan)); tocado = true; }
      });
      if (!tocado) return;
      g.sort(function (a, b) {
        return (b.points || 0) - (a.points || 0) ||
               (b.goalsDiff || 0) - (a.goalsDiff || 0) ||
               (((b.all || {}).goals || {}).for || 0) - (((a.all || {}).goals || {}).for || 0);
      });
      g.forEach(function (row, i) { row.rank = i + 1; });
    });
    return groups;
  }

  // Carga liga.json y corrige; si no está disponible, devuelve los grupos tal cual.
  async function sfCorregirConLiga(groups) {
    try {
      var r = await fetch('data/fixtures/liga.json?t=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) return groups;
      return sfCorregirGrupos(groups, await r.json());
    } catch (e) { return groups; }
  }

  window.sfCorregirGrupos = sfCorregirGrupos;
  window.sfCorregirConLiga = sfCorregirConLiga;
})();
