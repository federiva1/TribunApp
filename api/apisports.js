export const config = { runtime: 'edge' };

export default async function handler(req) {
  const key = process.env.API_SPORTS_KEY;
  if (!key) {
    return new Response(JSON.stringify({ error: 'not configured' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

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
