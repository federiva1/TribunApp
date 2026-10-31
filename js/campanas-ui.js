(async function () {
  "use strict";
  const app = document.getElementById("campanas");
  const C = window.CampanasCore;
  const escape = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (character) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character],
    );
  const modes = {
    formation: {
      title: "Formación incompleta",
      image: "formation",
      description:
        "Reconstruí el once de tu equipo; si jugás con todos los clubes, completás ambos. Las ayudas reducen los puntos.",
    },
    scorers: {
      title: "Bonus goleadores",
      image: "scorers",
      description:
        "Con el resultado revelado, elegí quién hizo cada gol. Cada acierto suma una parte del bonus.",
    },
    result: {
      title: "Bonus resultado",
      image: "result",
      description:
        "Después de completar el once, recordá el marcador. Hasta 20 puntos extra; equivocarte no resta.",
    },
  };
  const routes = {
    express: { title: "Expreso", description: "Una selección corta para entrar en partido.", mark: "I" },
    classic: { title: "Clásico", description: "La mitad del camino, de principio a fin.", mark: "II" },
    complete: { title: "Completo", description: "Cada partido de la campaña, a tu ritmo.", mark: "III" },
  };
  let data, catalog = [], journeyIndex = [], loadingCollection = false, view = "library",
    teams,
    scope = new URLSearchParams(location.search).get("club") || "all",
    round = null;
  let tournamentScope = scope, medalClub = "all", medalState = "all", medalRoute = "complete";
  const storageError = () => {
    const notice = document.getElementById("storage-notice");
    notice.hidden = false;
    notice.textContent =
      "No pudimos guardar o recuperar el progreso de este navegador. Podés seguir jugando; los nuevos resultados se conservarán sólo mientras esta página siga abierta.";
  };
  let storage;
  try {
    storage = window.localStorage;
  } catch (_) {
    storageError();
    storage = {
      getItem: () => null,
      setItem: () => {
        throw new Error("No disponible");
      },
    };
  }
  const progress = window.CampanasProgress.open(storage, storageError);
  const profile = window.CampanasProgress.openProfile(storage, storageError);
  const activity = window.CampanasProgress.openActivity(storage, storageError);
  let selectedRoute = new URLSearchParams(location.search).get("route") || profile.get().route;
  if (!routes[selectedRoute]) selectedRoute = "express";
  const routeGames = () => C.routeMatches(data.matches, scope, selectedRoute);
  const routeStats = () => C.routeStatus(routeGames(), records(), data.id);
  const modeImage = (mode) => `<img class="mode-photo" src="assets/campanas/${modes[mode].image}.webp" alt="" width="768" height="432" loading="lazy">`;
  const profileNav = () => `<div class="profile-nav">${profile.get().nickname ? `<button class="back nickname" data-action="profile">${escape(profile.get().nickname)}</button>` : ""}${round ? "" : '<button class="primary" data-action="quick-play">Jugar →</button>'}<button class="archive-button" data-action="medals">Mis campañas ↗</button></div>`;
  const localNote = '<p class="local-note">Tu apodo, puntos y medallas se guardan en este navegador. No es una cuenta: usar el mismo apodo en otro dispositivo no recupera tu progreso.</p>';
  const crest = (slug, name, className = "") => {
    const match = data?.matches.find(m => m.homeSlug === slug || m.awaySlug === slug);
    const side = match?.homeSlug === slug ? "home" : "away";
    const external = match?.[side + "Crest"];
    const src = external && /^https:\/\/a\.espncdn\.com\//.test(external) ? external : `escudos/${slug}.png`;
    return `<img class="${className}" src="${escape(src)}" alt="${escape(name)}" width="40" height="46">`;
  };
  function showLibrary() {
    return loadCollection("apertura-2026", "library");
  }
  function historicalLibrary() {
    const clubs = [...new Map(catalog.map(item => [item.clubSlug, item.club])).entries()];
    return `<section id="historical-campaigns" class="historical-library" aria-label="Campañas históricas" tabindex="-1"><div class="club-picker"><div><span class="eyebrow">LAS QUE NO TE OLVIDÁS</span><h2>Campañas históricas</h2><p class="muted">12 clubes. 24 historias. ¿Cuál vas a revivir?</p></div><label>Club <select id="history-club"><option value="all">Todos los clubes</option>${clubs.map(([slug,name])=>`<option value="${escape(slug)}">${escape(name)}</option>`).join("")}</select></label></div><div class="club-campaign-grid">${clubs.map(([slug,name])=>`<article class="club-campaign-card" data-club="${escape(slug)}"><div class="club-card-head">${crest(slug,name)}<h3>${escape(name)}</h3></div><div class="club-campaign-links">${catalog.filter(item=>item.clubSlug===slug).map(item=>`<button class="historical-card" data-collection="${escape(item.id)}"><strong>${escape(item.title.split(" · ").slice(1).join(" · "))}</strong><small>${item.matchCount} partidos <b aria-hidden="true">→</b></small></button>`).join("")}</div></article>`).join("")}</div></section>`;
  }
  async function loadCollection(id, target = "setup", nextScope) {
    if (loadingCollection) return;
    const item = catalog.find(c=>c.id===id);
    if (id !== "apertura-2026" && !item) return;
    loadingCollection = true;
    try {
      const response = await fetch(item?.file || "data/campanas/apertura-2026.json");
      if (!response.ok) throw new Error("No se pudo cargar la campaña");
      const next = await response.json();
      if (!next.matches?.length) throw new Error("Campaña sin partidos");
      data = next;
      const bySlug = new Map();
      data.matches.forEach(match => ["home", "away"].forEach(side => bySlug.set(match[side+"Slug"],match[side])));
      teams = [...bySlug].map(([slug,name])=>({slug,name})).sort((a,b)=>a.name.localeCompare(b.name,"es"));
      scope = data.clubSlug || nextScope || tournamentScope;
      if (!teams.some(team=>team.slug===scope)) scope="all";
      if (!data.clubSlug) tournamentScope = scope;
      view = target === "play" ? "setup" : target;
      updateUrl();
      showHome();focusMain();
      if (target === "play") start();
    } catch(error) {
      if (!data) throw error;
      showHome();
      const notice = document.createElement("p");notice.className="notice bad";notice.setAttribute("role","alert");notice.textContent="No pudimos cargar esa campaña. Volvé a intentarlo; tu progreso está guardado.";app.prepend(notice);
    } finally { loadingCollection=false; }
  }
  const records = () =>
    C.progressForClub(progress.list(), scope)
      .filter(
        (entry) =>
          entry.collectionId === data.id &&
          data.matches.some((match) => match.id === entry.matchId),
      );
  const scoped = () =>
    data.matches.filter(
      (match) => scope === "all" || match.homeSlug === scope || match.awaySlug === scope,
    );
  const scopeName = () => teams.find((team) => team.slug === scope)?.name || "Todos los equipos";
  function focusMain() {
    app.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  function updateUrl() {
    const url = new URL(location.href);
    if (view === "library") { url.searchParams.delete("collection"); url.searchParams.delete("route"); }
    else { url.searchParams.set("collection", data.id); url.searchParams.set("route", selectedRoute); }
    if (!data.clubSlug && scope !== "all") url.searchParams.set("club",scope);
    else url.searchParams.delete("club");
    history.replaceState(null,"",url);
  }
  function clubSelect() {
    return `<label><span class="eyebrow">EQUIPO</span><select id="club-select" aria-label="Equipo"><option value="all">Todos los equipos</option>${teams.map(team=>`<option value="${escape(team.slug)}" ${scope===team.slug?"selected":""}>${escape(team.name)}</option>`).join("")}</select></label>`;
  }
  function showHome() {
    round = null;
    if (view !== "library") return showSetup();
    app.innerHTML = `<div class="section-bar"><span class="eyebrow">CAMPAÑAS TRIBUNAPP</span>${profileNav()}</div>
      <section class="hero"><div><h1>¿Cuánto sabés<br>de <span>fútbol argentino?</span></h1><div class="hero-tags"><span class="tag">30 CLUBES</span><a class="tag tag-link" href="#historical-campaigns">24 CAMPAÑAS HISTÓRICAS</a><span class="tag">FORMACIÓN + BONUS</span></div></div><div class="crest-wall" aria-label="Los 30 clubes del torneo">${teams.map(team=>crest(team.slug,team.name)).join("")}</div></section>
      <section class="mode-intro" aria-label="Cómo se juega"><div class="club-picker"><div><span class="eyebrow">UN PARTIDO, PASO A PASO</span><h2>Armá el once. Sumá con los bonus.</h2><p class="muted">La formación hace avanzar tu campaña. Después, resultado y goleadores son opcionales.</p></div></div><div class="mode-grid">${Object.entries(modes).sort(([a],[b])=>["formation","result","scorers"].indexOf(a)-["formation","result","scorers"].indexOf(b)).map(([mode,info],index)=>`<article class="mode-card mode-explainer">${modeImage(mode)}<div class="mode-body"><span class="eyebrow">${index===0?"01 · EL DESAFÍO":"0"+(index+1)+" · BONUS OPCIONAL"}</span><h3>${info.title}</h3><p>${info.description}</p></div></article>`).join("")}</div></section>
      <section id="tournaments" class="tournament-library" aria-label="Torneos argentinos"><div class="club-picker"><div><span class="eyebrow">EMPEZÁ POR ACÁ</span><h2>Torneos argentinos</h2></div></div><div class="tournament-card"><div><span class="eyebrow">255 PARTIDOS · 30 CLUBES</span><h3>Apertura 2026</h3><p class="muted">Seguí a tu equipo o recorré el torneo entero.</p><span class="tag">EXPRESO · CLÁSICO · COMPLETO</span></div><div class="tournament-choice">${clubSelect()}<button class="primary" data-collection="apertura-2026">Elegir recorrido →</button></div></div></section>
      ${historicalLibrary()}${localNote}`;
  }
  function showSetup() {
    view = "setup";
    const stats = routeStats();
    app.innerHTML = `<div class="section-bar"><button class="back" data-action="library">← Todas las campañas</button>${profileNav()}</div>
      <section class="hero campaign-hero"><div><span class="eyebrow">ELEGÍ TU RECORRIDO</span><h1>${escape(data.title)}</h1>${data.clubSlug ? "" : `<p>${escape(data.description)}</p>`}<div class="hero-tags"><span class="tag">${C.routeMatches(data.matches,scope,"complete").length} PARTIDOS JUGABLES</span><span class="tag">${escape(scopeName())}</span></div></div>${data.clubSlug ? crest(data.clubSlug,data.club,"campaign-crest") : ""}</section>
      ${data.clubSlug ? "" : `<div class="club-picker"><p class="muted">Jugá con tu club o con todos los equipos.</p>${clubSelect()}</div>`}
      <section aria-label="Recorrido"><div class="club-picker"><div><span class="eyebrow">01 · A TU RITMO</span><h2>¿Cuánto querés jugar?</h2></div></div><div class="route-grid">${Object.keys(routes).map(key=>`<button class="route-card" data-route="${key}" aria-pressed="${selectedRoute===key}"><strong>${C.routeMatches(data.matches,scope,key).length}</strong> <span>partidos</span></button>`).join("")}</div></section>
      <div class="route-status ${stats.complete?"earned":""}" role="status"><strong>${stats.complete?"✓ Recorrido completado":routes[selectedRoute].title+" · "+stats.done+" de "+stats.total+" partidos"}</strong><span>Completá la formación de cada partido para ganar la medalla. Los bonus suman puntos extra.</span></div>
      <section class="campaign-start"><div><span class="eyebrow">02 · A LA CANCHA</span><h2>${stats.complete?"Recorrido completo":"Tu próximo partido"}</h2><p class="muted">Primero, el once. Después, bonus opcionales de resultado y goleadores.</p></div><div class="campaign-start-actions"><button class="primary" data-action="campaign-play">${stats.complete?"Ver mis partidos":stats.done?"Continuar campaña":"Empezar campaña"} →</button><button class="back" data-action="archive">Mi archivo ↗</button></div></section>
      ${localNote}`;
  }
  function showQuickPlay() {
    const recent = activity.list().find(item=>journeyIndex.some(c=>c.id===item.collectionId));
    const current = view === "setup" ? {collectionId:data.id,club:scope,route:selectedRoute}
      : recent;
    const remembered=journeyIndex.find(item=>item.id===current?.collectionId);
    let kind=remembered&&!remembered.clubSlug?"tournament":"history",
      historyClub=remembered?.clubSlug||"", historyCollection=remembered?.clubSlug?remembered.id:"",
      tournamentClub=current?.club||tournamentScope, route=routes[current?.route]?current.route:selectedRoute;
    let dialog=document.getElementById("quick-play-dialog");
    if(dialog) dialog.remove();
    dialog=document.createElement("dialog");dialog.id="quick-play-dialog";dialog.className="quick-play-dialog";
    dialog.setAttribute("aria-labelledby","quick-play-title");
    const tournament=journeyIndex.find(c=>c.id==="apertura-2026");
    const clubNames=[...new Map(tournament.matches.flatMap(m=>[[m.homeSlug,m.home],[m.awaySlug,m.away]])).entries()].sort((a,b)=>a[1].localeCompare(b[1],"es"));
    const historyClubs=[...new Map(catalog.map(item=>[item.clubSlug,{name:item.club,short:item.title.split(" · ")[0]}])).entries()];
    if(!clubNames.some(([slug])=>slug===tournamentClub)) tournamentClub="all";
    dialog.innerHTML=`<form id="quick-play-form"><div class="dialog-heading"><span class="eyebrow">DIRECTO A LA CANCHA</span><button type="button" class="back" data-close-quick aria-label="Cerrar">✕</button></div><h2 id="quick-play-title">¿Qué jugamos?</h2><div class="quick-kinds" role="group" aria-label="Tipo de campaña"><button type="button" data-quick-kind="history">Campañas históricas</button><button type="button" data-quick-kind="tournament">Apertura 2026</button></div><div id="quick-choices"></div><button class="primary quick-submit">Jugar →</button></form>`;
    document.body.append(dialog);
    const selection=()=>({id:kind==="history"?historyCollection:tournament.id,club:kind==="history"?historyClub:tournamentClub});
    const clubButton=(slug,name,short,selected)=>`<button type="button" class="quick-club" data-quick-club="${escape(slug)}" aria-label="${escape(name)}" aria-pressed="${selected}">${slug==="all"?'<span class="quick-all" aria-hidden="true">30</span>':`<img src="escudos/${escape(slug)}.png" alt="" width="32" height="36">`}<span>${escape(short)}</span></button>`;
    const refresh=(focusSelector)=>{
      const {id,club}=selection(),item=journeyIndex.find(c=>c.id===id);
      dialog.querySelectorAll("[data-quick-kind]").forEach(button=>button.setAttribute("aria-pressed",button.dataset.quickKind===kind));
      const clubs=kind==="history"?historyClubs.map(([slug,{name,short}])=>clubButton(slug,name,short,slug===historyClub)).join("")
        :clubButton("all","Todos los equipos","Todos",tournamentClub==="all")+clubNames.map(([slug,name])=>clubButton(slug,name,historyClubs.find(([key])=>key===slug)?.[1].short||name,slug===tournamentClub)).join("");
      const campaigns=kind==="history"&&historyClub?`<fieldset class="quick-section"><legend>Campaña de ${escape(historyClubs.find(([slug])=>slug===historyClub)[1].short)}</legend><div class="quick-campaigns">${catalog.filter(c=>c.clubSlug===historyClub).map(c=>`<button type="button" data-quick-collection="${escape(c.id)}" aria-pressed="${historyCollection===c.id}">${escape(c.title.split(" · ").slice(1).join(" · "))}</button>`).join("")}</div></fieldset>`:"";
      dialog.querySelector("#quick-choices").innerHTML=`<fieldset class="quick-section"><legend>Club</legend><div class="quick-clubs ${kind==="tournament"?"tournament-clubs":""}">${clubs}</div></fieldset>${campaigns}${item?`<fieldset class="quick-section"><legend>¿Cuántos partidos?</legend><div class="quick-routes">${Object.keys(routes).map(key=>`<button type="button" data-quick-route="${key}" aria-pressed="${route===key}"><strong>${C.routeMatches(item.matches,club,key).length}</strong><span>partidos</span></button>`).join("")}</div></fieldset>`:""}`;
      dialog.querySelector(".quick-submit").disabled=!item;
      if(focusSelector) dialog.querySelector(focusSelector)?.focus({preventScroll:true});
    };
    dialog.querySelector("form").addEventListener("click",event=>{
      const button=event.target.closest("button");if(!button)return;
      if(button.dataset.quickKind) {kind=button.dataset.quickKind;return refresh();}
      if(button.dataset.quickClub) {
        if(kind==="history") {
          if(historyClub!==button.dataset.quickClub) historyCollection="";
          historyClub=button.dataset.quickClub;
        } else tournamentClub=button.dataset.quickClub;
        return refresh(`[data-quick-club="${CSS.escape(button.dataset.quickClub)}"]`);
      }
      if(button.dataset.quickCollection) {historyCollection=button.dataset.quickCollection;return refresh(`[data-quick-collection="${CSS.escape(historyCollection)}"]`);}
      if(button.dataset.quickRoute) {route=button.dataset.quickRoute;return refresh(`[data-quick-route="${route}"]`);}
    });
    dialog.querySelector("[data-close-quick]").addEventListener("click",()=>dialog.close());
    dialog.querySelector("form").addEventListener("submit",event=>{
      event.preventDefault();
      const {id,club}=selection();if(!journeyIndex.some(c=>c.id===id))return;
      selectedRoute=route;
      dialog.close();loadCollection(id,"play",club);
    });
    refresh();dialog.showModal();dialog.querySelector(`[data-quick-kind="${kind}"]`).focus();
  }
  let pendingStart = null, profileReturnFocus = null;
  function askNickname(next) {
    pendingStart = next;
    profileReturnFocus = document.activeElement;
    let dialog = document.getElementById("nickname-dialog");
    if (!dialog) {
      dialog = document.createElement("dialog");dialog.id="nickname-dialog";dialog.className="nickname-dialog";
      dialog.setAttribute("aria-labelledby","nickname-title");
      dialog.innerHTML='<form id="nickname-form"><span class="eyebrow">TU LUGAR EN LA TRIBUNA</span><h2 id="nickname-title">¿Cómo te llamamos?</h2><p class="muted">Elegí un apodo para tu medallero. Sin email ni contraseña.</p><label for="nickname-input">Tu apodo</label><input id="nickname-input" name="nickname" maxlength="24" required autocomplete="nickname" placeholder="Ej. Fede del Bicho"><p class="local-note">Se guarda en este navegador. No crea una cuenta ni sincroniza otros dispositivos. Tu progreso anterior se conserva.</p><div class="dialog-actions"><button type="button" class="secondary" id="nickname-cancel">Volver</button><button class="primary">Guardar y seguir →</button></div></form>';
      document.body.append(dialog);
      dialog.querySelector("#nickname-cancel").addEventListener("click",()=>{ pendingStart=null;dialog.close(); });
      dialog.addEventListener("cancel",()=>{pendingStart=null;});
      dialog.addEventListener("close",()=>{profileReturnFocus?.focus({preventScroll:true});});
      dialog.querySelector("form").addEventListener("submit",event=>{
        event.preventDefault();
        const input=dialog.querySelector("input");
        if (!input.value.trim()) {input.setCustomValidity("Escribí un apodo.");input.reportValidity();return;}
        profile.save({nickname:input.value});
        const next=pendingStart;pendingStart=null;dialog.close();
        if(next) next(); else if(view==="medals") showMedals(); else if(round) renderRound(); else showHome();
      });
      dialog.querySelector("input").addEventListener("input",event=>event.target.setCustomValidity(""));
    }
    dialog.querySelector("input").value=profile.get().nickname;
    dialog.showModal();dialog.querySelector("input").focus();
  }
  function start(matchId, bothTeams = false) {
    if (!profile.get().nickname) return askNickname(()=>start(matchId,bothTeams));
    profile.save({route:selectedRoute,mode:"formation"});
    const seen=records(), options=C.eligible(matchId?scoped():routeGames(),scope,"formation");
    const chosen=matchId ? options.find(m=>m.id===matchId) : options.find(m=>!seen.some(e=>e.matchId===m.id&&e.mode==="formation"));
    if(!chosen) return showArchive();
    const formationSides=C.formationSides(chosen,bothTeams?"all":scope);
    const existing=seen.filter(e=>e.matchId===chosen.id), saved=existing.find(e=>e.mode==="formation" && (!bothTeams || !e.formationClub || e.formationClub==="all"));
    const teamGames=new Set(seen.filter(e=>e.mode==="formation").map(e=>e.matchId)).size;
    activity.start(data.id,scope,selectedRoute,"formation");
    round={mode:"formation",match:chosen,points:saved?Math.max(0,saved.bestScore):0,solved:new Set(),hints:{},selected:[],eliminated:new Set(),scorerHints:0,
      completed:!!saved,correct:saved?true:null,saved,formationSides,formationTotal:formationSides.reduce((n,side)=>n+chosen[side+"XI"].length,0),
      showRival:false,rivalSeen:false,hideNumbers:scope!=="all"&&teamGames>=2,
      resultRevealed:false,
      scores:Object.fromEntries(existing.map(e=>[e.mode,Math.max(0,e.bestScore)]))};
    if(saved) for(const side of formationSides) chosen[side+"XI"].forEach((p,i)=>round.solved.add(playerKey(side,i)));
    app.innerHTML="";renderRound();focusMain();
  }
  const matchPoints = () => round.points + Object.entries(round.scores).filter(([mode])=>mode!==round.mode).reduce((n,[,points])=>n+points,0);
  function beginBonus(mode) {
    if(!round.completed || !pending(round.match).includes(mode) || mode==="formation") return;
    round.mode=mode;round.points=0;round.completed=false;round.correct=null;round.saved=null;round.skipped=false;
    round.selected=[];round.eliminated=new Set();round.scorerHints=0;round.scorerResult=null;
    if(mode==="scorers") round.resultRevealed=true;
    renderRound();focusMain();
  }
  function skipResult() {
    if(!round || !((round.completed&&pending(round.match).includes("result")) || (round.mode==="result"&&!round.completed))) return;
    round.mode="result";round.points=0;round.completed=false;complete(false,true);
    if(pending(round.match).includes("scorers")) beginBonus("scorers");
    else renderRound("Resultado revelado. Conservás todos los puntos de tu formación.");
  }
  function revealResult() {
    if(!round || round.mode!=="formation" || round.resultRevealed) return;
    // Revealing the score resolves only that bonus, never the unfinished lineup.
    const existing=collectionRecords().find(e=>e.matchId===round.match.id&&e.mode==="result");
    const entry=existing || progress.save(data.id,round.match.id,"result",0,data.version,scope,"all",{skipped:true,flowVersion:2});
    round.scores.result=Math.max(0,entry.bestScore);
    round.resultRevealed=true;
    renderRound("Resultado revelado. No suma ni resta puntos. "+(round.completed?"Podés seguir con el bonus de goleadores si está disponible.":"Seguí completando la formación; después vienen los bonus pendientes."));
  }
  const playerKey = (side, index) => `${side}-${index}`;
  const playerName = (player) => player.accepted_answers?.[0] || player.name;
  const hiddenNumber = (player) => round.hideNumbers && player.n != null && player.n !== "";
  const collectionRecords = () => progress.list().filter(e=>e.collectionId===data.id);
  const pending = (match) => C.pendingModes(match, records(), collectionRecords());
  function bonusButtons(match) {
    const next=pending(match)[0];
    if(next==="result") return `<div class="bonus-offer"><p>Tu formación ya cuenta. ¿Sumamos puntos extra?</p><div class="completion-actions"><button class="primary" data-bonus="result">Bonus resultado · hasta +20</button><button class="back" data-action="skip-result">${C.eligible([match],"all","scorers").length?"Omitir resultado e ir a goleadores →":"Ver resultado · 0 puntos"}</button></div></div>`;
    if(next==="scorers") return '<div class="bonus-offer"><p>La planilla está completa. Ahora podés sumar con los autores de los goles.</p><button class="primary" data-bonus="scorers">Jugar bonus goleadores · hasta +20</button></div>';
    if(records().some(e=>e.matchId===match.id&&e.mode==="scorers")) return '<p class="muted">Ya jugaste el bonus de goleadores de este partido. Tus puntos están guardados.</p>';
    return `<p class="muted">${round.resultRevealed&&!match.scorers.length?"Este partido terminó sin goles: no tiene bonus de goleadores.":"No hay bonus de goleadores disponible para esta ficha."}</p>`;
  }
  function stageTrail() {
    const played=records().filter(e=>e.matchId===round.match.id);
    return `<ol class="stage-trail" aria-label="Etapas del partido">${["formation","result","scorers"].map((mode,i)=>{
      const entry=played.find(e=>e.mode===mode), exposed=mode==="result"&&C.resultRevealed(round.match,collectionRecords())&&!entry, unavailable=mode==="scorers"&&round.resultRevealed&&!C.eligible([round.match],"all","scorers").length;
      return `<li class="${round.mode===mode?"active ":""}${entry||exposed?"done":""} ${unavailable?"unavailable":""}" ${round.mode===mode?'aria-current="step"':""}><span class="stage-number" aria-hidden="true">${entry||exposed?"✓":i+1}</span><span>${mode==="formation"?"Formación":mode==="result"?"Resultado":"Goleadores"}<small>${unavailable?(round.match.scorers.length?"No disponible":"Sin goles"):exposed?"Ya jugado":entry?.skipped?"Revelado · 0 pts":entry?"Jugado":mode==="formation"?"Avance de campaña":"Bonus opcional"}</small></span></li>`;
    }).join("")}</ol>`;
  }
  function completionPanel(status) {
    if(!round.completed) return "";
    const title=round.mode==="formation"?"Planilla completa":round.skipped?"Bonus omitido":round.mode==="scorers"&&!round.correct?`${round.scorerResult?.matched||0} de ${round.match.scorers.length} goles acertados`:round.correct?"¡Lo tenías guardado!":"Esta vez no sumaste bonus";
    const hasBonus=pending(round.match).length>0;
    return `<section tabindex="-1" class="completion ${round.correct?"success":"neutral"}"><h2>${title}</h2><p><strong>+${round.points} puntos</strong> ${round.mode==="formation"?"por la formación":"en este bonus"}. Total del partido: <strong>${matchPoints()} puntos</strong>.</p><div class="points-breakdown">${["formation","result","scorers"].filter(mode=>Object.hasOwn(round.scores,mode)).map(mode=>`<span>${mode==="formation"?"Formación":mode==="result"?"Resultado":"Goleadores"} <b>${round.scores[mode]} pts</b></span>`).join("")}</div>${round.mode==="scorers"?`<p class="goal-summary">Goleadores: ${escape(round.match.scorers.join(", "))}.</p>`:""}${status.complete?`<p class="medal-earned">✓ Completaste ${routes[selectedRoute].title}. Los bonus siguen siendo opcionales.</p>`:""}${bonusButtons(round.match)}<div class="completion-actions">${hasBonus?'<button class="back" data-action="skip-bonuses">Continuar sin los bonus pendientes →</button>':`<button class="primary" data-action="next">${status.complete?"Ver mi medalla":"Siguiente partido"} →</button>`}</div></section>`;
  }
  function playerRow(player, side, index, reference = false) {
    const key = playerKey(side, index),
      solved = round.solved.has(key),
      level = round.hints[key];
    player = { ...player, name: playerName(player) };
    const number = !reference && hiddenNumber(player) && level === undefined && !solved ? "—" : (player.n ?? "—");
    const letterHint = level === undefined || (hiddenNumber(player) && level === 0)
      ? "" : mask(player.name, Math.max(0, level - (hiddenNumber(player) ? 1 : 0)));
    return `<li class="player-row ${solved ? "solved" : ""}" data-player="${key}"><span class="shirt-number">${escape(number)}</span>${reference || solved || round.mode !== "formation" ? `<span class="player-name">${escape(player.name)}</span>${solved ? '<span class="solved-mark">✓</span>' : ""}` : `<form data-player-form="${key}"><div class="entry-wrap"><label class="sr-only" for="guess-${key}">Apellido del jugador ${index + 1} de ${escape(side === "home" ? round.match.home : round.match.away)}</label><input id="guess-${key}" name="answer" class="${letterHint ? "hint-placeholder" : ""}" placeholder="${escape(letterHint || "Apellido del jugador")}" title="${escape(letterHint || "Apellido del jugador")}" aria-label="Apellido del jugador ${index + 1}${letterHint ? `, pista: ${escape(letterHint)}` : ""}" autocomplete="off" autocapitalize="words" spellcheck="false" required></div><button class="check-answer" aria-label="Comprobar jugador ${index + 1}" title="Comprobar">✓</button></form><button class="player-hint" data-hint="${key}" title="Pedir una pista para este jugador" aria-label="Pista para jugador ${index + 1}">?</button>`}</li>`;
  }
  function mask(name, count) {
    const letters = [...name],
      positions = letters
        .map((letter, index) => (/[\p{L}\p{N}]/u.test(letter) ? index : -1))
        .filter((index) => index >= 0),
      order = [];
    while (positions.length) {
      order.push(positions.shift());
      if (positions.length) order.push(positions.pop());
    }
    const visible = new Set(order.slice(0, count));
    return letters
      .map((letter, index) => (!/[\p{L}\p{N}]/u.test(letter) || visible.has(index) ? letter : "_"))
      .join(" ");
  }
  function scorerRow(candidate) {
    candidate = { ...candidate, name: playerName(candidate) };
    const count = round.selected.filter((id) => id === candidate.id).length,
      actual = C.actualScorers(round.match).filter((id) => id === candidate.id).length;
    return `<li class="player-row ${round.eliminated.has(candidate.id) && !round.completed ? "eliminated" : ""} ${round.completed && actual ? "goal-correct" : round.completed && count ? "goal-wrong" : ""}"><span class="shirt-number">${escape(candidate.n ?? "—")}</span><button class="goal-pick ${count ? "selected" : ""}" data-goal="${escape(candidate.id)}" ${round.completed ? "disabled" : ""}><span class="player-name">${escape(candidate.name)}</span><b>${round.completed ? (actual ? `⚽ ×${actual}` : count ? "✕" : "") : count ? `⚽ ×${count}` : "+"}</b></button>${count && !round.completed ? `<button class="undo-goal" data-undo="${escape(candidate.id)}" aria-label="Quitar un gol de ${escape(candidate.name)}">−</button>` : ""}</li>`;
  }
  function sheet(side, reference = false) {
    const match = round.match,
      name = match[side],
      slug = match[side + "Slug"],
      players = match[side + "XI"];
    let body = C.orderedLineup(players).map(({player, index}) => playerRow(player, side, index, reference)).join("");
    if (round.mode === "result" && match.availability?.formation === false)
      body = '<li class="player-row muted">La formación completa no está disponible en esta ficha. Podés jugar a recordar el resultado.</li>';
    if (round.mode === "scorers") {
      const candidates = C.orderedLineup(C.scorerCandidates(match).filter((player) => player.team === name)).map(row=>row.player);
      body = candidates
        .filter((player) => !player.substitute && !player.rosterUnknown)
        .map(scorerRow)
        .join("");
      const subs = candidates.filter((player) => player.substitute),
        others = candidates.filter((player) => player.rosterUnknown);
      const substituteScored = C.scorerCandidates(match).some(player => player.substitute && C.actualScorers(match).includes(player.id));
      if (subs.length && substituteScored)
        body += `<li class="sub-heading">SUPLENTES</li>${subs.map(scorerRow).join("")}`;
      if (others.length)
        body += `<li class="sub-heading">OTROS JUGADORES DE LA FICHA</li>${others.map(scorerRow).join("")}`;
    }
    return `<section class="team-sheet"><div class="sheet-title">${crest(slug, "")}<h2>${escape(name)}</h2><span>${reference ? "REFERENCIA" : round.mode === "scorers" ? "PLANILLA" : "ONCE INICIAL"}</span></div><ol class="player-list">${body}</ol></section>`;
  }
  function formationSheets() {
    if (round.mode !== "formation" || round.formationSides.length === 2) return `<div class="sheets">${sheet("home")}${sheet("away")}</div>`;
    const side=round.formationSides[0], rival=side==="home"?"away":"home";
    const showcase=round.match.id==="espn-528144" && !round.completed && !round.solved.size && !Object.keys(round.hints).length && !round.rivalSeen;
    return `<div class="lineup-toolbar"><span class="muted">Tu once · ${escape(round.match[side])}</span><div><button class="secondary" data-action="toggle-rival" aria-expanded="${round.showRival}" aria-controls="rival-sheet">${round.showRival?"Ocultar rival":"Ver rival"}</button>${showcase?'<button class="text-button" data-action="both-teams">Final de Madrid: jugar ambos once →</button>':""}</div></div><div class="sheets ${round.showRival?"with-rival":"single-team"}">${sheet(side)}<div id="rival-sheet" ${round.showRival?"":"hidden"}>${round.showRival?sheet(rival,true):""}</div></div>${round.showRival?'<p class="rival-note muted">El rival es una referencia: no tenés que completarlo ni consume ayudas o puntos.</p>':""}`;
  }
  function renderRound(message = "", tone = "") {
    const match = round.match,
      info = modes[round.mode];
    const drafts = {};
    app.querySelectorAll("[data-player-form] input").forEach((input) => {
      drafts[input.id] = input.value;
    });
    const activeId = document.activeElement?.id;
    const activeButton = document.activeElement?.closest("button");
    const focusAction = activeButton
      ? ["hint", "goal", "undo", "action"]
          .map((key) => [key, activeButton.dataset[key]])
          .find(([, value]) => value !== undefined)
      : null;
    const rules =
      round.mode === "formation"
        ? `Completá ${round.formationSides.length===1 ? `los ${round.formationTotal} apellidos de ${escape(match[round.formationSides[0]])}` : "los dos once: 22 apellidos"}. Sin ayuda: 3 puntos por jugador; primera ayuda: 2; segunda: 1; desde la tercera: 0. También vale 0 si se revelan dos letras o la mitad del apellido. Equivocarte no resta. ${round.hideNumbers ? "Desde tu tercer partido con este club, la primera pista revela el dorsal, si está disponible." : "Tocá ? al lado de un jugador para pedir una pista."}`
        : round.mode === "scorers"
          ? "Tocá un jugador una vez por cada gol. Cada gol acertado suma una parte de los 20 puntos; con ayudas, el máximo baja a 14, 8 o 0. Equivocarte no resta."
          : "Recordá el marcador final (incluye alargue, no la tanda de penales). Exacto: +20 puntos. Si no acertás, el bonus vale 0.";
    const status = routeStats();
    const newlyCompleted=round.completed&&!app.querySelector(".completion");
    app.innerHTML = `<div class="section-bar"><button class="back" data-action="home">← Volver a la campaña</button>${profileNav()}</div><div class="game-top"><div><span class="eyebrow">${escape(data.title)} · ${escape(scopeName())}</span><h1>${info.title}</h1></div><div class="points" aria-label="Puntos de esta partida">${matchPoints()} pts · partido</div></div>
      <div class="journey-strip"><span>${routes[selectedRoute].title} · ${status.done} / ${status.total} partidos terminados${status.complete ? " · ✓ Medalla obtenida" : ""}</span><button class="back" data-action="archive">Mi archivo ↗</button></div>
      ${stageTrail()}<section class="match-board" aria-label="Partido"><p class="match-date">${escape(match.date)}</p><div class="scoreboard"><div class="score-team">${crest(match.homeSlug, "")}<span>${escape(match.home)}</span></div><strong class="score-value">${round.resultRevealed ? escape(match.score) : "? — ?"}</strong><div class="score-team away">${crest(match.awaySlug, "")}<span>${escape(match.away)}</span></div></div>${round.mode==="formation"&&!round.resultRevealed?'<button class="reveal-result" data-action="reveal-result">Ver resultado <span>· sin puntos por este bonus</span></button>':""}<p class="venue">${escape(match.stadium)}${round.resultRevealed ? ` · ${escape(match.zone)}` : ""}</p></section>
      <p class="rules-strip">${rules}</p>
      ${round.mode === "result" && !round.completed ? `<form id="result-form" class="result-form"><div class="result-inputs"><label><span>${escape(match.home)}</span><input name="home" type="number" inputmode="numeric" min="0" max="99" step="1" required aria-label="Goles de ${escape(match.home)}"></label><span class="result-separator" aria-hidden="true">—</span><label><span>${escape(match.away)}</span><input name="away" type="number" inputmode="numeric" min="0" max="99" step="1" required aria-label="Goles de ${escape(match.away)}"></label></div><button class="primary">Confirmar resultado</button></form>` : ""}
      <p class="notice ${tone}" id="game-message" role="status" aria-live="polite">${escape(message || (round.mode === "formation" ? `${round.solved.size} / ${round.formationTotal} apellidos encontrados` : round.mode === "scorers" ? `${round.selected.length} / ${match.scorers.length} goles elegidos` : "Tu formación ya está completa. Este bonus es opcional."))}</p>
      ${completionPanel(status)}
      ${round.mode==="result"?"":formationSheets()}
      ${round.completed?"":`<div class="game-actions">${round.mode === "scorers" ? `<button class="secondary" data-action="scorer-hint" ${C.scorerHintPlan(match,round.eliminated,round.scorerHints).length?"":"disabled"}>? Ayuda (${round.scorerHints}/3)</button><span class="muted">Bonus máximo: ${C.scoreScorers(C.actualScorers(match),match,round.scorerHints).score} puntos</span><button class="primary" data-action="confirm-scorers" ${round.selected.length!==match.scorers.length?"disabled":""}>Confirmar goleadores</button>`:round.mode==="formation"?`<span class="muted">${round.solved.size} / ${round.formationTotal} apellidos</span>`:'<button class="back" data-action="skip-result">Omitir bonus y revelar resultado →</button>'}<button class="secondary" data-action="next">${round.mode==="formation"?"Saltar partido":"Siguiente partido"} →</button></div>`}`;
    for (const [id, value] of Object.entries(drafts)) {
      const input = document.getElementById(id);
      if (input) input.value = value;
    }
    if (activeId && document.getElementById(activeId))
      document.getElementById(activeId).focus({ preventScroll: true });
    else if (focusAction) {
      const [key, value] = focusAction;
      const target = [...app.querySelectorAll("button")].find(
        (button) =>
          button.dataset[key] === value && !button.disabled && !button.closest(".eliminated"),
      );
      (target || app.querySelector(".completion button") || app).focus({ preventScroll: true });
    }
    if(newlyCompleted) {
      const panel=app.querySelector(".completion");panel.focus({preventScroll:true});panel.scrollIntoView({block:"start"});
    }
  }
  function complete(correct, skipped = false) {
    if (round.completed) return;
    round.completed = true;
    round.correct = correct;
    round.skipped = skipped;
    round.scores[round.mode] = round.points;
    if(round.mode!=="formation") round.resultRevealed=true;
    const formationClub=round.formationSides.length===1?round.match[round.formationSides[0]+"Slug"]:"all";
    round.saved = progress.save(data.id, round.match.id, round.mode, round.points, data.version, scope, formationClub, {skipped,flowVersion:2});
  }
  function activePlayer(key) {
    const [side,index]=key.split("-");
    return round.mode==="formation" && round.formationSides.includes(side) && /^\d+$/.test(index) && Number(index)<round.match[side+"XI"].length;
  }
  function getPlayer(key) {
    const [side, index] = key.split("-");
    return round.match[side + "XI"][Number(index)];
  }
  function hint(key) {
    if (round.completed || !activePlayer(key) || round.solved.has(key)) return;
    const raw = getPlayer(key),
      player = { ...raw, name: playerName(raw) },
      level = round.hints[key] === undefined ? 0 : round.hints[key] + 1;
    round.hints[key] = level;
    const letterCount = [...player.name].filter((letter) => /[\p{L}\p{N}]/u.test(letter)).length;
    if (level >= letterCount + (hiddenNumber(player) ? 1 : 0)) {
      round.solved.add(key);
      if (round.solved.size === round.formationTotal) complete(true);
      renderRound(`${player.name} quedó revelado. No suma puntos.`, "");
    } else
      renderRound(
        hiddenNumber(player) && level === 0
          ? `Revelamos el dorsal ${player.n}.`
          : `Pista para este jugador. Este apellido ahora vale ${C.pointsForPlayer(level, player.name, hiddenNumber(player))} puntos.`,
        "",
      );
    document.getElementById(`guess-${key}`)?.focus({ preventScroll: true });
  }
  function scorerHint() {
    if (round.completed || round.scorerHints >= 3) return;
    const removed = C.scorerHintPlan(round.match, round.eliminated, round.scorerHints);
    if (!removed.length) return;
    round.scorerHints++;
    removed.forEach((id) => round.eliminated.add(id));
    if (!C.scorerHintPlan(round.match, round.eliminated, 0).length) round.scorerHints = 3;
    const previous = round.selected.length;
    round.selected = round.selected.filter((id) => !round.eliminated.has(id));
    renderRound(`${round.scorerHints === 3 ? "Quedan únicamente los goleadores; indicá cuántos goles hizo cada uno. Acertar ya no suma puntos." : `Descartamos ${removed.length} jugadores que no convirtieron.`}${previous !== round.selected.length ? " Quitamos las selecciones de esos jugadores." : ""}`);
  }
  function showArchive() {
    round=null;
    const entries=records().filter(e=>scoped().some(m=>m.id===e.matchId)).sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt));
    const unique=entries.filter((e,i)=>entries.findIndex(other=>other.matchId===e.matchId)===i);
    app.innerHTML=`<div class="section-bar"><button class="back" data-action="home">← Volver a la campaña</button><span class="eyebrow">TU MEMORIA TIENE HISTORIA</span></div><h1 class="display archive-title">Mi archivo</h1><p class="muted">${escape(scopeName())} · ${unique.length} partidos con actividad guardada.</p>${unique.length?`<div class="archive-grid">${unique.map(entry=>{
      const match=data.matches.find(m=>m.id===entry.matchId),completed=entries.filter(e=>e.matchId===match.id),formed=completed.some(e=>e.mode==="formation"),revealed=C.resultRevealed(match,collectionRecords()),next=pending(match)[0];
      return `<article class="archive-card"><span class="eyebrow">${formed?"FORMACIÓN COMPLETA":"REGISTRO ANTERIOR"}</span><div class="archive-score">${crest(match.homeSlug,match.home)}<b>${revealed?escape(match.score):"? — ?"}</b>${crest(match.awaySlug,match.away)}</div><h2>${escape(match.home)} — ${escape(match.away)}</h2><p>${escape(match.date)}</p>${completed.map(e=>`<p>${e.skipped?"—":"✓"} ${e.mode==="formation"?"Formación":e.mode==="result"?"Bonus resultado":"Bonus goleadores"}: <strong>${Math.max(0,e.bestScore)} pts</strong>${e.skipped?" · omitido":""}</p>`).join("")}<button class="secondary" data-open-match="${escape(match.id)}">${!formed?"Completar formación":next?"Continuar bonus":"Ver ficha"} →</button></article>`;
    }).join("")}</div>`:'<div class="empty-state"><h2>Tu primera planilla te espera</h2><p class="muted">Completá una formación y encontrala acá.</p><button class="primary" data-action="campaign-play">Jugar →</button></div>'}`;
    focusMain();
  }
  function showMedals() {
    round = null; view = "medals";
    const entries=progress.list();
    const tournament=journeyIndex.find(item=>item.id==="apertura-2026");
    const tournamentNames=new Map();
    // Names live in the small index so this also works when opening a historical deep link.
    tournament.matches.forEach(m=>["home","away"].forEach(side=>tournamentNames.set(m[side+"Slug"],m[side])));
    const personal=C.personalCampaigns(journeyIndex,activity.list(),entries);
    const allClubs=[...tournamentNames].filter(([slug])=>personal.some(c=>c.club===slug)).sort((a,b)=>a[1].localeCompare(b[1],"es"));
    if(!allClubs.some(([slug])=>slug===medalClub)) medalClub="all";
    const cards=personal.filter(c=>medalClub==="all"||c.club===medalClub).map(({item,club})=>{
      const medals=Object.keys(routes).map(key=>({key,...C.routeStatus(C.routeMatches(item.matches,club,key),C.progressForClub(entries,club),item.id)}));
      const current=medals.find(m=>m.key===medalRoute);
      const state=current.complete?"complete":"started";
      return {item,medals,current,state,club};
    });
    const visible=cards.filter(card=>medalState==="all"||card.state===medalState);
    const totalPoints=journeyIndex.reduce((sum,item)=>sum+C.routeStatus(C.routeMatches(item.matches,"all","complete"),entries,item.id).score,0);
    const medalCount=cards.reduce((sum,c)=>sum+c.medals.filter(m=>m.complete).length,0);
    app.innerHTML=`<div class="section-bar"><button class="back" data-action="library">← Todas las campañas</button><div class="profile-nav"><button class="primary" data-action="quick-play">Jugar →</button><button class="back" data-action="profile">${profile.get().nickname?"Cambiar apodo":"Elegir apodo"}</button></div></div>
      <section class="medal-hero"><span class="eyebrow">TU HISTORIA EN LA TRIBUNA</span><h1>Mis campañas</h1><p>${profile.get().nickname?`${escape(profile.get().nickname)}, tu memoria tiene premio.`:"Tu próxima medalla empieza con un partido."}</p><div class="hero-tags"><span class="tag">${totalPoints} PUNTOS · MEJORES MARCAS</span><span class="tag">${medalCount} ${medalCount===1?"MEDALLA":"MEDALLAS"} EN ESTA VISTA</span></div></section>
      ${personal.length?`<div class="medal-filters"><label>Club<select id="medal-club"><option value="all">Todos mis clubes</option>${allClubs.map(([slug,name])=>`<option value="${escape(slug)}" ${medalClub===slug?"selected":""}>${escape(name)}</option>`).join("")}</select></label><label>Recorrido<select id="medal-route">${Object.entries(routes).map(([key,info])=>`<option value="${key}" ${medalRoute===key?"selected":""}>${info.title}</option>`).join("")}</select></label><label>Estado<select id="medal-state">${[["all","Todos"],["started","En juego"],["complete","Completadas"]].map(([key,name])=>`<option value="${key}" ${medalState===key?"selected":""}>${name}</option>`).join("")}</select></label></div><p class="muted medal-explanation">Sólo las campañas que empezaste. Completá la formación de cada partido para ganar cada medalla. Los bonus suman puntos extra. Los puntos conservan tu mejor marca.</p>`:""}
      <div class="medal-grid">${visible.map(({item,medals,current,state,club})=>`<article class="medal-card ${state}" data-medal-collection="${escape(item.id)}" data-medal-club="${escape(club)}"><div class="medal-card-heading">${item.clubSlug||club!=="all"?crest(item.clubSlug||club,""): '<span class="tournament-monogram" aria-hidden="true">26</span>'}<span class="medal-state">${state==="complete"?"✓ Completada":"En juego"}</span></div><h2>${escape(item.title)}</h2>${!item.clubSlug?`<p class="muted">${escape(tournamentNames.get(club)||"Todos los equipos")}</p>`:""}<div class="medal-badges">${medals.map(m=>`<span class="medal-badge ${m.complete?"earned":m.done?"started":""}" title="${routes[m.key].title}: ${m.done} de ${m.total} partidos"><span class="medal-progress-label"><span>${routes[m.key].title}</span><small>${m.complete?"✓ Completado":`${m.done} / ${m.total} partidos`}</small></span><span class="medal-track" aria-hidden="true"><span style="width:${m.total?100*m.done/m.total:0}%"></span></span></span>`).join("")}</div><button class="secondary" data-medal-open="${escape(item.id)}" data-scope="${escape(club)}">${current.complete?"Ver campaña":`Continuar ${routes[medalRoute].title.toLowerCase()}`} →</button></article>`).join("")}</div>${visible.length?"":personal.length?'<div class="empty-state"><h2>Todavía no hay campañas con este filtro</h2><p class="muted">Cambiá el estado o elegí otro recorrido.</p></div>':'<div class="empty-state"><h2>Tu primera campaña te espera</h2><p class="muted">Cuando empieces a jugar, la vas a encontrar acá.</p><button class="primary" data-action="quick-play">Jugar ahora →</button></div>'}${localNote}`;
    focusMain();
  }
  function nextRound() {
    const stats=routeStats(),previous=round.match.id;
    if(stats.complete) {medalClub=scope;medalRoute=selectedRoute;medalState="all";return showMedals();}
    const index=stats.remaining.findIndex(m=>m.id===previous);
    start(stats.remaining[(index+1)%stats.remaining.length].id);
  }
  app.addEventListener("change", (event) => {
    if(event.target.id.startsWith("medal-")) {
      const id=event.target.id;
      if(id==="medal-club") medalClub=event.target.value;
      if(id==="medal-route") medalRoute=event.target.value;
      if(id==="medal-state") medalState=event.target.value;
      showMedals();document.getElementById(id).focus({preventScroll:true});return;
    }
    if (event.target.id === "history-club") {
      app.querySelectorAll(".club-campaign-card").forEach(card=>{card.hidden=event.target.value!=="all"&&card.dataset.club!==event.target.value;});
      return;
    }
    if (event.target.id !== "club-select") return;
    scope = event.target.value;
    tournamentScope=scope;
    updateUrl();
    showHome();
    document.getElementById("club-select").focus({ preventScroll: true });
  });
  app.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button || button.disabled) return;
    if(button.dataset.route) {
      selectedRoute=button.dataset.route;profile.save({route:selectedRoute});updateUrl();showSetup();
      app.querySelector(`[data-route="${selectedRoute}"]`).focus({preventScroll:true});return;
    }
    if(button.dataset.medalOpen) {
      selectedRoute=medalRoute;profile.save({route:selectedRoute});
      return loadCollection(button.dataset.medalOpen,"setup",button.dataset.scope);
    }
    if (button.dataset.collection) return loadCollection(button.dataset.collection);
    if (button.dataset.openMatch) return start(button.dataset.openMatch);
    if (button.dataset.bonus && round) return beginBonus(button.dataset.bonus);
    const action = button.dataset.action;
    if(action==="campaign-play") return start();
    if(action==="skip-result") return skipResult();
    if(action==="reveal-result") return revealResult();
    if(action==="quick-play") return showQuickPlay();
    if(action==="profile") return askNickname(null);
    if(action==="medals") return showMedals();
    if (action === "library") {
      const url = new URL(location.href);url.searchParams.delete("collection");history.replaceState(null,"",url);
      return showLibrary();
    }
    if (action === "home") {
      view="setup";
      showHome();
      focusMain();
      return;
    }
    if (action === "archive") return showArchive();
    if (!round) return;
    if(action==="toggle-rival" && round.mode==="formation" && round.formationSides.length===1) {
      round.showRival=!round.showRival;round.rivalSeen=true;return renderRound();
    }
    if(action==="both-teams" && round.match.id==="espn-528144" && !round.rivalSeen && !round.completed && !round.solved.size && !Object.keys(round.hints).length) return start(round.match.id,true);
    if (action === "next" || (action === "skip-bonuses" && round.completed)) {
      return nextRound();
    }
    if (button.dataset.hint) return hint(button.dataset.hint);
    if (
      button.dataset.goal &&
      !round.completed &&
      !round.eliminated.has(button.dataset.goal) &&
      round.selected.length < round.match.scorers.length
    ) {
      round.selected.push(button.dataset.goal);
      return renderRound();
    }
    if (button.dataset.undo && !round.completed) {
      const index = round.selected.lastIndexOf(button.dataset.undo);
      if (index >= 0) round.selected.splice(index, 1);
      return renderRound();
    }
    if (action === "scorer-hint") return scorerHint();
    if (
      action === "confirm-scorers" &&
      !round.completed &&
      round.selected.length === round.match.scorers.length
    ) {
      const result = C.scoreScorers(round.selected, round.match, round.scorerHints);
      round.points = result.score;
      round.scorerResult = result;
      complete(result.correct);
      renderRound(
        result.correct
          ? "¡Acertaste todos los goleadores!"
          : `Acertaste ${result.matched} de ${result.total} goles: +${result.score} puntos. Los errores no restan.`,
        result.correct ? "good" : "",
      );
    }
  });
  app.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!round || round.completed) return;
    const form = event.target;
    if (form.id === "result-form") {
      const values = new FormData(form),
        home = Number(values.get("home")),
        away = Number(values.get("away"));
      if (!form.checkValidity() || !Number.isInteger(home) || !Number.isInteger(away)) return;
      const correct = home === round.match.homeGoals && away === round.match.awayGoals;
      round.points = correct ? 20 : 0;
      complete(correct);
      renderRound(
        correct ? "¡Resultado exacto! +20 puntos." : `El partido terminó ${round.match.score}. Bonus: 0 puntos; conservás lo ganado.`,
        correct ? "good" : "bad",
      );
    } else if (form.dataset.playerForm) {
      if(!activePlayer(form.dataset.playerForm)) return;
      const key = form.dataset.playerForm,
        player = getPlayer(key);
      if (round.solved.has(key)) return;
      const answer = new FormData(form).get("answer");
      if (!C.acceptedAnswer(answer, player)) {
        const message = document.getElementById("game-message");
        message.className = "notice bad";
        message.textContent = "Todavía no. Probá otro apellido o pedí una pista con ?.";
        form.querySelector("input").setAttribute("aria-invalid", "true");
        return;
      }
      const pendingKeys = [...app.querySelectorAll("[data-player-form]")].map(
        (item) => item.dataset.playerForm,
      );
      const nextKey =
        pendingKeys[pendingKeys.indexOf(key) + 1] || pendingKeys.find((item) => item !== key);
      const points = C.pointsForPlayer(round.hints[key], playerName(player), hiddenNumber(player));
      round.points += points;
      round.solved.add(key);
      if (round.solved.size === round.formationTotal) complete(true);
      renderRound(`¡Bien! ${playerName(player)} estaba en la planilla. +${points} puntos.`, "good");
      if (!round.completed && nextKey)
        document.getElementById(`guess-${nextKey}`)?.focus({ preventScroll: true });
    }
  });
  try {
    const response = await fetch("data/campanas/catalog.json");
    if (!response.ok) throw new Error("No se pudo cargar el catálogo");
    catalog = (await response.json()).collections;
    if (!Array.isArray(catalog)) throw new Error("Catálogo inválido");
    const indexResponse=await fetch("data/campanas/recorridos.json");
    if(!indexResponse.ok) throw new Error("No se pudo cargar el índice de recorridos");
    journeyIndex=(await indexResponse.json()).collections;
    const requested = new URLSearchParams(location.search).get("collection");
    if (requested && (requested === "apertura-2026" || catalog.some(item=>item.id===requested))) await loadCollection(requested);
    else await showLibrary();
  } catch (error) {
    app.innerHTML =
      '<div class="empty-state"><h1>No pudimos abrir las planillas</h1><p class="muted">Revisá tu conexión e intentá de nuevo. Tu progreso guardado sigue en este navegador.</p><button class="primary" id="retry-load">Volver a intentar</button></div>';
    document.getElementById("retry-load").addEventListener("click", () => location.reload());
    console.error("Campañas:", error);
  }
})();
