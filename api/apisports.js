export const config = { runtime: 'edge' };

// La API key vive solo en la env var API_SPORTS_KEY de Vercel — nunca en el repo.

// Allowlist: solo los endpoints que la app realmente consume. Bloquea
// /status (que filtra datos de la cuenta) y cualquier otro uso abusivo del proxy.
const ALLOWED = ['fixtures', 'standings', 'teams', 'players'];

const UPSTREAM = 'https://v3.football.api-sports.io';

// Orígenes permitidos (defensa adicional contra uso del proxy desde afuera).
// Se parsea el hostname y se compara exacto/sufijo — un regex sin anclar dejaba
// pasar tribunapp.com.ar.evil.com. Falta de header = fetch mismo-origen (los GET
// same-origin no mandan Origin), se permite; el gate real es la allowlist de path.
function originOk(req) {
  const raw = req.headers.get('origin') || req.headers.get('referer') || '';
  if (!raw) return true;
  let host;
  try { host = new URL(raw).hostname.toLowerCase(); } catch (e) { return false; }
  return host === 'tribunapp.com.ar' ||
         host.endsWith('.tribunapp.com.ar') ||
         host.endsWith('.vercel.app');
}

export default async function handler(req) {
  const key = process.env.API_SPORTS_KEY;
  if (!key) {
    return new Response(JSON.stringify({ error: 'API_SPORTS_KEY no configurada' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
  const url = new URL(req.url);

  // El rewrite de vercel.json pasa el segmento como query param "path".
  let apiPath = url.pathname.replace(/^\/api\/apisports/, '');
  const pathParam = url.searchParams.get('path');
  if (!apiPath && pathParam) apiPath = '/' + pathParam;
  url.searchParams.delete('path');

  // NORMALIZAR antes de validar: se construye la URL upstream y se re-parsea, así
  // cualquier `..` o `//` se colapsa y validamos el path REAL. Antes se validaba el
  // primer segmento del path crudo, pero fetch() (edge/WHATWG URL) colapsa los
  // `..` recién al pegar → `path=fixtures/../status` pasaba el gate y llegaba a
  // /status (datos de la cuenta) gastando la cuota paga.
  let normPath;
  try {
    const u = new URL(apiPath.replace(/^\/*/, '/'), UPSTREAM);
    if (u.origin !== UPSTREAM) {            // apiPath absoluto/protocol-relative (//evil.com)
      return new Response(JSON.stringify({ error: 'path no permitido' }), {
        status: 403, headers: { 'Content-Type': 'application/json' },
      });
    }
    normPath = u.pathname;                  // ya normalizado, sin `..`
  } catch (e) {
    return new Response(JSON.stringify({ error: 'path inválido' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const seg = normPath.replace(/^\/+/, '').split('/')[0].toLowerCase();
  if (!ALLOWED.includes(seg)) {
    return new Response(JSON.stringify({ error: 'endpoint no permitido' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!originOk(req)) {
    return new Response(JSON.stringify({ error: 'origen no permitido' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }

  // Datos en vivo (marcador/estado de un partido en curso): nunca cachear, o el CDN
  // sirve una respuesta vieja (ej. live=all de hace rato, sin el partido de hoy).
  // El resto (standings, teams, players, listados de fixtures) sí puede cachear 60s.
  const isLive = seg === 'fixtures' &&
    (url.searchParams.has('live') || url.searchParams.has('id') || url.searchParams.has('fixture'));
  const cacheControl = isLive ? 'no-store' : 'public, max-age=60';

  const qs = url.searchParams.toString();
  const upstream = UPSTREAM + normPath + (qs ? '?' + qs : '');

  const res = await fetch(upstream, { headers: { 'x-apisports-key': key } });
  const body = await res.arrayBuffer();
  return new Response(body, {
    status: res.status,
    headers: {
      'Content-Type': res.headers.get('Content-Type') || 'application/json',
      'Cache-Control': cacheControl,
    },
  });
}
