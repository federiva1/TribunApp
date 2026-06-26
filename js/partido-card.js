/* ============================================================
   partido-card.js  —  Widget de "partido en vivo" para index.html
   ------------------------------------------------------------
   Replica el card de partido + ficha desplegable de fixture.html.
   Es autocontenido (IIFE → window.LiveMatch) para no colisionar
   con los globales de index.html (que tiene su propio NOMBRES_ES
   con nombres largos para las tablas de grupos).

   La lógica del card/ficha es un espejo de la de fixture.html:
   si se modifica una, conviene reflejarla en la otra.
   ============================================================ */
(function () {
'use strict';

// Nombres cortos (igual que fixture.html — los cards son angostos)
const NOMBRES_ES = {
  czechia:'Chequia', mexico:'México', southafrica:'Sudáfrica', southkorea:'Corea del Sur',
  bosniaandherzegovina:'Bosnia y Herz.', canada:'Canadá', qatar:'Qatar', switzerland:'Suiza',
  brazil:'Brasil', haiti:'Haití', morocco:'Marruecos', scotland:'Escocia',
  australia:'Australia', paraguay:'Paraguay', turkiye:'Turquía', usa:'EE.UU.',
  curacao:'Curazao', ecuador:'Ecuador', germany:'Alemania', ivorycoast:'Costa de Marfil',
  japan:'Japón', netherlands:'Países Bajos', sweden:'Suecia', tunisia:'Túnez',
  belgium:'Bélgica', egypt:'Egipto', iran:'Irán', newzealand:'Nueva Zelanda',
  capeverde:'Cabo Verde', saudiarabia:'Arabia Saudita', spain:'España', uruguay:'Uruguay',
  france:'Francia', iraq:'Irak', norway:'Noruega', senegal:'Senegal',
  algeria:'Argelia', argentina:'Argentina', austria:'Austria', jordan:'Jordania',
  colombia:'Colombia', drcongo:'Rep. D. Congo', portugal:'Portugal', uzbekistan:'Uzbekistán',
  croatia:'Croacia', england:'Inglaterra', ghana:'Ghana', panama:'Panamá',
};

let slugPorId = {};
let grupoPorSlug = {};

const DIAS_ES  = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
const MESES_ES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dic'];

const LIVE_SHORT = ['1H','HT','2H','ET','BT','P','SUSP'];

// ── Helpers ─────────────────────────────────────────────────────────────────
function slugDeNombre(nombre) {
  return (nombre || '').toLowerCase()
    .normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .replace(/\s+/g, '').replace(/-/g, '').replace(/'/g, '');
}

function formatearHora(utcStr) {
  const d = new Date(utcStr);
  d.setHours(d.getHours() - 3);
  const h = String(d.getUTCHours()).padStart(2, '0');
  const m = String(d.getUTCMinutes()).padStart(2, '0');
  return `${h}:${m}`;
}

// Escapa HTML — los nombres de jugadores/equipos vienen de FotMob/api-sports
// (fuentes externas no confiables) y se interpolan en innerHTML.
function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

// Siempre vía el proxy serverless — la API key vive solo en el servidor.
function getApiBase() { return '/api/apisports'; }
function getApiHeaders() { return {}; }

// ── Card de partido ─────────────────────────────────────────────────────────
function crearCardPartido(p) {
  const tieneStats = p.stats_id && p.status.finished;
  const tieneFicha = !!(p.api_id || p.stats_id);
  const card = document.createElement('div');
  const { started, finished } = p.status;
  const enCurso = started && !finished;

  let claseCard = 'partido-card';
  if (enCurso) claseCard += ' en-curso';
  if (finished) claseCard += ' terminado';
  card.className = claseCard;
  if (p.api_id) card.dataset.apiId = p.api_id;

  const slugHome = p.home.slug || slugPorId[p.home.id] || slugDeNombre(p.home.name);
  const slugAway = p.away.slug || slugPorId[p.away.id] || slugDeNombre(p.away.name);
  const nomHome = escapeHtml(NOMBRES_ES[slugHome] || p.home.name);
  const nomAway = escapeHtml(NOMBRES_ES[slugAway] || p.away.name);

  const golesHome = p.home.score ?? p.home_score ?? null;
  const golesAway = p.away.score ?? p.away_score ?? null;
  const hayMarcador = golesHome !== null && golesAway !== null;

  let claseNomHome = 'partido-nombre';
  let claseNomAway = 'partido-nombre';
  if (finished && hayMarcador) {
    if (golesHome > golesAway) { claseNomHome += ' ganador'; claseNomAway += ' perdedor'; }
    else if (golesAway > golesHome) { claseNomAway += ' ganador'; claseNomHome += ' perdedor'; }
  }

  let metaLabel = '';
  const grupoLetra = grupoPorSlug[p.home?.slug] || grupoPorSlug[p.away?.slug] || null;
  if (p.group) metaLabel = grupoLetra ? `Grupo ${grupoLetra}` : 'Fase de Grupos';
  else if (p.round === '1/16') metaLabel = 'Octavos de Final';
  else if (p.round === '1/8')  metaLabel = 'Cuartos de Final';
  else if (p.round === '1/4')  metaLabel = 'Semifinal';
  else if (p.round === '1/2')  metaLabel = 'Final';
  else if (p.round === 'bronze') metaLabel = 'Tercer Puesto';
  else if (p.round === 'final')  metaLabel = 'GRAN FINAL';

  let horaHTML = '';
  if (enCurso) {
    horaHTML = `<span class="partido-hora en-curso">EN VIVO</span>`;
  } else if (finished) {
    horaHTML = `<span class="partido-hora">FIN</span>`;
  } else {
    horaHTML = `<span class="partido-hora">${formatearHora(p.status.utcTime)} hs</span>`;
  }

  let marcadorHTML = '';
  if (hayMarcador) {
    marcadorHTML = `
      <div class="marcador">
        <span class="marcador-gol">${golesHome}</span>
        <span class="marcador-sep">-</span>
        <span class="marcador-gol">${golesAway}</span>
      </div>`;
  } else {
    marcadorHTML = `<div class="marcador"><span class="marcador-vs">VS</span></div>`;
  }

  const metaRonda = p.round === 'amistoso' ? 'Amistoso' : metaLabel;

  let btnsHTML = '';
  if (tieneFicha || tieneStats) {
    btnsHTML = '<div class="card-btns">';
    if (tieneFicha) btnsHTML += `<button class="card-btn card-btn-ficha" data-api="${p.api_id}" data-home="${nomHome}" data-away="${nomAway}" data-hslug="${slugHome}" data-aslug="${slugAway}">📋 Ver ficha</button>`;
    if (tieneStats) btnsHTML += `<a class="card-btn card-btn-stats" href="estadisticas.html?p=${p.stats_id}">📊 Ver estadísticas →</a>`;
    btnsHTML += '</div>';
  }

  card.innerHTML = `
    <div class="partido-meta">
      <span class="partido-grupo">${metaRonda}</span>
      ${horaHTML}
    </div>
    <div class="partido-fila">
      <div class="equipo-home">
        <span class="${claseNomHome}">${nomHome}</span>
        <a href="equipo.html?c=${slugHome}" onclick="event.stopPropagation()">
          <img class="partido-flag" src="escudos/${slugHome}.png" alt="${nomHome}" onerror="this.style.opacity='0.1'">
        </a>
      </div>
      ${marcadorHTML}
      <div class="equipo-away">
        <a href="equipo.html?c=${slugAway}" onclick="event.stopPropagation()">
          <img class="partido-flag" src="escudos/${slugAway}.png" alt="${nomAway}" onerror="this.style.opacity='0.1'">
        </a>
        <span class="${claseNomAway}">${nomAway}</span>
      </div>
    </div>
    ${btnsHTML}
    <div class="ficha-panel" id="ficha-${p.api_id || ''}"></div>
  `;

  if (tieneFicha) {
    const btn = card.querySelector('.card-btn-ficha');
    btn.addEventListener('click', () => toggleFicha(p, btn, card));
  }

  return card;
}

// ── Ficha ───────────────────────────────────────────────────────────────────
const _fichaCache = {};
let _liveTimer = null;
let _openFichaState = { p: null, card: null };

async function loadFichaContent(p, card) {
  const panel = card.querySelector('.ficha-panel');
  const cacheKey = p.stats_id || p.api_id;
  const enCursoAhora = p.status?.started && !p.status?.finished;

  if (_fichaCache[cacheKey] && !enCursoAhora) {
    applyFichaCtx(panel, _fichaCache[cacheKey]);
    return;
  }

  if (!panel.innerHTML || panel.innerHTML.includes('ficha-loading')) {
    panel.innerHTML = '<div class="ficha-loading">CARGANDO...</div>';
  }

  try {
    if (p.stats_id) {
      const res = await fetch(`data/partidos/${p.stats_id}.json?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        const slugLocal = data.partido.local;
        const slugVisit = data.partido.visitante;
        const [rL, rV] = await Promise.allSettled([
          fetch(`data/planteles/${slugLocal}.json`),
          fetch(`data/planteles/${slugVisit}.json`),
        ]);
        const plantelLocal = rL.status === 'fulfilled' && rL.value.ok ? await rL.value.json() : null;
        const plantelVisit = rV.status === 'fulfilled' && rV.value.ok ? await rV.value.json() : null;
        const ctx = renderFichaFromJson(data, plantelLocal, plantelVisit);
        if (!enCursoAhora) _fichaCache[cacheKey] = ctx;
        applyFichaCtx(panel, ctx);
        return;
      }
    }
    if (!p.api_id) {
      panel.innerHTML = '<div class="ficha-loading">No disponible</div>';
      return;
    }
    const base = getApiBase();
    const headers = getApiHeaders();
    const slugHome = p.home?.slug || slugPorId[p.home?.id] || slugDeNombre(p.home?.name || '');
    const slugAway = p.away?.slug || slugPorId[p.away?.id] || slugDeNombre(p.away?.name || '');
    const [resLinea, resEv, resPlay, rPL, rPV] = await Promise.allSettled([
      fetch(`${base}/fixtures/lineups?fixture=${p.api_id}`, { headers }),
      fetch(`${base}/fixtures/events?fixture=${p.api_id}`, { headers }),
      fetch(`${base}/fixtures/players?fixture=${p.api_id}`, { headers }),
      fetch(`data/planteles/${slugHome}.json`),
      fetch(`data/planteles/${slugAway}.json`),
    ]);
    const lineups = resLinea.status === 'fulfilled' && resLinea.value.ok ? (await resLinea.value.json()).response || [] : [];
    const events  = resEv.status  === 'fulfilled' && resEv.value.ok  ? (await resEv.value.json()).response  || [] : [];
    const playerStats = resPlay.status === 'fulfilled' && resPlay.value.ok ? (await resPlay.value.json()).response || [] : [];
    const plantelLocal = rPL.status === 'fulfilled' && rPL.value.ok ? await rPL.value.json() : null;
    const plantelVisit = rPV.status === 'fulfilled' && rPV.value.ok ? await rPV.value.json() : null;
    const ctx = renderFichaEnhanced(lineups, events, p, plantelLocal, plantelVisit, playerStats);
    if (!enCursoAhora) _fichaCache[cacheKey] = ctx;
    applyFichaCtx(panel, ctx);
  } catch(e) {
    panel.innerHTML = `<div class="ficha-loading">No disponible</div>`;
  }
}

async function toggleFicha(p, btn, card) {
  const panel = card.querySelector('.ficha-panel');
  const abierto = panel.classList.contains('abierto');
  if (abierto) {
    panel.classList.remove('abierto');
    btn.textContent = '📋 Ver ficha';
    _openFichaState = { p: null, card: null };
    panel._openDetailPid = null;
    return;
  }
  panel.classList.add('abierto');
  btn.textContent = '📋 Ocultar ficha';
  _openFichaState = { p, card };
  await loadFichaContent(p, card);
}

function renderFichaFromJson(data, plantelLocal, plantelVisit) {
  const p = data.partido;
  const jugadores = data.jugadores || {};

  const normN = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const firstLast = s => { const w = normN(s).split(/\s+/).filter(Boolean); return w.length >= 2 ? w[0]+' '+w[w.length-1] : normN(s); };
  const tokKey = s => '' + normN(s).replace(/-/g,' ').split(/\s+/).filter(Boolean).sort().join(' ');
  const tokSet = s => new Set(normN(s).replace(/-/g,' ').split(/\s+/).filter(Boolean));
  const lastWord = s => { const w = normN(s).replace(/\./g,'').split(/\s+/).filter(Boolean); return w[w.length-1] || ''; };

  function buildFidIndex(plantel) {
    const idx = { _list: (plantel?.jugadores || []) };
    for (const pl of idx._list) {
      idx['n:' + normN(pl.nombre)] = pl;
      idx['f:' + firstLast(pl.nombre)] = pl;
      idx['t:' + tokKey(pl.nombre)] = pl;
    }
    return idx;
  }

  const fidLocal = buildFidIndex(plantelLocal);
  const fidVisit = buildFidIndex(plantelVisit);

  function getPlantelEntry(nombre, idx) {
    const directo = idx['n:' + normN(nombre)] || idx['f:' + firstLast(nombre)] || idx['t:' + tokKey(nombre)];
    if (directo) return directo;
    const lw = lastWord(nombre);
    const byLast = (idx._list || []).filter(pl => lastWord(pl.nombre) === lw);
    if (byLast.length === 1) return byLast[0];
    const mine = tokSet(nombre);
    const scored = (idx._list || []).map(pl => {
      const o = tokSet(pl.nombre); let n = 0; mine.forEach(t => { if (o.has(t)) n++; }); return { pl, n };
    }).sort((a, b) => b.n - a.n);
    if (scored.length && scored[0].n >= 2 && (scored.length === 1 || scored[1].n < scored[0].n)) return scored[0].pl;
    return null;
  }

  const players = {};

  function eventosIconos(j) {
    const iconos = [];
    for (let i = 0; i < (j.goles || 0); i++) iconos.push('<span class="ev-icon" title="Gol">⚽</span>');
    for (let i = 0; i < (j.asist || 0); i++) iconos.push('<span class="ev-icon" title="Asistencia">🅰️</span>');
    if (j.amarilla) iconos.push('<span class="ev-icon" title="Amarilla">🟨</span>');
    if (j.roja)     iconos.push('<span class="ev-icon" title="Roja">🟥</span>');
    return iconos.join('');
  }

  function filaJugador(j, fidIdx, teamName, movHTML) {
    const pe = getPlantelEntry(j.nombre, fidIdx);
    const fid = pe?.fid || null;
    const num = j.num || pe?.numero || '';
    const foto = fid ? `fotos/${fid}.png` : (j.id ? `https://media.api-sports.io/football/players/${j.id}.png` : '');
    players[j.id] = { j: { ...j, num }, teamName, fid, foto };
    return `
      <div class="ficha-jugador clickable" data-pid="${j.id}">
        ${foto ? `<img class="ficha-jugador-foto" src="${foto}" alt="" onerror="this.style.display='none'">` : '<span class="ficha-jugador-foto"></span>'}
        <span class="ficha-jugador-num">${num}</span>
        <div class="ficha-jugador-info">
          <div class="ficha-jugador-nombre">${escapeHtml(j.nombre)}</div>
        </div>
        <div class="ficha-jugador-eventos">${movHTML || ''}${eventosIconos(j)}</div>
      </div>`;
  }

  function renderEquipoJson(slug, fidIdx) {
    const jgs = jugadores[slug] || [];
    const titulares = jgs.filter(j => j.tipo === 'titular');
    const suplentes = jgs.filter(j => j.tipo === 'suplente' && j.min > 0);
    const nombre = NOMBRES_ES[slug] || slug;

    let html = `<div class="ficha-equipo-titulo">${escapeHtml(nombre)}</div>`;

    for (const j of titulares) {
      const movHTML = (j.min != null && j.min < 90)
        ? `<span class="ficha-mov ficha-mov-out" title="Salió">↓ ${j.min}'</span> ` : '';
      html += filaJugador(j, fidIdx, nombre, movHTML);
    }

    if (suplentes.length) {
      html += `<div class="ficha-subs"><div class="ficha-subs-titulo">Suplentes</div>`;
      for (const s of suplentes) {
        const minEntro = s.min != null ? (90 - s.min) : null;
        const movHTML = minEntro != null
          ? `<span class="ficha-mov ficha-mov-in" title="Ingresó">↑ ${minEntro}'</span> ` : '';
        html += filaJugador(s, fidIdx, nombre, movHTML);
      }
      html += '</div>';
    }

    return html;
  }

  const col1 = renderEquipoJson(p.local, fidLocal);
  const col2 = renderEquipoJson(p.visitante, fidVisit);

  let golesHTML = '';
  const gd = p.goles_detalle;
  if (gd && (gd.local?.length || gd.visitante?.length)) {
    const ultimaPalabra = s => normN(s).split(/\s+/).filter(Boolean).slice(-1)[0] || '';
    const renderGolesCol = (arr, slug) => {
      const jgsDelEquipo = jugadores[slug] || [];
      return (arr || []).map(g => {
        const apellido = ultimaPalabra(g.jugador);
        const match = jgsDelEquipo.find(j => ultimaPalabra(j.nombre) === apellido);
        const esSuplente = match?.tipo === 'suplente';
        const subIcon = esSuplente ? '<span class="ficha-gol-suplente">↑</span> ' : '';
        const asistHTML = (esSuplente && g.asist) ? ` <span class="ficha-gol-asist">(${escapeHtml(g.asist)})</span>` : '';
        return `<div class="ficha-gol-fila"><span class="ficha-gol-min">${g.min}'</span> <span class="ficha-gol-jugador">⚽ ${subIcon}${escapeHtml(g.jugador)}${asistHTML}</span></div>`;
      }).join('');
    };
    golesHTML = `<div class="ficha-goles"><div>${renderGolesCol(gd.local, p.local)}</div><div>${renderGolesCol(gd.visitante, p.visitante)}</div></div>`;
  }

  const lineupHTML = `${golesHTML}<div class="ficha-cols"><div>${col1}</div><div>${col2}</div></div>`;
  return { lineupHTML, players };
}

// ── Detalle de jugador ──────────────────────────────────────────────────────
const LBL_TOP = {tiros_totales:'Tiros totales',disparos_puerta:'A puerta',oport_creadas:'Oport. creadas',grandes_oport:'Gran. oport.',acc_defensivas:'Acc. defensivas',pases_precisos:'Pases precisos'};
const LBL_ATQ = {toques:'Toques',toques_area:'Toques área rival',regates:'Regates',pases_ultimo_tercio:'Pases últ. tercio',tiros_largos:'Tiros largos',perdida_balon:'Pérdidas'};
const LBL_DEF = {acc_defensivas:'Acc. defensivas',entradas:'Entradas',interceptaciones:'Interceptaciones',recuperaciones:'Recuperaciones',despejes:'Despejes',bloqueos:'Bloqueos',regateado:'Regateado'};
const LBL_DUE = {ganados:'Duelos ganados',perdidos:'Duelos perdidos',terrestres:'Terrestres',aereos:'Aéreos',faltas:'Faltas cometidas',faltas_recibidas:'Faltas recibidas'};

function _fdGrid(obj, labels) {
  const rows = Object.entries(labels).map(([k, l]) => {
    const raw = obj[k];
    const isNull = raw === null || raw === undefined;
    return `<div class="fd-row"><span class="fd-row-label">${l}</span><span class="fd-row-val${isNull ? ' null' : ''}">${isNull ? '—' : raw}</span></div>`;
  });
  const mid = Math.ceil(rows.length / 2);
  return `<div class="fd-grid"><div>${rows.slice(0, mid).join('')}</div><div>${rows.slice(mid).join('')}</div></div>`;
}

function _fdSec(titulo, gridHTML) {
  return `<div class="fd-sec"><div class="fd-sec-tit">${titulo}</div>${gridHTML}</div>`;
}

function _fdGridFromRows(rows) {
  const html = rows.map(r => `<div class="fd-row"><span class="fd-row-label">${r.label}</span><span class="fd-row-val">${r.val}</span></div>`);
  const mid = Math.ceil(html.length / 2);
  return `<div class="fd-grid"><div>${html.slice(0, mid).join('')}</div><div>${html.slice(mid).join('')}</div></div>`;
}

function renderFichaDetalle(entry) {
  const { j, teamName, fid } = entry;
  const foto = entry.foto || (fid ? `fotos/${fid}.png` : (j.id ? `https://media.api-sports.io/football/players/${j.id}.png` : ''));
  const fotoTag = foto
    ? `<img class="fd-foto" src="${foto}" alt="" onerror="this.style.visibility='hidden'">`
    : `<span class="fd-foto"></span>`;
  const tipoLabel = j.tipo === 'suplente' ? 'Suplente' : (j.tipo === 'dt' ? 'DT' : 'Titular');

  const badges = [];
  if (j.min != null) badges.push(`<span class="fd-badge">${j.min}' jugados</span>`);
  if (j.goles)    badges.push(`<span class="fd-badge">⚽ ${j.goles}</span>`);
  if (j.asist)    badges.push(`<span class="fd-badge">🅰️ ${j.asist}</span>`);
  if (j.amarilla) badges.push(`<span class="fd-badge">🟨</span>`);
  if (j.roja)     badges.push(`<span class="fd-badge">🟥</span>`);

  const secs = [];
  if (j.portero && j.portero_stats) {
    const ps = j.portero_stats;
    const box = (v, l) => `<div class="fd-pbox"><div class="fd-pval">${v}</div><div class="fd-plabel">${l}</div></div>`;
    const items = [
      ps.paradas != null ? box(ps.paradas, 'Paradas') : '',
      ps.goles_contra != null ? box(ps.goles_contra, 'Goles enc.') : '',
      ps.goles_evitados != null ? box((ps.goles_evitados >= 0 ? '+' : '') + ps.goles_evitados, 'Evitados') : '',
    ].filter(Boolean);
    if (items.length) secs.push(`<div class="fd-sec"><div class="fd-sec-tit">Arquero</div><div class="fd-portero">${items.join('')}</div></div>`);
  }
  if (j.top)     secs.push(_fdSec('Top',     _fdGrid(j.top, LBL_TOP)));
  if (j.ataque)  secs.push(_fdSec('Ataque',  _fdGrid(j.ataque, LBL_ATQ)));
  if (j.defensa) secs.push(_fdSec('Defensa', _fdGrid(j.defensa, LBL_DEF)));
  if (j.duelos)  secs.push(_fdSec('Duelos',  _fdGrid(j.duelos, LBL_DUE)));
  if (!secs.length && j._live && j._live.length) secs.push(_fdSec('Estadísticas', _fdGridFromRows(j._live)));

  const body = secs.length
    ? secs.join('')
    : `<div class="fd-empty">Las estadísticas se cargan a medida que avanza el partido.</div>`;

  return `
    <div class="ficha-detalle">
      <div class="fd-header">
        ${fotoTag}
        <div class="fd-info">
          <div class="fd-nombre">${(j.num || j.numero) ? `<span class="fd-num">${escapeHtml(j.num || j.numero)}</span>` : ''}${escapeHtml(j.nombre)}</div>
          <div class="fd-meta">${escapeHtml(teamName)} · ${tipoLabel}</div>
          <div class="fd-badges">${badges.join('')}</div>
        </div>
        <button class="fd-close" data-ficha-close aria-label="Cerrar">✕</button>
      </div>
      ${body}
    </div>`;
}

function bindFichaPanel(panel) {
  if (panel._fichaBound) return;
  panel._fichaBound = true;
  panel.addEventListener('click', (e) => {
    const ctx = panel._fichaCtx;
    if (!ctx) return;
    if (e.target.closest('[data-ficha-close]')) {
      panel._openDetailPid = null;
      panel.innerHTML = ctx.lineupHTML;
      return;
    }
    const row = e.target.closest('[data-pid]');
    if (row) {
      const pid = row.getAttribute('data-pid');
      const entry = ctx.players[pid];
      if (entry) { panel._openDetailPid = pid; panel.innerHTML = renderFichaDetalle(entry); }
    }
  });
}

function applyFichaCtx(panel, ctx) {
  panel._fichaCtx = ctx;
  const pid = panel._openDetailPid;
  if (pid && ctx.players && ctx.players[pid]) {
    panel.innerHTML = renderFichaDetalle(ctx.players[pid]);
  } else {
    panel.innerHTML = ctx.lineupHTML;
  }
  bindFichaPanel(panel);
}

function _liveStatsRows(st) {
  if (!st) return [];
  const rows = [];
  const add = (label, val, sfx = '') => { if (val !== null && val !== undefined && val !== '') rows.push({ label, val: '' + val + sfx }); };
  const g = st.games || {}, sh = st.shots || {}, go = st.goals || {}, pa = st.passes || {},
        ta = st.tackles || {}, du = st.duels || {}, dr = st.dribbles || {}, fo = st.fouls || {};
  add('Tiros', sh.total);
  add('Tiros al arco', sh.on);
  add('Pases', pa.total);
  add('Precisión pases', pa.accuracy, '%');
  add('Pases clave', pa.key);
  add('Entradas', ta.total);
  add('Intercepciones', ta.interceptions);
  add('Bloqueos', ta.blocks);
  add('Duelos ganados', du.won);
  add('Duelos totales', du.total);
  add('Regates', (dr.success != null && dr.attempts != null) ? `${dr.success}/${dr.attempts}` : dr.success);
  add('Faltas cometidas', fo.committed);
  add('Faltas recibidas', fo.drawn);
  if (g.position === 'G' || go.saves != null) {
    add('Atajadas', go.saves);
    add('Goles recibidos', go.conceded);
  }
  return rows;
}

function renderFichaEnhanced(lineups, events, p, plantelLocal, plantelVisit, playerStats) {
  if (!lineups.length) return { lineupHTML: '<div class="ficha-loading">Sin datos de alineación</div>', players: {} };

  const players = {};

  const statsById = {};
  for (const team of (playerStats || [])) {
    for (const pj of (team.players || [])) {
      const pid = pj.player?.id;
      if (pid) statsById[pid] = (pj.statistics || [])[0] || null;
    }
  }

  const normN = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const firstLast = s => { const w = normN(s).split(/\s+/).filter(Boolean); return w.length >= 2 ? w[0]+' '+w[w.length-1] : normN(s); };
  const lastWord = s => { const w = normN(s).replace(/\./g, '').split(/\s+/).filter(Boolean); return w[w.length - 1] || ''; };

  function buildFidIndex(plantel) {
    return { _list: (plantel?.jugadores || []) };
  }

  function getEntry(name, idx) {
    const list = idx._list || [];
    const nn = normN(name), fl = firstLast(name);
    let m = list.find(pl => normN(pl.nombre) === nn) || list.find(pl => firstLast(pl.nombre) === fl);
    if (m) return m;
    const lw = lastWord(name);
    const byLast = list.filter(pl => lastWord(pl.nombre) === lw);
    if (byLast.length === 1) return byLast[0];
    const mine = new Set(normN(name).replace(/-/g, ' ').split(/\s+/).filter(Boolean));
    const scored = list.map(pl => { const o = new Set(normN(pl.nombre).replace(/-/g, ' ').split(/\s+/).filter(Boolean)); let n = 0; mine.forEach(t => { if (o.has(t)) n++; }); return { pl, n }; }).sort((a, b) => b.n - a.n);
    if (scored.length && scored[0].n >= 2 && (scored.length === 1 || scored[1].n < scored[0].n)) return scored[0].pl;
    return null;
  }

  const fidLocal = buildFidIndex(plantelLocal);
  const fidAway  = buildFidIndex(plantelVisit);

  const evByPlayer = {};
  for (const ev of events) {
    const pid = ev.player?.id;
    if (!pid) continue;
    if (!evByPlayer[pid]) evByPlayer[pid] = [];
    evByPlayer[pid].push(ev);
  }
  const subsByTeam = {};
  for (const ev of events) {
    if (ev.type !== 'subst') continue;
    const tid = ev.team?.id;
    if (!subsByTeam[tid]) subsByTeam[tid] = [];
    subsByTeam[tid].push(ev);
  }

  function iconosJugador(pid) {
    const evs = evByPlayer[pid] || [];
    return evs.map(ev => {
      if (ev.type === 'Goal') return ev.detail === 'Own Goal' ? '<span class="ev-icon" title="Gol en contra">⚽🔴</span>' : '<span class="ev-icon" title="Gol">⚽</span>';
      if (ev.type === 'Card') return ev.detail === 'Yellow Card' ? '<span class="ev-icon" title="Amarilla">🟨</span>' : '<span class="ev-icon" title="Roja">🟥</span>';
      if (ev.type === 'Assist') return '<span class="ev-icon" title="Asistencia">🅰️</span>';
      return '';
    }).join('');
  }

  function infoBasica(pid) {
    const evs = evByPlayer[pid] || [];
    let goles = 0, asist = 0, amarilla = false, roja = false;
    for (const ev of evs) {
      if (ev.type === 'Goal' && ev.detail !== 'Own Goal') goles++;
      else if (ev.type === 'Assist') asist++;
      else if (ev.type === 'Card') { if ((ev.detail || '').includes('Red')) roja = true; else amarilla = true; }
    }
    return { goles, asist, amarilla, roja };
  }

  function renderEquipo(lineup, fidIdx) {
    const tid = lineup.team?.id;
    const teamName = lineup.team?.name || '';
    const titulares = lineup.startXI || [];
    const subs = subsByTeam[tid] || [];

    const outMin = {};
    const subsIn = [];
    for (const s of subs) {
      if (s.player?.id) outMin[s.player.id] = s.time?.elapsed ?? null;
      if (s.assist?.id) subsIn.push({ id: s.assist.id, name: s.assist.name || '', min: s.time?.elapsed ?? null });
    }

    function fila(pid, name, number, fid, capClass, movHTML, tipo) {
      const st = statsById[pid];
      const info = infoBasica(pid);
      const fotoSrc = fid ? `fotos/${fid}.png` : `https://media.api-sports.io/football/players/${pid}.png`;
      players[pid] = { j: { nombre: name, num: number || '', id: pid, tipo, min: st?.games?.minutes ?? null, ...info, _live: _liveStatsRows(st) }, teamName, fid };
      return `
        <div class="ficha-jugador clickable" data-pid="${pid}">
          <img class="ficha-jugador-foto" src="${fotoSrc}" alt="" onerror="this.src='data:image/svg+xml,<svg xmlns=\\'http://www.w3.org/2000/svg\\'/>'" >
          <span class="ficha-jugador-num">${number || ''}</span>
          <div class="ficha-jugador-info">
            <div class="ficha-jugador-nombre${capClass}">${escapeHtml(name)}</div>
          </div>
          <div class="ficha-jugador-eventos">${movHTML || ''}${iconosJugador(pid)}</div>
        </div>`;
    }

    let html = `<div class="ficha-equipo-titulo">${escapeHtml(teamName)}</div>`;

    for (const j of titulares) {
      const pl = j.player;
      const entry = getEntry(pl.name || '', fidIdx);
      const fid = entry?.fid || null;
      const number = pl.number || entry?.numero || '';
      const cap = pl.captain ? ' capitan' : '';
      const mv = outMin[pl.id] != null ? `<span class="ficha-mov ficha-mov-out" title="Salió">↓ ${outMin[pl.id]}'</span> ` : '';
      html += fila(pl.id, pl.name || '', number, fid, cap, mv, 'titular');
    }

    if (subsIn.length) {
      html += `<div class="ficha-subs"><div class="ficha-subs-titulo">Suplentes</div>`;
      for (const s of subsIn) {
        const entry = getEntry(s.name, fidIdx);
        const fid = entry?.fid || null;
        const number = entry?.numero || '';
        const mv = s.min != null ? `<span class="ficha-mov ficha-mov-in" title="Ingresó">↑ ${s.min}'</span> ` : '';
        html += fila(s.id, s.name, number, fid, '', mv, 'suplente');
      }
      html += '</div>';
    }

    return html;
  }

  const col1 = lineups[0] ? renderEquipo(lineups[0], fidLocal) : '';
  const col2 = lineups[1] ? renderEquipo(lineups[1], fidAway)  : '';
  return { lineupHTML: `<div class="ficha-cols"><div>${col1}</div><div>${col2}</div></div>`, players };
}

// ── Live polling (espejo de fixture.html, adaptado al widget) ────────────────
function startLivePolling(liveCards, contEl) {
  if (_liveTimer) clearInterval(_liveTimer);

  async function tick() {
    const base = getApiBase();
    const headers = getApiHeaders();

    const activos = liveCards.filter(({ p }) => !p.status?.finished);

    for (const { p, card } of activos) {
      try {
        const res = await fetch(`${base}/fixtures?id=${p.api_id}`, { headers });
        if (!res.ok) continue;
        const data = await res.json();
        const fixture = data.response?.[0];
        if (!fixture) continue;

        const short    = fixture.fixture?.status?.short;
        const elapsed  = fixture.fixture?.status?.elapsed;
        const golesH   = fixture.goals?.home ?? null;
        const golesA   = fixture.goals?.away ?? null;
        const finished = ['FT','AET','PEN'].includes(short);

        p.status.short    = short;
        p.status.finished = finished;
        p.status.started  = true;
        if (finished) { p.home_score = golesH; p.away_score = golesA; }

        const marcadorEl = card.querySelector('.marcador');
        if (marcadorEl && golesH !== null && golesA !== null) {
          marcadorEl.innerHTML = `
            <span class="marcador-gol">${golesH}</span>
            <span class="marcador-sep">-</span>
            <span class="marcador-gol">${golesA}</span>`;
        }

        const horaEl = card.querySelector('.partido-hora');
        if (horaEl) {
          if (finished) {
            horaEl.className = 'partido-hora';
            horaEl.textContent = 'FIN';
            card.classList.remove('en-curso');
            card.classList.add('terminado');
          } else if (LIVE_SHORT.includes(short)) {
            horaEl.className = 'partido-hora en-curso';
            horaEl.textContent = elapsed ? `${elapsed}'` : 'EN VIVO';
          }
        }

        if (finished && golesH !== null && golesA !== null) {
          const nomEls = card.querySelectorAll('.partido-nombre');
          if (nomEls.length === 2) {
            nomEls[0].classList.remove('ganador', 'perdedor');
            nomEls[1].classList.remove('ganador', 'perdedor');
            if (golesH > golesA) { nomEls[0].classList.add('ganador'); nomEls[1].classList.add('perdedor'); }
            else if (golesA > golesH) { nomEls[1].classList.add('ganador'); nomEls[0].classList.add('perdedor'); }
          }
        }

        if (!finished && _openFichaState.p === p && _openFichaState.card === card) {
          await loadFichaContent(p, card);
        }
      } catch(e) { /* ignorar error individual */ }
    }

    // Si ya no queda ningún partido en juego, ocultar el bloque y frenar el
    // polling en el mismo tick en que se detecta el FT (sin esperar 60s más).
    if (liveCards.every(({ p }) => p.status?.finished)) {
      clearInterval(_liveTimer);
      _liveTimer = null;
      if (contEl) contEl.style.display = 'none';
    }
  }

  tick();
  _liveTimer = setInterval(tick, 60000);
}

// ── API pública ─────────────────────────────────────────────────────────────
async function init() {
  const cont = document.getElementById('live-match');
  if (!cont) return;

  try {
    const ts = Date.now();
    const [rf, re] = await Promise.all([
      fetch(`data/fixtures/mundial.json?t=${ts}`),
      fetch(`data/equipos.json?t=${ts}`),
    ]);
    const partidos = await rf.json();
    const equipos  = await re.json();

    for (const eq of equipos) {
      slugPorId[String(eq.id)] = eq.slug;
      if (eq.api_id) slugPorId[String(eq.api_id)] = eq.slug;
      if (eq.grupo) grupoPorSlug[eq.slug] = eq.grupo;
    }

    // Candidatos a "en juego": no terminado en el JSON, con api_id, dentro de la
    // ventana de 24h desde el kickoff (o ya marcado en vivo por la API).
    const now = Date.now();
    const candidatos = partidos.filter(p => {
      if (!p.api_id) return false;
      if (p.status?.finished || p.status?.cancelled) return false;
      const utc = p.status?.utcTime ? new Date(p.status.utcTime).getTime() : null;
      const dentroVentana = utc && (now >= utc) && (now <= utc + 24 * 60 * 60 * 1000);
      const yaEnCurso = LIVE_SHORT.includes(p.status?.short);
      return dentroVentana || yaEnCurso;
    });

    if (!candidatos.length) { cont.style.display = 'none'; return; }

    // mundial.json es estático y puede quedar desactualizado tras el FT (lo
    // actualiza el pipeline post-partido). Confirmamos el estado real con la API:
    // si el partido ya terminó, no se muestra. Si la API falla, usamos el dato
    // optimista del JSON (mejor mostrarlo de más que esconder uno en vivo).
    const base = getApiBase(), headers = getApiHeaders();
    const live = [];
    for (const p of candidatos) {
      try {
        const r = await fetch(`${base}/fixtures?id=${p.api_id}`, { headers });
        if (r.ok) {
          const fx = (await r.json()).response?.[0];
          const short = fx?.fixture?.status?.short;
          if (['FT','AET','PEN'].includes(short)) continue;   // ya terminó → omitir
          if (fx) {
            if (fx.goals?.home != null) p.home_score = fx.goals.home;
            if (fx.goals?.away != null) p.away_score = fx.goals.away;
            if (short) { p.status.short = short; p.status.started = true; }
          }
        }
      } catch (_) { /* API caída → usar el dato optimista del JSON */ }
      live.push(p);
    }

    if (!live.length) { cont.style.display = 'none'; return; }

    cont.innerHTML = `<div class="live-match-tit">En juego ahora</div><div id="live-match-cards"></div>`;
    cont.style.display = '';
    const cardsWrap = cont.querySelector('#live-match-cards');

    const liveCards = [];
    for (const p of live) {
      const card = crearCardPartido(p);
      cardsWrap.appendChild(card);
      liveCards.push({ p, card });
    }

    startLivePolling(liveCards, cont);
  } catch (e) {
    cont.style.display = 'none';
  }
}

window.LiveMatch = { init };
})();
