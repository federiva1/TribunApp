export const config = { runtime: 'edge' };

// Fallback de alineaciones EN VIVO: cuando api-sports no publica los lineups de un
// partido (pasa con algunos partidos de LPF — devolvió response:[] con el partido en
// juego), el frontend pide acá y este endpoint las saca de FotMob. FotMob hace SSR:
// el lineup viene embebido en <script id="__NEXT_DATA__"> del HTML del partido, y el
// navegador no puede pedirlo directo por CORS — por eso el passthrough.
// GET /api/fotmob?home={slug}&away={slug}&date=YYYY-MM-DD
// → { lineup: { [slug]: { formacion, titulares: [{nombre, num, portero, pos:{x,y}}] } } }
// pos = % sobre la cancha apaisada con el arquero a la izquierda (misma convención
// que data/partidos — horizontalLayout de FotMob × 100, sin transformar).

// slug → fotmob team id. Fuente de verdad: scripts/clubes_map.py (mantener a mano).
const FOTMOB_IDS = {
  argentinosjuniors: 10086, velezsarsfield: 10079, estudiantes: 10094,
  bocajuniors: 10077, defensayjusticia: 161730, union: 10096, lanus: 10082,
  talleres: 10101, independiente: 10078, sanlorenzo: 10083,
  clubatleticoplatense: 10089, gimnasiamendoza: 568727,
  centralcordobadesantiago: 213596, instituto: 10090, deportivoriestra: 298629,
  newellsoldboys: 10201, independienterivadavia: 161729, riverplate: 10076,
  belgrano: 10092, racingclub: 10080, rosariocentral: 10084, tigre: 89396,
  barracascentral: 213534, sarmiento: 202757, huracan: 10081, gimnasialp: 10103,
  banfield: 10087, atleticotucuman: 161727, aldosivi: 161728,
  estudiantesderiocuarto: 213591,
};

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

function originOk(req) {
  const raw = req.headers.get('origin') || req.headers.get('referer') || '';
  if (!raw) return true;
  let host;
  try { host = new URL(raw).hostname.toLowerCase(); } catch (e) { return false; }
  return host === 'tribunapp.com.ar' ||
         host.endsWith('.tribunapp.com.ar') ||
         host.endsWith('.vercel.app');
}

function json(body, status, cache) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': cache || 'public, max-age=60' },
  });
}

async function nextData(url) {
  const res = await fetch(url, {
    headers: { 'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8' },
  });
  if (!res.ok) return null;
  const html = await res.text();
  const i = html.indexOf('id="__NEXT_DATA__"');
  if (i < 0) return null;
  const j = html.indexOf('>', i), k = html.indexOf('</script>', j);
  if (j < 0 || k < 0) return null;
  try { return JSON.parse(html.slice(j + 1, k)); } catch (e) { return null; }
}

// Página de fixtures del equipo → pageUrl del partido de esa fecha (UTC).
async function resolveMatchUrl(fotmobId, date) {
  const d = await nextData('https://www.fotmob.com/teams/' + fotmobId + '/fixtures');
  if (!d) return null;
  let fx;
  try { fx = d.props.pageProps.fallback['team-' + fotmobId].fixtures; } catch (e) { return null; }
  const fixtures = (fx && !Array.isArray(fx)) ? ((fx.allFixtures || {}).fixtures || fx) : fx;
  if (!Array.isArray(fixtures)) return null;
  for (const m of fixtures) {
    const utc = String(((m.status || {}).utcTime) || m.utcTime || '');
    if (utc.indexOf(date) >= 0 && m.pageUrl) return 'https://www.fotmob.com' + m.pageUrl;
  }
  return null;
}

function equipoDe(team) {
  const starters = team.starters || [];
  if (starters.length < 7) return null;
  const titulares = [];
  let minX = null;
  for (const p of starters) {
    const h = p.horizontalLayout || {};
    const pos = (h.x != null && h.y != null)
      ? { x: Math.round(h.x * 1000) / 10, y: Math.round(h.y * 1000) / 10 } : null;
    if (pos && (minX === null || pos.x < minX)) minX = pos.x;
    titulares.push({
      nombre: p.name || '', num: String(p.shirtNumber || ''), pos: pos, portero: false,
    });
  }
  // El arquero es el de menor x (cancha apaisada, arquero a la izquierda).
  for (const t of titulares) if (t.pos && t.pos.x === minX) { t.portero = true; break; }
  return { formacion: team.formation || '', titulares: titulares };
}

export default async function handler(req) {
  if (!originOk(req)) return json({ error: 'origen no permitido' }, 403, 'no-store');
  const url = new URL(req.url);
  const home = (url.searchParams.get('home') || '').toLowerCase();
  const away = (url.searchParams.get('away') || '').toLowerCase();
  const date = url.searchParams.get('date') || '';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return json({ error: 'date inválida' }, 400, 'no-store');
  if (!FOTMOB_IDS[home] && !FOTMOB_IDS[away]) return json({ error: 'club desconocido' }, 400, 'no-store');

  // Se resuelve por el fixture de cualquiera de los dos clubes que esté en el mapa
  // (en copa el rival extranjero no está).
  const baseId = FOTMOB_IDS[home] || FOTMOB_IDS[away];
  const matchUrl = await resolveMatchUrl(baseId, date);
  if (!matchUrl) return json({ lineup: null, motivo: 'partido no encontrado' }, 200, 'public, max-age=60');

  const nd = await nextData(matchUrl);
  let lu;
  try { lu = nd.props.pageProps.content.lineup; } catch (e) { lu = null; }
  if (!lu) return json({ lineup: null, motivo: 'sin lineup todavía' }, 200, 'public, max-age=60');

  // Lado FotMob → slug nuestro, matcheando por team id (sin confiar en que el
  // "home" de FotMob coincida con el de api-sports).
  const out = {};
  for (const side of ['homeTeam', 'awayTeam']) {
    const t = lu[side] || {};
    let slug = null;
    if (FOTMOB_IDS[home] === t.id) slug = home;
    else if (FOTMOB_IDS[away] === t.id) slug = away;
    else slug = (FOTMOB_IDS[home] ? away : home);   // el que no está en el mapa
    const eq = t.starters ? equipoDe(t) : null;
    if (slug && eq) out[slug] = eq;
  }
  if (!Object.keys(out).length) return json({ lineup: null, motivo: 'sin titulares' }, 200, 'public, max-age=60');
  // Una vez confirmadas, las alineaciones no cambian → cache más larga.
  return json({ lineup: out }, 200, 'public, max-age=300');
}
