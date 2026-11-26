/* EUROTRIBUNAPP (prototipo): utilidades compartidas de euro.html, euro-liga.html (tabla),
   euro-fixture.html, euro-stats.html, euro-tribunapp.html y euro-club.html. Los datos salen de data/euro/ (scripts/fetch_euro.py,
   FotMob); escudos y logos: copias propias en escudos/euro/ (fetch_euro.py), con respaldo a images.fotmob.com.

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
  // Botones del header del modo Euro. `donde` = página actual ('home' | 'fixture' | 'tablas' | 'stats' | 'tribunapp' | 'club')
  header(donde, lid) {
    const acts = document.querySelector('#site-header .header-actions');
    if (!acts) return;
    const l = lid || EURO.liga();
    const ico = {
      euro: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5-4.8-4.6 6.6-.9z"/></svg>',
      fixture: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
      tablas: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
      stats: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
      tribunapp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
      arg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
    };
    const pill = (href, k, label, extra, tip) =>
      `<a class="header-pill${extra ? ' ' + extra : ''}${donde === k ? ' on' : ''}" href="${href}" title="${tip}" aria-label="${tip}">${ico[k] || ico.arg}<span class="header-pill-label">${label}</span></a>`;
    acts.innerHTML =
      pill('euro.html', 'euro', 'EURO', 'euro', 'Inicio de Eurotribunapp')
      + pill(`euro-fixture.html?l=${l}`, 'fixture', 'Fixture', '', 'Fixture de la competición')
      + pill(`euro-liga.html?l=${l}`, 'tablas', 'Tablas/Equipos', '', 'Tabla de posiciones y equipos')
      + pill(`euro-stats.html?l=${l}`, 'stats', 'Estadísticas', '', 'Estadísticas de la última fecha')
      + pill(`euro-tribunapp.html?l=${l}`, 'tribunapp', 'TribunApp', '', 'Lo que vota la gente')
      + pill('index.html', 'arg', 'Argentina', '', 'Volver a TribunApp Argentina');
  },
  // Fila de botones con las competiciones (cambia de liga sin salir de la página); `extra` = "&c=123" para conservar el club
  selector(activo, pagina, extra) {
    return EURO.LIGAS.map(l =>
      `<a class="chip-liga${l.id === Number(activo) ? ' on' : ''}" href="${pagina}?l=${l.id}${extra || ''}">`
      + `<img src="${EURO.logoLiga(l.id)}" alt=""><span>${EURO.esc(l.corto)}</span></a>`).join('');
  },
  // "Gianluigi Donnarumma" → "G. Donnarumma" (para listas angostas)
  jug(n) {
    const p = String(n || '').trim().split(/\s+/);
    return p.length < 2 ? p[0] || '' : p[0][0] + '. ' + p.slice(1).join(' ');
  },
  // Minuto de un gol: 90 + extra → "90+3'"
  min(m, extra) { return m == null ? '' : `${m}${extra ? '+' + extra : ''}'`; },
  // Color de la nota (escala de FotMob): 8+ verde fuerte … menos de 6 rojo
  notaClase(n) { return n == null ? '' : n >= 8 ? 't1' : n >= 7 ? 't2' : n >= 6.5 ? 't3' : n >= 6 ? 't4' : 't5'; },
  // "12" → "Fecha 12" ("Jornada 5" en la Champions); las eliminatorias, por su nombre
  ronda(r, lid) {
    const s = String(r == null ? '' : r);
    if (/^\d+$/.test(s)) return `${Number(lid) === 42 ? 'Jornada' : 'Fecha'} ${s}`;
    const ko = { '1/32': 'Dieciseisavos', '1/16': 'Playoff', 'playoff': 'Playoff', '1/8': 'Octavos', '1/4': 'Cuartos', '1/2': 'Semifinales', 'final': 'Final' };
    return ko[s.toLowerCase()] || s;
  },
  // Escudos y logos: copias propias en escudos/euro/ (scripts/fetch_euro.py); si alguno falta, se pide a FotMob (ver abajo)
  escudo: id => `escudos/euro/${id}.png`,
  logoLiga: id => `escudos/euro/liga-${id}.png`,
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

/* ---------- Votos de la gente (Supabase) y utilidades de las páginas con formación y puntajes ----------
   Los votos de Europa van a las MISMAS tablas que los de Argentina (formaciones y puntajes); el club se guarda
   como "euro-{id de FotMob}" y los jugadores por su id de FotMob. Requieren js/config.js (SUPABASE_URL / KEY). */
EURO.clubKey = id => 'euro-' + id;
EURO.diaAR = utc => utc ? new Date(new Date(utc).getTime() - 3 * 3600e3).toISOString().slice(0, 10) : '';   // día local argentino del partido
EURO.deviceId = function () {
  try {
    let d = localStorage.getItem('tribunapp_device_id');
    if (!d) { d = 'dev_' + Math.random().toString(36).substr(2, 12) + Date.now().toString(36); localStorage.setItem('tribunapp_device_id', d); }
    return d;
  } catch (e) { return 'dev_' + Math.random().toString(36).substr(2, 12); }
};
EURO.ls = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
};
EURO.sb = {
  async get(path) {
    const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, { headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` } });
    if (!r.ok) throw new Error('supabase ' + r.status);
    return r.json();
  },
  // Inserta un voto; con sesión va firmado con el usuario (js/cuenta.js). Devuelve el status (201 ok, 409 ya votó)
  async votar(tabla, cuerpo) {
    const f = window.TA_CUENTA && TA_CUENTA.firmaVoto ? await TA_CUENTA.firmaVoto()
      : { headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` }, extra: {} };
    const r = await fetch(`${SUPABASE_URL}/rest/v1/${tabla}`, {
      method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json', Prefer: 'return=minimal' }, f.headers),
      body: JSON.stringify(Object.assign({}, cuerpo, f.extra)),
    });
    return r.status;
  },
};
EURO.toast = function (msg) {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; document.body.appendChild(t); }
  t.textContent = msg; t.classList.add('on');
  clearTimeout(EURO._tt); EURO._tt = setTimeout(() => t.classList.remove('on'), 2600);
};
// "Rúben Dias" → "Dias"; "Kevin De Bruyne" → "De Bruyne" (para fichas con poco lugar)
EURO.apellido = n => { const p = String(n || '').trim().split(/\s+/); return p.length > 1 ? p.slice(1).join(' ') : p[0] || ''; };
// Ficha (círculo con el kit del club y el dorsal)
EURO.ficha = (clubId, color, num, px) =>
  `<span class="kk" style="width:${px}px;height:${px}px;background:${EURO.kitFondo(clubId, px, color)};font-size:${Math.round(px * 0.46)}px">${num != null && num !== '' ? num : ''}</span>`;

/* Escudo que falta en escudos/euro/ (por ejemplo un rival de copa): se reintenta una vez con el de FotMob */
document.addEventListener('error', function (e) {
  const i = e.target;
  if (!i || i.tagName !== 'IMG' || i.dataset.fb) return;
  const m = /escudos\/euro\/(liga-)?(\d+)\.png/.exec(i.getAttribute('src') || '');
  if (!m) return;
  i.dataset.fb = '1';
  i.src = `https://images.fotmob.com/image_resources/logo/${m[1] ? 'leaguelogo' : 'teamlogo'}/${m[2]}.png`;
}, true);

/* ---------- Equipos de la gente: mini cancha con las fichas del club ---------- */
EURO.PITCH_SVG = '<svg viewBox="0 0 100 122" preserveAspectRatio="none" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="0.7">'
  + '<rect x="3" y="3" width="94" height="116"/><line x1="3" y1="61" x2="97" y2="61"/><circle cx="50" cy="61" r="11"/>'
  + '<rect x="25" y="3" width="50" height="18"/><rect x="38" y="3" width="24" height="7"/><rect x="25" y="101" width="50" height="18"/><rect x="38" y="112" width="24" height="7"/></svg>';
EURO.miniCancha = function (jugadores, clubId, color, pie) {
  const fichas = (jugadores || []).map(j =>
    `<span class="mp" style="left:${j.x}%;top:${j.y}%">${EURO.ficha(clubId, color, j.num, 24)}</span>`).join('');
  return `<div class="mini"><div class="mini-c">${EURO.PITCH_SVG}${fichas}</div>${pie ? `<div class="mini-p">${pie}</div>` : ''}</div>`;
};
// "hace 3 h" / "hace 2 días" desde un timestamp de Supabase
EURO.hace = function (iso) {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  return m < 60 ? `hace ${m || 1} min` : m < 1440 ? `hace ${Math.round(m / 60)} h` : `hace ${Math.round(m / 1440)} d`;
};
