// Supabase config — no subir a repos públicos si usás service_role key
const _SUPABASE_URL = 'https://ieujdkthaoujtnndkiqo.supabase.co';
const _SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlldWpka3RoYW91anRubmRraXFvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMTEwOTYsImV4cCI6MjA5MTc4NzA5Nn0.FDzVx-W3v48Eq9_hSzsghP1Q8ES4e70S7MN2koGT5wY';

// Stack de auth de clubes argentinos (auth.js / auth-ui.js) espera estos nombres.
// currentUser DEBE ser `var` (hoisting) para estar disponible a los inline scripts
// que corren antes de auth.js — ver CLAUDE.md. Los nombres con guion bajo los usan
// las páginas del Mundial (equipo.html, tribunapp-equipo.html, etc.).
var currentUser = null;
const SUPABASE_URL = _SUPABASE_URL;
const SUPABASE_KEY = _SUPABASE_KEY;
