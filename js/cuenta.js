/* Cuenta de usuario (login opcional) — la cargan todas las páginas con #site-header.

   - Carga supabase-js y crea un cliente con la sesión guardada (localStorage del navegador).
   - Pone el botón de cuenta en el header ("Ingresar" o el escudo + usuario). No es una
     .header-pill, así que js/header-menu.js no lo mete en el ☰: queda siempre a la vista.
   - Expone window.TA_CUENTA para que las páginas firmen los votos con el usuario.

   Sin sesión, todo sigue como siempre (invitado por device_id). Con sesión, los votos
   (formaciones y puntajes) llevan además user_id y van con el token del usuario; el
   equipo del hincha lo completa la base desde el perfil (trigger voto_equipo_hincha),
   no se confía en lo que manda el navegador. */
(function () {
  const SB_URL = (typeof SUPABASE_URL !== 'undefined') ? SUPABASE_URL : 'https://ieujdkthaoujtnndkiqo.supabase.co';
  const SB_KEY = (typeof SUPABASE_KEY !== 'undefined') ? SUPABASE_KEY
    : 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlldWpka3RoYW91anRubmRraXFvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMTEwOTYsImV4cCI6MjA5MTc4NzA5Nn0.FDzVx-W3v48Eq9_hSzsghP1Q8ES4e70S7MN2koGT5wY';
  const LIB = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js';

  let resolver;
  const subs = [];
  const C = window.TA_CUENTA = {
    listo: new Promise(r => { resolver = r; }),
    client: null,
    user: null,       // auth user (null = invitado)
    perfil: null,     // fila de perfiles (null = sin perfil todavía)
    onCambio(fn) { subs.push(fn); },
    url: SB_URL,
    key: SB_KEY,
  };

  function cargarLib() {
    if (window.supabase && window.supabase.createClient) return Promise.resolve();
    return new Promise((ok, ko) => {
      const s = document.createElement('script');
      s.src = LIB; s.async = true;
      s.onload = () => ok(); s.onerror = () => ko(new Error('supabase-js no cargó'));
      document.head.appendChild(s);
    });
  }

  async function leerPerfil(user) {
    const { data } = await C.client.from('perfiles').select('*').eq('id', user.id).maybeSingle();
    if (data) return data;
    // Recién confirmado el mail: el perfil se crea con lo que dejó en el registro
    const m = user.user_metadata || {};
    if (m.username && m.equipo_hincha) {
      const fila = { id: user.id, username: m.username, equipo_hincha: m.equipo_hincha, publico: m.publico !== false };
      const { data: nuevo, error } = await C.client.from('perfiles').insert(fila).select().maybeSingle();
      if (!error && nuevo) return nuevo;
    }
    return null;
  }

  async function refrescar(session) {
    C.user = session ? session.user : null;
    C.perfil = C.user ? await leerPerfil(C.user).catch(() => null) : null;
    pintarBoton();
    subs.forEach(fn => { try { fn(C); } catch (e) { console.error(e); } });
  }

  /* Vuelve a leer sesión + perfil (después de crear o editar el perfil) */
  C.recargar = async function () {
    const { data } = await C.client.auth.getSession();
    await refrescar(data.session);
  };

  /* Datos para firmar un voto: { headers, extra }. Sin usuario con perfil → anónimo de siempre. */
  C.firmaVoto = async function () {
    const anon = { headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` }, extra: {} };
    try {
      await Promise.race([C.listo, new Promise(r => setTimeout(r, 4000))]);
      if (!C.client || !C.user || !C.perfil) return anon;
      const { data } = await C.client.auth.getSession();   // renueva el token si venció
      const s = data && data.session;
      if (!s) return anon;
      return { headers: { apikey: SB_KEY, Authorization: `Bearer ${s.access_token}` }, extra: { user_id: s.user.id } };
    } catch (e) { return anon; }
  };

  // ---------- botón del header ----------
  let btn;
  function pintarBoton() {
    const header = document.getElementById('site-header');
    const acts = header && header.querySelector('.header-actions');
    if (!acts) return;
    if (!btn) {
      const css = document.createElement('style');
      css.textContent = `
        .cuenta-btn { display: flex; align-items: center; gap: 7px; height: 36px; padding: 0 12px 0 10px; flex: 0 0 auto;
          border-radius: 10px; text-decoration: none; color: #fff; font-family: 'Barlow Condensed', sans-serif;
          font-size: 13px; letter-spacing: .5px; background: rgba(245,197,24,.12); border: 1px solid rgba(245,197,24,.35); }
        .cuenta-btn:hover { background: rgba(245,197,24,.22); }
        .cuenta-btn svg { width: 16px; height: 16px; color: #f5c518; flex: 0 0 auto; }
        .cuenta-btn img { width: 22px; height: 22px; object-fit: contain; flex: 0 0 auto; }
        .cuenta-btn .cb-txt { max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .cuenta-btn.falta { border-color: #f5c518; box-shadow: 0 0 0 2px rgba(245,197,24,.25); }
        @media (max-width: 560px) { .cuenta-btn { width: 36px; padding: 0; justify-content: center; } .cuenta-btn .cb-txt { display: none; } }`;
      document.head.appendChild(css);
      btn = document.createElement('a');
      btn.className = 'cuenta-btn';
      const menu = acts.querySelector('.header-menu-btn');
      acts.insertBefore(btn, menu || null);
    }
    const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    const ICO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/></svg>';
    btn.href = 'cuenta.html';
    btn.classList.toggle('falta', !!(C.user && !C.perfil));
    if (C.user && C.perfil) {
      btn.innerHTML = `<img src="escudos/${esc(C.perfil.equipo_hincha)}.png" alt="" onerror="this.remove()"><span class="cb-txt">${esc(C.perfil.username || 'Mi cuenta')}</span>`;
      btn.title = 'Mi cuenta';
    } else if (C.user) {
      btn.innerHTML = `${ICO}<span class="cb-txt">Completar perfil</span>`;
      btn.title = 'Completá tu perfil';
    } else {
      btn.innerHTML = `${ICO}<span class="cb-txt">Ingresar</span>`;
      btn.title = 'Ingresar o crear cuenta';
    }
    window.dispatchEvent(new Event('resize'));   // header-menu.js vuelve a medir
  }

  async function init() {
    pintarBoton();
    try {
      await cargarLib();
      C.client = window.supabase.createClient(SB_URL, SB_KEY, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'tribunapp-auth' },
      });
      const { data } = await C.client.auth.getSession();
      await refrescar(data.session);
      C.client.auth.onAuthStateChange((ev, session) => {
        C.ultimoEvento = ev;
        if (ev === 'INITIAL_SESSION') return;
        if (ev === 'TOKEN_REFRESHED' && C.user && session && session.user.id === C.user.id) return;
        refrescar(session);
      });
    } catch (e) {
      console.warn('cuenta:', e.message);
    }
    resolver(C);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
