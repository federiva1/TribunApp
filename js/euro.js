/* EUROTRIBUNAPP (prototipo): utilidades compartidas de euro.html, euro-liga.html y euro-club.html.
   Los datos salen de data/euro/ (scripts/fetch_euro.py, FotMob); escudos y logos se piden a
   images.fotmob.com (no se guardan en el repo). */
const EURO = {
  escudo: id => `https://images.fotmob.com/image_resources/logo/teamlogo/${id}.png`,
  logoLiga: id => `https://images.fotmob.com/image_resources/logo/leaguelogo/${id}.png`,
  esc: s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])),
  async json(path) {
    const r = await fetch(path + (path.includes('?') ? '&' : '?') + 't=' + Date.now());
    if (!r.ok) throw new Error(path + ' ' + r.status);
    return r.json();
  },
  // Hora argentina (UTC-3, sin horario de verano)
  ar(utc) {
    if (!utc) return null;
    const d = new Date(new Date(utc).getTime() - 3 * 3600e3);
    const dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
    const mes = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    const hh = String(d.getUTCHours()).padStart(2, '0'), mm = String(d.getUTCMinutes()).padStart(2, '0');
    return { dia: `${dias[d.getUTCDay()]} ${d.getUTCDate()} ${mes[d.getUTCMonth()]}`, hora: `${hh}:${mm}` };
  },
  // Leyenda de FotMob (en inglés) → castellano
  leyenda(t) {
    const s = (t || '').toLowerCase();
    if (s.includes('champions league')) return s.includes('qualification') ? 'Previa de Champions' : 'Champions League';
    if (s.includes('europa league')) return s.includes('qualification') ? 'Previa de Europa League' : 'Europa League';
    if (s.includes('conference')) return s.includes('qualification') ? 'Previa de Conference' : 'Conference League';
    if (s.includes('relegation') && s.includes('play')) return 'Promoción';
    if (s.includes('relegation')) return 'Descenso';
    return t;
  },
  // Fila de partido: con resultado si terminó, si no con día y hora
  partido(p, opts) {
    const o = opts || {};
    const t = EURO.ar(p.utcTime);
    const term = p.terminado && p.goles_local != null;
    const cls = lado => !term ? '' : (lado === 'l' ? p.goles_local > p.goles_visitante : p.goles_visitante > p.goles_local) ? 'gana' : 'pierde';
    const centro = term
      ? `<b class="res">${p.goles_local} - ${p.goles_visitante}</b>${t ? t.dia : ''}`
      : `<b>${t ? t.hora : '--:--'}</b>${t ? t.dia : 'A confirmar'}`;
    const lg = o.liga ? `<img class="lgm" src="${EURO.logoLiga(o.liga)}" alt="">` : '';
    return `<div class="mt">`
      + `<a class="tm ${cls('l')}" href="euro-club.html?id=${p.local.id}"><img src="${EURO.escudo(p.local.id)}" alt="" loading="lazy"><span>${EURO.esc(p.local.nombre)}</span></a>`
      + `<div class="c">${lg}${centro}</div>`
      + `<a class="tm r ${cls('v')}" href="euro-club.html?id=${p.visitante.id}"><span>${EURO.esc(p.visitante.nombre)}</span><img src="${EURO.escudo(p.visitante.id)}" alt="" loading="lazy"></a>`
      + `</div>`;
  },
};
