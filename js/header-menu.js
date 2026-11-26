/* Menú del header para pantallas angostas (lo cargan todas las páginas con #site-header).

   El header repite a mano el logo + 3 o 4 botones (.header-pill) en cada página. Debajo de
   ~360 px no entran: el header ensanchaba la página entera y todo lo demás (la grilla de
   equipos del index, por ejemplo) quedaba cortado en vez de reacomodarse. Acá, en esas
   pantallas, los botones se agrupan en uno solo (☰) que despliega la lista con sus nombres,
   y el logo se achica si hace falta. Arriba de 360 px no cambia nada, salvo que los botones
   no entren (por ejemplo el index con el ★ EURO de la rama eurotribunapp): ahí también se
   agrupan (clase .hm-compacto, se mide al cargar y al cambiar el tamaño de la ventana).

   Los estilos van inyectados desde acá para no tocar el CSS repetido de cada página. */
(function () {
  const header = document.getElementById('site-header');
  const acts = header && header.querySelector('.header-actions');
  if (!acts) return;
  const pills = [...acts.querySelectorAll('a.header-pill')];
  if (!pills.length) return;

  const css = document.createElement('style');
  css.textContent = `
    #site-header { position: relative; }
    #site-header .logo-wrap { min-width: 0; flex-shrink: 1; }
    #site-header .logo-wrap img { max-width: 100%; }
    .header-menu-btn { display: none; width: 38px; height: 38px; flex: 0 0 auto; border-radius: 10px; cursor: pointer;
      align-items: center; justify-content: center; color: rgba(255,255,255,0.85);
      background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.12); }
    .header-menu-btn svg { width: 18px; height: 18px; }
    .header-menu-btn[aria-expanded="true"] { background: rgba(79,195,247,0.16); border-color: rgba(79,195,247,0.45); color: #fff; }
    .header-menu-panel { display: none; position: absolute; right: 12px; top: calc(100% - 4px); z-index: 1500;
      min-width: 190px; max-width: calc(100vw - 24px); padding: 6px; border-radius: 12px;
      background: #151a2b; border: 1px solid rgba(255,255,255,0.12); box-shadow: 0 12px 30px rgba(0,0,0,0.55); }
    .header-menu-panel.open { display: block; }
    .header-menu-panel a { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px;
      color: rgba(255,255,255,0.88); text-decoration: none; font-family: 'Barlow Condensed', sans-serif;
      font-size: 16px; letter-spacing: 0.4px; }
    .header-menu-panel a:hover, .header-menu-panel a:active { background: rgba(79,195,247,0.14); color: #fff; }
    .header-menu-panel a svg { width: 17px; height: 17px; flex: 0 0 auto; color: var(--celeste, #4fc3f7); }
    @media (max-width: 359px) {
      #site-header { padding-left: 12px; padding-right: 12px; }
      #site-header .header-actions .header-pill { display: none !important; }
      .header-menu-btn { display: flex; }
    }
    /* Además, en cualquier ancho en que los botones no entren (ej. el index con el ★ EURO) */
    #site-header.hm-compacto .header-actions .header-pill { display: none !important; }
    #site-header.hm-compacto .header-menu-btn { display: flex; }
    .header-menu-panel a.euro { color: var(--euro, #ffd54f); }
    .header-menu-panel a.euro svg { color: var(--euro, #ffd54f); }`;
  document.head.appendChild(css);

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'header-menu-btn';
  btn.setAttribute('aria-label', 'Menú');
  btn.setAttribute('aria-expanded', 'false');
  btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
    + '<line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/></svg>';

  const panel = document.createElement('nav');
  panel.className = 'header-menu-panel';
  pills.forEach(p => {
    const a = document.createElement('a');
    a.href = p.getAttribute('href');
    if (p.classList.contains('euro')) a.className = 'euro';
    const ico = p.querySelector('svg');
    if (ico) a.appendChild(ico.cloneNode(true));
    const lbl = p.querySelector('.header-pill-label');
    a.appendChild(document.createTextNode((lbl ? lbl.textContent : p.textContent).trim()));
    panel.appendChild(a);
  });

  const cerrar = () => { panel.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); };
  btn.addEventListener('click', e => {
    e.stopPropagation();
    const abrir = !panel.classList.contains('open');
    panel.classList.toggle('open', abrir);
    btn.setAttribute('aria-expanded', String(abrir));
  });
  document.addEventListener('click', e => { if (!panel.contains(e.target)) cerrar(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') cerrar(); });
  // Modo compacto si los botones no entran: se mide con los botones visibles
  const medir = () => {
    header.classList.remove('hm-compacto');
    if (header.scrollWidth > header.clientWidth + 1) header.classList.add('hm-compacto');
    if (!header.classList.contains('hm-compacto') && window.innerWidth >= 360) cerrar();
  };
  let tMedir;
  window.addEventListener('resize', () => { clearTimeout(tMedir); tMedir = setTimeout(medir, 100); });
  window.addEventListener('load', medir);

  acts.appendChild(btn);
  header.appendChild(panel);
  medir();
})();
