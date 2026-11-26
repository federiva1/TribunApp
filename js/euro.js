/* EUROTRIBUNAPP (prototipo): utilidades compartidas de euro.html, euro-liga.html (tabla),
   euro-fixture.html y euro-club.html. Los datos salen de data/euro/ (scripts/fetch_euro.py,
   FotMob); escudos y logos se piden a images.fotmob.com (no se guardan en el repo).

   En el modo Euro el header es otro (dorado, con Fixture y Tablas de la competición que se está
   mirando): EURO.header() lo arma. La competición sale de ?l= o, si no, de la última que se miró
   (localStorage); el logo y "Argentina" vuelven al home del fútbol argentino. */
const EURO = {
  // Competiciones, en el orden en que se muestran (ids de FotMob)
  LIGAS: [
    { id: 42, corto: 'Champions', nombre: 'Champions League' },
    { id: 47, corto: 'Premier', nombre: 'Premier League' },
    { id: 87, corto: 'LaLiga', nombre: 'LaLiga' },
    { id: 55, corto: 'Serie A', nombre: 'Serie A' },
    { id: 54, corto: 'Bundesliga', nombre: 'Bundesliga' },
    { id: 53, corto: 'Ligue 1', nombre: 'Ligue 1' },
  ],
  // Competición activa: ?l= → última mirada → Champions
  liga() {
    const ids = EURO.LIGAS.map(l => String(l.id));
    const q = (new URLSearchParams(location.search).get('l') || '').replace(/\D/g, '');
    let v = ids.includes(q) ? q : '';
    if (!v) { try { v = localStorage.getItem('euro_liga') || ''; } catch (e) {} }
    v = ids.includes(v) ? v : ids[0];
    try { localStorage.setItem('euro_liga', v); } catch (e) {}
    return Number(v);
  },
  recordar(id) { try { localStorage.setItem('euro_liga', String(id)); } catch (e) {} },
  // Botones del header del modo Euro. `donde` = página actual ('home' | 'fixture' | 'tablas' | 'club')
  header(donde, lid) {
    const acts = document.querySelector('#site-header .header-actions');
    if (!acts) return;
    const l = lid || EURO.liga();
    const ico = {
      euro: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5-4.8-4.6 6.6-.9z"/></svg>',
      fixture: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
      tablas: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
      arg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
    };
    const pill = (href, k, label, extra, tip) =>
      `<a class="header-pill${extra ? ' ' + extra : ''}${donde === k ? ' on' : ''}" href="${href}" title="${tip}" aria-label="${tip}">${ico[k] || ico.arg}<span class="header-pill-label">${label}</span></a>`;
    acts.innerHTML =
      pill('euro.html', 'euro', 'EURO', 'euro', 'Inicio de Eurotribunapp')
      + pill(`euro-fixture.html?l=${l}`, 'fixture', 'Fixture', '', 'Fixture de la competición')
      + pill(`euro-liga.html?l=${l}`, 'tablas', 'Tablas', '', 'Tabla de posiciones y equipos')
      + pill('index.html', 'arg', 'Argentina', '', 'Volver a TribunApp Argentina');
  },
  // Fila de botones con las competiciones (cambia de liga sin salir de la página)
  selector(activo, pagina) {
    return EURO.LIGAS.map(l =>
      `<a class="chip-liga${l.id === Number(activo) ? ' on' : ''}" href="${pagina}?l=${l.id}">`
      + `<img src="${EURO.logoLiga(l.id)}" alt=""><span>${EURO.esc(l.corto)}</span></a>`).join('');
  },
  // "12" → "Fecha 12" ("Jornada 5" en la Champions); las eliminatorias, por su nombre
  ronda(r, lid) {
    const s = String(r == null ? '' : r);
    if (/^\d+$/.test(s)) return `${Number(lid) === 42 ? 'Jornada' : 'Fecha'} ${s}`;
    const ko = { '1/32': 'Dieciseisavos', '1/16': 'Playoff', 'playoff': 'Playoff', '1/8': 'Octavos', '1/4': 'Cuartos', '1/2': 'Semifinales', 'final': 'Final' };
    return ko[s.toLowerCase()] || s;
  },
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
  // Fila de partido: con resultado si terminó, si no con día y hora.
  // opts.liga = logo de la competición en el centro y para armar los links al club; opts.sinDia = sin el día
  // (cuando los partidos ya vienen agrupados por día).
  partido(p, opts) {
    const o = opts || {};
    const t = EURO.ar(p.utcTime);
    const term = p.terminado && p.goles_local != null;
    const cls = lado => !term ? '' : (lado === 'l' ? p.goles_local > p.goles_visitante : p.goles_visitante > p.goles_local) ? 'gana' : 'pierde';
    const dia = t && !o.sinDia ? t.dia : '';
    const centro = term
      ? `<b class="res">${p.goles_local} - ${p.goles_visitante}</b>${dia}`
      : p.cancelado ? '<b>SUSP.</b>'
      : `<b>${t ? t.hora : '--:--'}</b>${t ? dia : 'A confirmar'}`;
    const lg = o.logo && o.liga ? `<img class="lgm" src="${EURO.logoLiga(o.liga)}" alt="">` : '';
    const ql = o.liga ? `&l=${o.liga}` : '';
    return `<div class="mt">`
      + `<a class="tm ${cls('l')}" href="euro-club.html?id=${p.local.id}${ql}"><img src="${EURO.escudo(p.local.id)}" alt="" loading="lazy"><span>${EURO.esc(p.local.nombre)}</span></a>`
      + `<div class="c">${lg}${centro}</div>`
      + `<a class="tm r ${cls('v')}" href="euro-club.html?id=${p.visitante.id}${ql}"><span>${EURO.esc(p.visitante.nombre)}</span><img src="${EURO.escudo(p.visitante.id)}" alt="" loading="lazy"></a>`
      + `</div>`;
  },
};
