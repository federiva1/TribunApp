export const config = { runtime: 'edge' };

// Fallback a la key pública del repo si la env var no está configurada en Vercel.
// Esta misma key ya está expuesta client-side en otras páginas (standings, fixture local).
const FALLBACK_KEY = 'b8bbfc856fd5cf12cd7d697b2b01887d';

export default async function handler(req) {
  const key = process.env.API_SPORTS_KEY || FALLBACK_KEY;

  const url = new URL(req.url);
  // Remove the /api/apisports prefix; the rest becomes the api-sports path+query
  const upstream = 'https://v3.football.api-sports.io' + url.pathname.replace(/^\/api\/apisports/, '') + url.search;

  const res = await fetch(upstream, {
    headers: { 'x-apisports-key': key },
  });

  const body = await res.arrayBuffer();
  return new Response(body, {
    status: res.status,
    headers: {
      'Content-Type': res.headers.get('Content-Type') || 'application/json',
      'Cache-Control': 'public, max-age=60',
    },
  });
}
