/* ui-help.js — utilidades de UI compartidas:
   1) Tooltips de ayuda por sección: cualquier elemento con [data-help] muestra
      una explicación al tocarlo. Para un ícono usar:
        <span class="help-icon" data-help="texto explicativo"></span>
      También sirve en cualquier otro elemento con data-help.
   2) Banner de idioma: si el visitante no viene en español, le avisa que puede
      traducir con el navegador (la página declara lang="es", así Chrome/Edge/
      Safari ya ofrecen traducirla automáticamente).

   Para secciones que se generan dinámicamente, llamar window.UIHelp.refresh()
   después de inyectar el HTML. */
(function () {
  'use strict';

  // ── Estilos ────────────────────────────────────────────────────────────────
  function injectCSS() {
    if (document.getElementById('ui-help-css')) return;
    var css = ''
      + '.help-icon{display:inline-flex;align-items:center;justify-content:center;'
      + 'width:16px;height:16px;border-radius:50%;border:1px solid rgba(255,255,255,0.35);'
      + 'color:rgba(255,255,255,0.7);font-size:11px;font-weight:700;line-height:1;cursor:pointer;'
      + "vertical-align:middle;margin-left:6px;flex-shrink:0;font-family:'Barlow Condensed',sans-serif;"
      + 'user-select:none;transition:all .15s;}'
      + '.help-icon::before{content:"i";font-style:italic;}'
      + '.help-icon:hover{background:rgba(255,255,255,0.15);color:#fff;border-color:rgba(255,255,255,0.6);}'
      + '.help-pop{position:absolute;z-index:9999;max-width:260px;background:#1c1c1e;color:#eee;'
      + 'border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:10px 12px;font-size:13px;'
      + "line-height:1.45;font-family:'Barlow Condensed',Arial,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,0.5);"
      + 'opacity:0;transform:translateY(-4px);transition:opacity .12s,transform .12s;pointer-events:none;}'
      + '.help-pop.show{opacity:1;transform:translateY(0);pointer-events:auto;}'
      + '#lang-hint-bar{position:sticky;top:0;z-index:9998;display:flex;align-items:center;gap:10px;'
      + 'justify-content:center;background:#11304a;color:#dbe9f7;font-size:13px;padding:8px 14px;'
      + "font-family:'Barlow Condensed',Arial,sans-serif;border-bottom:1px solid rgba(255,255,255,0.08);}"
      + '#lang-hint-bar button{background:transparent;border:none;color:#9fc3e8;font-size:15px;cursor:pointer;'
      + 'padding:0 4px;line-height:1;}'
      + '#lang-hint-bar button:hover{color:#fff;}';
    var s = document.createElement('style');
    s.id = 'ui-help-css';
    s.textContent = css;
    document.head.appendChild(s);
  }

  // ── Tooltip único reutilizable ──────────────────────────────────────────────
  var pop = null, popOwner = null;

  function ensurePop() {
    if (pop) return pop;
    pop = document.createElement('div');
    pop.className = 'help-pop';
    document.body.appendChild(pop);
    return pop;
  }

  function hideTip() {
    if (pop) { pop.classList.remove('show'); popOwner = null; }
  }

  function showTip(anchor, text) {
    var p = ensurePop();
    if (popOwner === anchor && p.classList.contains('show')) { hideTip(); return; }
    p.textContent = text;
    p.classList.add('show');
    popOwner = anchor;
    var r = anchor.getBoundingClientRect();
    var sx = window.scrollX || window.pageXOffset;
    var sy = window.scrollY || window.pageYOffset;
    // Posicionar debajo del ícono, alineado a la izquierda, sin salirse del viewport
    var left = r.left + sx;
    var maxLeft = sx + document.documentElement.clientWidth - p.offsetWidth - 12;
    if (left > maxLeft) left = maxLeft;
    if (left < sx + 8) left = sx + 8;
    p.style.left = left + 'px';
    p.style.top = (r.bottom + sy + 6) + 'px';
  }

  function attach(el) {
    if (el._uiHelpDone) return;
    el._uiHelpDone = true;
    var text = el.getAttribute('data-help');
    if (!text) return;
    el.setAttribute('role', el.getAttribute('role') || 'button');
    el.setAttribute('tabindex', el.getAttribute('tabindex') || '0');
    el.setAttribute('aria-label', el.getAttribute('aria-label') || 'Ayuda');
    el.addEventListener('click', function (e) { e.stopPropagation(); e.preventDefault(); showTip(el, text); });
    el.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); showTip(el, text); } });
  }

  function refresh() {
    var els = document.querySelectorAll('[data-help]');
    for (var i = 0; i < els.length; i++) attach(els[i]);
  }

  // Cerrar el tooltip al tocar afuera o hacer scroll/resize
  document.addEventListener('click', function (e) {
    if (popOwner && !e.target.closest('[data-help]')) hideTip();
  });
  window.addEventListener('scroll', hideTip, true);
  window.addEventListener('resize', hideTip);

  // ── Banner de idioma ────────────────────────────────────────────────────────
  function initLangBanner() {
    try {
      var lang = (navigator.language || navigator.userLanguage || 'es').toLowerCase();
      if (lang.indexOf('es') === 0) return;                 // ya está en español
      if (localStorage.getItem('langBannerDismissed')) return;
      var isPt = lang.indexOf('pt') === 0;
      var msg = isPt
        ? 'Este site está em espanhol. Use a tradução do seu navegador para lê-lo no seu idioma.'
        : 'This site is in Spanish — use your browser’s translate option to read it in your language.';
      var bar = document.createElement('div');
      bar.id = 'lang-hint-bar';
      var span = document.createElement('span');
      span.textContent = '🌐 ' + msg;
      var btn = document.createElement('button');
      btn.setAttribute('aria-label', 'Cerrar');
      btn.textContent = '✕';
      btn.addEventListener('click', function () {
        bar.remove();
        try { localStorage.setItem('langBannerDismissed', '1'); } catch (e) {}
      });
      bar.appendChild(span);
      bar.appendChild(btn);
      document.body.insertBefore(bar, document.body.firstChild);
    } catch (e) { /* noop */ }
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }
  ready(function () { injectCSS(); initLangBanner(); refresh(); });

  window.UIHelp = { refresh: refresh, hide: hideTip };
})();
