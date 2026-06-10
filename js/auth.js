// ============================================================
// auth.js — Supabase Auth client para TribunApp
// Requiere: js/config.js (SUPABASE_URL, SUPABASE_KEY)
// CDN de supabase-js debe estar incluido antes de este archivo
// ============================================================

let _supabase = null;

function getSupabaseClient() {
  if (!_supabase) {
    _supabase = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
  }
  return _supabase;
}

// Estado global del usuario autenticado — declarado en config.js para disponibilidad temprana
// { id, email, equipoHincha } | null

// Callbacks registrados para cambios de sesión
const _authListeners = [];

window.onAuthChange = function onAuthChange(fn) {
  _authListeners.push(fn);
};

function _notifyListeners(user) {
  _authListeners.forEach(fn => { try { fn(user); } catch(e) {} });
}

// ---- Inicializar: leer sesión existente y suscribirse a cambios ----
async function initAuth() {
  const sb = getSupabaseClient();
  const { data: { session } } = await sb.auth.getSession();
  if (session) {
    currentUser = await _buildUser(session.user);
  }
  sb.auth.onAuthStateChange(async (event, session) => {
    if (session) {
      currentUser = await _buildUser(session.user);
    } else {
      currentUser = null;
    }
    _notifyListeners(currentUser);
  });
  return currentUser;
}

async function _buildUser(supaUser) {
  const sb = getSupabaseClient();
  // Intentar leer equipo_hincha desde perfiles
  let equipoHincha = null;
  try {
    const { data } = await sb
      .from('perfiles')
      .select('equipo_hincha')
      .eq('id', supaUser.id)
      .single();
    equipoHincha = data?.equipo_hincha || null;
  } catch(e) {}
  return { id: supaUser.id, email: supaUser.email, equipoHincha };
}

// ---- Registro ----
async function signUp(email, password, equipoSlug) {
  const sb = getSupabaseClient();
  const redirectTo = window.location.protocol === 'file:'
    ? 'https://federiva1.github.io/TribunApp/'
    : window.location.origin + '/';
  const { data, error } = await sb.auth.signUp({ email, password, options: { emailRedirectTo: redirectTo } });
  if (error) throw error;
  // Crear perfil con equipo_hincha
  if (data.user) {
    await sb.from('perfiles').upsert({
      id: data.user.id,
      equipo_hincha: equipoSlug || null
    });
  }
  return data;
}

// ---- Login ----
async function signIn(email, password) {
  const sb = getSupabaseClient();
  const { data, error } = await sb.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
}

// ---- Google OAuth ----
async function signInWithGoogle() {
  const sb = getSupabaseClient();
  const { error } = await sb.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin + window.location.pathname }
  });
  if (error) throw error;
}

// ---- Logout ----
async function signOut() {
  const sb = getSupabaseClient();
  const { error } = await sb.auth.signOut();
  if (error) throw error;
}

// ---- Sesión actual (no async, usa estado en memoria) ----
function getSession() {
  return currentUser;
}
