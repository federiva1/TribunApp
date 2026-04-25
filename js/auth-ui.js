// ============================================================
// auth-ui.js — Modal de login/registro + botón header
// Requiere: js/config.js, js/auth.js, js/clubes.js
// ============================================================

(function () {

  // ---- Inyectar estilos ----
  const style = document.createElement('style');
  style.textContent = `
#auth-modal-overlay {
  display: none;
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  align-items: center; justify-content: center;
}
#auth-modal-overlay.open { display: flex; }
#auth-modal {
  background: #1a1a2e;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  padding: 24px 20px 20px;
  width: 100%; max-width: 360px;
  margin: 16px;
  position: relative;
}
#auth-modal-close {
  position: absolute; top: 12px; right: 14px;
  background: none; border: none; color: rgba(255,255,255,0.4);
  font-size: 20px; cursor: pointer; line-height: 1;
}
#auth-modal-close:hover { color: #fff; }
.auth-tabs {
  display: flex; gap: 4px;
  background: rgba(255,255,255,0.05);
  border-radius: 10px; padding: 4px;
  margin-bottom: 20px;
}
.auth-tab-btn {
  flex: 1;
  font-family: 'Bebas Neue', sans-serif; font-size: 14px; letter-spacing: 1px;
  border: none; background: transparent; color: rgba(255,255,255,0.4);
  border-radius: 7px; padding: 8px 4px; cursor: pointer; transition: all 0.2s;
}
.auth-tab-btn.active { background: #1565c0; color: #fff; }
.auth-form-group { margin-bottom: 14px; }
.auth-form-group label {
  display: block;
  font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 1px;
  color: rgba(255,255,255,0.4); text-transform: uppercase; margin-bottom: 6px;
}
.auth-input {
  width: 100%; background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
  padding: 10px 12px; color: #fff; font-size: 14px;
  font-family: 'DM Sans', sans-serif; outline: none;
  transition: border-color 0.2s;
}
.auth-input:focus { border-color: #1565c0; }
.auth-select {
  width: 100%; background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
  padding: 10px 12px; color: #fff; font-size: 13px;
  font-family: 'DM Sans', sans-serif; outline: none;
  cursor: pointer; appearance: none;
  transition: border-color 0.2s;
}
.auth-select:focus { border-color: #1565c0; }
.auth-select option { background: #1a1a2e; }
.auth-submit-btn {
  width: 100%;
  font-family: 'Bebas Neue', sans-serif; font-size: 16px; letter-spacing: 1px;
  background: #1565c0; color: #fff; border: none;
  border-radius: 8px; padding: 12px; cursor: pointer;
  margin-top: 4px; transition: background 0.2s;
}
.auth-submit-btn:hover { background: #1976d2; }
.auth-submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.auth-error {
  font-size: 12px; color: #e53935; text-align: center;
  margin-top: 10px; min-height: 16px; line-height: 1.4;
}
.auth-success {
  font-size: 12px; color: #4caf50; text-align: center;
  margin-top: 10px; min-height: 16px; line-height: 1.4;
}

/* ---- Botón header ---- */
#auth-header-btn {
  display: flex; align-items: center; gap: 7px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 12px; padding: 6px 12px;
  cursor: pointer; font-family: 'Bebas Neue', sans-serif;
  font-size: 13px; letter-spacing: 1px; color: rgba(255,255,255,0.65);
  transition: background 0.2s, color 0.2s;
  white-space: nowrap;
}
#auth-header-btn:hover { background: rgba(255,255,255,0.12); color: #fff; }
#auth-header-btn.logged-in {
  border-color: rgba(21,101,192,0.5);
  background: rgba(21,101,192,0.12);
  color: #fff;
}
.auth-btn-escudo {
  width: 22px; height: 22px; object-fit: contain; border-radius: 50%;
}
  `;
  document.head.appendChild(style);

  // ---- Crear modal DOM ----
  const overlay = document.createElement('div');
  overlay.id = 'auth-modal-overlay';
  overlay.innerHTML = `
    <div id="auth-modal">
      <button id="auth-modal-close">✕</button>
      <div style="text-align:center;margin-bottom:16px;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:22px;letter-spacing:2px;color:#fff;">TRIBUNAPP</div>
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;letter-spacing:1px;color:rgba(255,255,255,0.35);margin-top:2px;">Tu app de fútbol argentino</div>
      </div>
      <div class="auth-tabs">
        <button class="auth-tab-btn active" data-tab="login" onclick="authSwitchTab('login',this)">Ingresar</button>
        <button class="auth-tab-btn" data-tab="register" onclick="authSwitchTab('register',this)">Registrarse</button>
      </div>

      <!-- TAB LOGIN -->
      <div id="auth-tab-login">
        <div class="auth-form-group">
          <label>Email</label>
          <input id="auth-login-email" class="auth-input" type="email" placeholder="tu@email.com" autocomplete="email">
        </div>
        <div class="auth-form-group">
          <label>Contraseña</label>
          <input id="auth-login-pass" class="auth-input" type="password" placeholder="••••••••" autocomplete="current-password">
        </div>
        <button class="auth-submit-btn" id="auth-login-btn" onclick="authDoLogin()">INGRESAR</button>
        <div class="auth-error" id="auth-login-error"></div>
      </div>

      <!-- TAB REGISTRO -->
      <div id="auth-tab-register" style="display:none;">
        <div class="auth-form-group">
          <label>Email</label>
          <input id="auth-reg-email" class="auth-input" type="email" placeholder="tu@email.com" autocomplete="email">
        </div>
        <div class="auth-form-group">
          <label>Contraseña</label>
          <input id="auth-reg-pass" class="auth-input" type="password" placeholder="Mínimo 6 caracteres" autocomplete="new-password">
        </div>
        <div class="auth-form-group">
          <label>Tu equipo</label>
          <select id="auth-reg-equipo" class="auth-select">
            <option value="">-- Elegí tu equipo --</option>
          </select>
        </div>
        <button class="auth-submit-btn" id="auth-reg-btn" onclick="authDoRegister()">REGISTRARSE</button>
        <div class="auth-error" id="auth-reg-error"></div>
        <div class="auth-success" id="auth-reg-success"></div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  // Cerrar con click fuera o botón ✕
  overlay.addEventListener('click', e => { if (e.target === overlay) closeAuthModal(); });
  document.getElementById('auth-modal-close').addEventListener('click', closeAuthModal);

  // Enter en inputs de login
  document.getElementById('auth-login-pass').addEventListener('keydown', e => { if (e.key === 'Enter') authDoLogin(); });
  document.getElementById('auth-login-email').addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('auth-login-pass').focus(); });

  // Poblar dropdown de equipos
  const sel = document.getElementById('auth-reg-equipo');
  if (typeof CLUBES_CONFIG !== 'undefined') {
    Object.entries(CLUBES_CONFIG)
      .sort((a, b) => a[1].nombre.localeCompare(b[1].nombre, 'es'))
      .forEach(([slug, club]) => {
        const opt = document.createElement('option');
        opt.value = slug;
        opt.textContent = club.nombre;
        sel.appendChild(opt);
      });
  }

  // ---- API pública ----
  window.openAuthModal = function(tab) {
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    if (tab) authSwitchTab(tab, document.querySelector(`.auth-tab-btn[data-tab="${tab}"]`));
    // Limpiar errores
    document.getElementById('auth-login-error').textContent = '';
    document.getElementById('auth-reg-error').textContent = '';
    document.getElementById('auth-reg-success').textContent = '';
  };

  window.closeAuthModal = function() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  };

  window.authSwitchTab = function(tab, btn) {
    document.querySelectorAll('.auth-tab-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.getElementById('auth-tab-login').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('auth-tab-register').style.display = tab === 'register' ? 'block' : 'none';
  };

  window.authDoLogin = async function() {
    const email = document.getElementById('auth-login-email').value.trim();
    const pass  = document.getElementById('auth-login-pass').value;
    const errEl = document.getElementById('auth-login-error');
    const btn   = document.getElementById('auth-login-btn');
    errEl.textContent = '';
    if (!email || !pass) { errEl.textContent = 'Completá todos los campos.'; return; }
    btn.disabled = true; btn.textContent = 'INGRESANDO...';
    try {
      await signIn(email, pass);
      closeAuthModal();
    } catch(e) {
      errEl.textContent = _translateError(e.message);
    } finally {
      btn.disabled = false; btn.textContent = 'INGRESAR';
    }
  };

  window.authDoRegister = async function() {
    const email  = document.getElementById('auth-reg-email').value.trim();
    const pass   = document.getElementById('auth-reg-pass').value;
    const equipo = document.getElementById('auth-reg-equipo').value;
    const errEl  = document.getElementById('auth-reg-error');
    const sucEl  = document.getElementById('auth-reg-success');
    const btn    = document.getElementById('auth-reg-btn');
    errEl.textContent = ''; sucEl.textContent = '';
    if (!email || !pass) { errEl.textContent = 'Completá email y contraseña.'; return; }
    if (pass.length < 6) { errEl.textContent = 'La contraseña debe tener al menos 6 caracteres.'; return; }
    btn.disabled = true; btn.textContent = 'REGISTRANDO...';
    try {
      await signUp(email, pass, equipo || null);
      sucEl.textContent = '¡Cuenta creada! Revisá tu email para confirmar.';
    } catch(e) {
      errEl.textContent = _translateError(e.message);
    } finally {
      btn.disabled = false; btn.textContent = 'REGISTRARSE';
    }
  };

  function _translateError(msg) {
    if (!msg) return 'Error desconocido.';
    if (msg.includes('Invalid login')) return 'Email o contraseña incorrectos.';
    if (msg.includes('Email not confirmed')) return 'Confirmá tu email antes de ingresar.';
    if (msg.includes('already registered')) return 'Ya existe una cuenta con ese email.';
    if (msg.includes('Password should be')) return 'La contraseña debe tener al menos 6 caracteres.';
    if (msg.includes('Unable to validate')) return 'Email inválido.';
    return msg;
  }

  // ---- Inicializar botón de header ----
  // El botón ya existe en el HTML — este método solo adjunta handlers y actualiza apariencia
  window.initAuthHeaderBtn = function() {
    const btn = document.getElementById('auth-header-btn');
    if (!btn) return;

    btn.addEventListener('click', () => {
      if (currentUser) _showUserMenu(btn);
      else openAuthModal('login');
    });

    _renderAuthBtn();
    onAuthChange(() => _renderAuthBtn());
  };

  function _renderAuthBtn() {
    const btn = document.getElementById('auth-header-btn');
    if (!btn) return;
    btn.innerHTML = '';
    if (currentUser) {
      btn.className = 'auth-header-btn logged-in';
      btn.style.cssText = 'display:flex;align-items:center;gap:7px;background:rgba(21,101,192,0.15);border:1px solid rgba(21,101,192,0.5);border-radius:12px;padding:6px 12px;cursor:pointer;font-family:"Bebas Neue",sans-serif;font-size:13px;letter-spacing:1px;color:#fff;transition:background 0.2s;white-space:nowrap;';
      if (currentUser.equipoHincha && typeof CLUBES_CONFIG !== 'undefined' && CLUBES_CONFIG[currentUser.equipoHincha]) {
        const img = document.createElement('img');
        img.src = `escudos/${currentUser.equipoHincha}.png`;
        img.className = 'auth-btn-escudo';
        img.onerror = () => img.style.display = 'none';
        btn.appendChild(img);
      } else {
        const icon = document.createElement('span');
        icon.textContent = '👤';
        icon.style.fontSize = '14px';
        btn.appendChild(icon);
      }
      const label = document.createElement('span');
      label.textContent = 'Mi cuenta';
      btn.appendChild(label);
    } else {
      btn.className = '';
      btn.style.cssText = 'display:flex;align-items:center;gap:6px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);border-radius:12px;padding:6px 12px;cursor:pointer;font-family:"Bebas Neue",sans-serif;font-size:13px;letter-spacing:1px;color:rgba(255,255,255,0.65);transition:background 0.2s,color 0.2s;white-space:nowrap;';
      const label = document.createElement('span');
      label.textContent = 'Ingresar';
      btn.appendChild(label);
    }
  }

  // Mini-menú desplegable para usuario logueado
  function _showUserMenu(anchorBtn) {
    const existing = document.getElementById('auth-user-menu');
    if (existing) { existing.remove(); return; }

    const menu = document.createElement('div');
    menu.id = 'auth-user-menu';
    const rect = anchorBtn.getBoundingClientRect();
    menu.style.cssText = `position:fixed;top:${rect.bottom + 6}px;right:${window.innerWidth - rect.right}px;background:#1a1a2e;border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:8px;z-index:1001;min-width:160px;`;

    const emailEl = document.createElement('div');
    emailEl.style.cssText = 'font-size:11px;color:rgba(255,255,255,0.4);padding:4px 8px 8px;border-bottom:1px solid rgba(255,255,255,0.07);font-family:"DM Sans",sans-serif;word-break:break-all;';
    emailEl.textContent = currentUser.email;
    menu.appendChild(emailEl);

    if (currentUser.equipoHincha && typeof CLUBES_CONFIG !== 'undefined' && CLUBES_CONFIG[currentUser.equipoHincha]) {
      const clubEl = document.createElement('div');
      clubEl.style.cssText = 'display:flex;align-items:center;gap:8px;padding:8px;font-family:"Barlow Condensed",sans-serif;font-size:12px;letter-spacing:1px;color:rgba(255,255,255,0.55);border-bottom:1px solid rgba(255,255,255,0.07);';
      const img = document.createElement('img');
      img.src = `escudos/${currentUser.equipoHincha}.png`;
      img.style.cssText = 'width:18px;height:18px;object-fit:contain;';
      img.onerror = () => img.style.display = 'none';
      clubEl.appendChild(img);
      clubEl.appendChild(document.createTextNode(CLUBES_CONFIG[currentUser.equipoHincha].nombre));
      menu.appendChild(clubEl);
    }

    const logoutBtn = document.createElement('button');
    logoutBtn.style.cssText = 'width:100%;background:transparent;border:none;color:rgba(229,57,53,0.8);font-family:"Bebas Neue",sans-serif;font-size:14px;letter-spacing:1px;padding:8px;cursor:pointer;text-align:left;border-radius:6px;';
    logoutBtn.textContent = 'Cerrar sesión';
    logoutBtn.onmouseover = () => logoutBtn.style.background = 'rgba(229,57,53,0.1)';
    logoutBtn.onmouseout = () => logoutBtn.style.background = 'transparent';
    logoutBtn.addEventListener('click', async () => {
      menu.remove();
      try { await signOut(); } catch(e) {}
    });
    menu.appendChild(logoutBtn);

    document.body.appendChild(menu);

    // Cerrar al hacer click fuera
    setTimeout(() => {
      document.addEventListener('click', function handler(e) {
        if (!menu.contains(e.target) && e.target !== anchorBtn) {
          menu.remove();
          document.removeEventListener('click', handler);
        }
      });
    }, 0);
  }

})();
