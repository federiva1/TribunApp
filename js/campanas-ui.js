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
      icon: "▦",
      description:
        "Reconstruí los 22 apellidos. Cada ayuda revela un poco más y reduce los puntos.",
    },
    scorers: {
      title: "Goleadores",
      icon: "⚽",
      description:
        "Elegí quién hizo cada gol. ¿Te acordás de aquel doblete o del héroe que entró del banco?",
    },
    result: {
      title: "Resultado oculto",
      icon: "⌁",
      description:
        "Tenés los equipos y sus formaciones. Falta lo más importante: el marcador exacto.",
    },
  };
  let data, catalog = [], loadingCollection = false,
    teams,
    scope = new URLSearchParams(location.search).get("club") || "all",
    round = null;
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
  const crest = (slug, name, className = "") => {
    const match = data?.matches.find(m => m.homeSlug === slug || m.awaySlug === slug);
    const side = match?.homeSlug === slug ? "home" : "away";
    const external = match?.[side + "Crest"];
    const src = external && /^https:\/\/a\.espncdn\.com\//.test(external) ? external : `escudos/${slug}.png`;
    return `<img class="${className}" src="${escape(src)}" alt="${escape(name)}" width="40" height="46">`;
  };
  function showLibrary() {
    return loadCollection("apertura-2026");
  }
  function historicalLibrary() {
    const clubs = [...new Map(catalog.map(item => [item.clubSlug, item.club])).entries()];
    return `<section class="historical-library" aria-label="Campañas históricas"><div class="club-picker"><div><span class="eyebrow">OTRAS HISTORIAS PARA VOLVER A JUGAR</span><h2>Campañas históricas</h2><p class="muted">24 campañas · 12 clubes. Elegí una época de tu equipo y jugá los mismos tres retos.</p></div><label>Club <select id="history-club"><option value="all">Todos los clubes</option>${clubs.map(([slug,name])=>`<option value="${escape(slug)}">${escape(name)}</option>`).join("")}</select></label></div><div class="archive-grid">${catalog.map(item=>`<article class="archive-card historical-card" data-club="${escape(item.clubSlug)}">${crest(item.clubSlug,item.club)}<h2>${escape(item.title)}</h2><p>${escape(item.achievement)}</p><p class="muted">${item.matchCount} partidos · Formación: ${item.coverage.formation} · Goleadores: ${item.coverage.scorers} · Resultado: ${item.coverage.result}</p><button class="primary" data-collection="${escape(item.id)}">Elegir retos →</button></article>`).join("")}</div><p class="local-note">Cada campaña guarda su propio progreso. Los retos sin datos suficientes y los encuentros suspendidos no se habilitan; los 0–0 no participan en goleadores.</p></section>`;
  }
  async function loadCollection(id) {
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
      scope = data.clubSlug || new URLSearchParams(location.search).get("club") || "all";
      if (!teams.some(team=>team.slug===scope)) scope="all";
      const url = new URL(location.href);url.searchParams.set("collection",data.id);history.replaceState(null,"",url);
      showHome();focusMain();
    } catch(error) {
      if (!data) throw error;
      showHome();
      const notice = document.createElement("p");notice.className="notice bad";notice.setAttribute("role","alert");notice.textContent="No pudimos cargar esa campaña. Volvé a intentarlo; tu progreso está guardado.";app.prepend(notice);
    } finally { loadingCollection=false; }
  }
  const records = () =>
    progress
      .list()
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
  const done = (mode) =>
    records().filter(
      (entry) =>
        entry.mode === mode &&
        C.eligible(data.matches, scope, mode).some((match) => match.id === entry.matchId),
    ).length;
  const bestTotal = () => records().reduce((total, entry) => total + entry.bestScore, 0);
  function focusMain() {
    app.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  function showHome() {
    round = null;
    const tournament = !data.clubSlug;
    app.innerHTML = `<div class="section-bar">${tournament ? '<span class="eyebrow">CAMPAÑAS · EL ARCHIVO DE LA TRIBUNA</span>' : '<button class="back" data-action="library">← Volver a Campañas</button>'}<button class="archive-button" data-action="archive">Mi archivo <span aria-hidden="true">↗</span></button></div>
      <section class="hero"><div><span class="eyebrow">${tournament ? "EL FÚTBOL SE JUEGA DE MEMORIA" : "VOLVÉ A JUGAR LA HISTORIA"}</span><h1>${tournament ? "¿Cuánto sabés<br>de <span>fútbol argentino?</span>" : escape(data.title)}</h1><p>${tournament ? "Los nombres, los goles, esos resultados que no se olvidan. Volvé a jugar el Apertura 2026: poné a prueba tu memoria con tu equipo o recorré todo el torneo." : escape(data.description)}</p><div class="hero-tags"><span class="tag">${data.matches.length} PARTIDOS</span>${tournament ? `<span class="tag">${teams.length} CLUBES</span>` : ""}<span class="tag">3 FORMAS DE JUGAR</span></div></div><div class="crest-wall" aria-label="${tournament ? "Los 30 clubes del torneo" : "Clubes de la campaña"}">${teams.filter(team=>tournament||team.slug===data.clubSlug).map((team) => crest(team.slug, team.name)).join("")}</div></section>
      <section aria-label="Elegir desafío"><div class="club-picker"><div>${tournament ? '<span class="eyebrow">APERTURA 2026 · TORNEO COMPLETO</span>' : ""}<h2>${tournament ? "¿Qué reto querés jugar?" : "Elegí tu desafío"}</h2><p class="muted">${data.clubSlug ? escape(data.club) : "Seguí a tu club o jugá con todos."}</p></div>${data.clubSlug ? "" : `<label><span class="eyebrow" style="display:block;margin-bottom:6px">EQUIPO</span><select id="club-select" aria-label="Equipo"> <option value="all">Todos los equipos</option>${teams.map((team) => `<option value="${escape(team.slug)}" ${scope === team.slug ? "selected" : ""}>${escape(team.name)}</option>`).join("")}</select></label>`}</div>
      <div class="mode-grid">${Object.entries(modes)
        .map(([mode, info]) => {
          const total = C.eligible(data.matches, scope, mode).length,
            count = done(mode);
          return `<button class="mode-card" data-mode="${mode}" ${total ? "" : "disabled"}><span class="mode-icon" aria-hidden="true">${info.icon}</span><h3>${info.title}</h3><p>${info.description}</p><span class="mode-progress">${count} / ${total} partidos completados</span><span class="progress-track"><span style="width:${total ? (count / total) * 100 : 0}%"></span></span><span class="mode-cta">${count === total && total ? "Volver a jugar" : count ? "Seguir jugando" : "Empezar a jugar"} <span aria-hidden="true">→</span></span></button>`;
        })
        .join("")}</div></section>
      <p class="local-note"><span aria-hidden="true">◉</span><span>Jugá sin registrarte. Tu progreso queda en este navegador. Si cambiás de dispositivo o borrás sus datos, empezás de nuevo.</span></p>
      ${records().length ? `<div class="summary-strip"><span><b>${records().length}</b> desafíos completados</span><span><b>${bestTotal()}</b> puntos · suma de tus mejores marcas</span></div>` : ""}
      ${data.clubSlug ? `<details class="coming"><summary>Ver recorrido y disponibilidad</summary><div>${data.matches.map(match=>`<p>${escape(match.date)} · ${escape(match.home)} — ${escape(match.away)} · ${Object.entries(modes).filter(([mode])=>C.eligible([match],"all",mode).length).map(([,info])=>info.title).join(" / ") || "Pendiente de revisión"}</p>`).join("")}</div></details>` : historicalLibrary()}`;
  }
  function start(mode, matchId) {
    const options = C.eligible(data.matches, scope, mode);
    if (!options.length) return;
    const seen = records();
    const chosen =
      options.find((match) => match.id === matchId) ||
      options.find((match) => !seen.some((entry) => entry.matchId === match.id)) ||
      options.find(
        (match) => !seen.some((entry) => entry.matchId === match.id && entry.mode === mode),
      ) ||
      options[(options.findIndex((match) => match.id === round?.match.id) + 1) % options.length];
    const teamGames = new Set(
      seen
        .filter((entry) => scoped().some((match) => match.id === entry.matchId))
        .map((entry) => entry.matchId),
    ).size;
    round = {
      mode,
      match: chosen,
      points: 0,
      solved: new Set(),
      hints: {},
      selected: [],
      eliminated: new Set(),
      scorerHints: 0,
      completed: false,
      correct: null,
      hideNumbers: mode === "formation" && scope !== "all" && teamGames >= 2,
    };
    app.innerHTML = "";
    renderRound();
    focusMain();
  }
  const playerKey = (side, index) => `${side}-${index}`;
  const playerName = (player) => player.accepted_answers?.[0] || player.name;
  const hiddenNumber = (player) => round.hideNumbers && player.n != null && player.n !== "";
  const pending = (match) => C.pendingModes(match, records());
  function pendingButtons(match) {
    const available = pending(match);
    return available.length
      ? `<p class="muted">Otros retos pendientes de este partido:</p><div class="pending-challenges">${available.map((mode) => `<button class="secondary" data-replay="${escape(match.id)}" data-replay-mode="${mode}">${modes[mode].title} →</button>`).join("")}</div>`
      : '<p class="muted">Ya completaste todos los retos disponibles de este partido.</p>';
  }
  function playerRow(player, side, index) {
    const key = playerKey(side, index),
      solved = round.solved.has(key),
      level = round.hints[key];
    player = { ...player, name: playerName(player) };
    const number = hiddenNumber(player) && level === undefined && !solved ? "—" : (player.n ?? "—");
    const letterHint = level === undefined || (hiddenNumber(player) && level === 0)
      ? "" : mask(player.name, Math.max(0, level - (hiddenNumber(player) ? 1 : 0)));
    return `<li class="player-row ${solved ? "solved" : ""}" data-player="${key}"><span class="shirt-number">${escape(number)}</span>${solved || round.mode !== "formation" ? `<span class="player-name">${escape(player.name)}</span>${solved ? '<span class="solved-mark">✓</span>' : ""}` : `<form data-player-form="${key}"><div class="entry-wrap"><label class="sr-only" for="guess-${key}">Apellido del jugador ${index + 1} de ${escape(side === "home" ? round.match.home : round.match.away)}</label><input id="guess-${key}" name="answer" class="${letterHint ? "hint-placeholder" : ""}" placeholder="${escape(letterHint || "Apellido del jugador")}" title="${escape(letterHint || "Apellido del jugador")}" aria-label="Apellido del jugador ${index + 1}${letterHint ? `, pista: ${escape(letterHint)}` : ""}" autocomplete="off" autocapitalize="words" spellcheck="false" required></div><button class="check-answer" aria-label="Comprobar jugador ${index + 1}" title="Comprobar">✓</button></form><button class="player-hint" data-hint="${key}" title="Pedir una pista para este jugador" aria-label="Pista para jugador ${index + 1}">?</button>`}</li>`;
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
  function sheet(side) {
    const match = round.match,
      name = match[side],
      slug = match[side + "Slug"],
      players = match[side + "XI"];
    let body = players.map((player, index) => playerRow(player, side, index)).join("");
    if (round.mode === "result" && match.availability?.formation === false)
      body = '<li class="player-row muted">La formación completa no está disponible en esta ficha. Podés jugar a recordar el resultado.</li>';
    if (round.mode === "scorers") {
      const candidates = C.scorerCandidates(match).filter((player) => player.team === name);
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
    return `<section class="team-sheet"><div class="sheet-title">${crest(slug, "")}<h2>${escape(name)}</h2><span>${round.mode === "scorers" ? "PLANILLA" : "ONCE INICIAL"}</span></div><ol class="player-list">${body}</ol></section>`;
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
        ? `Completá los 22 apellidos. Sin ayuda: 3 puntos; primera ayuda: 2; segunda: 1; desde la tercera: 0. También vale 0 si se revelan dos letras o la mitad del apellido. Equivocarte no resta. ${round.hideNumbers ? "Desde tu tercer partido con este club, la primera pista revela el dorsal, si está disponible." : "Tocá ? al lado de un jugador para pedir una pista."}`
        : round.mode === "scorers"
          ? "Tocá un jugador una vez por cada gol. Podés quitar goles con −. Acertar suma 20 puntos; con ayudas: 14, 8 o 0. Un error resta 5."
          : "Ingresá el marcador al final del partido (incluye alargue, no la tanda de penales). Acertar suma 20 puntos; un error resta 5.";
    app.innerHTML = `<div class="section-bar"><button class="back" data-action="home">← Cambiar desafío</button><button class="archive-button" data-action="archive">Mi archivo ↗</button></div><div class="game-top"><div><span class="eyebrow">${escape(data.title)} · ${escape(scopeName())}</span><h1>${info.title}</h1></div><div class="points" aria-label="Puntos de esta partida">${round.points} pts</div></div>
      <section class="match-board" aria-label="Partido"><p class="match-date">${escape(match.date)}</p><div class="scoreboard"><div class="score-team">${crest(match.homeSlug, "")}<span>${escape(match.home)}</span></div><strong class="score-value">${round.mode === "result" && !round.completed ? "? — ?" : escape(match.score)}</strong><div class="score-team away">${crest(match.awaySlug, "")}<span>${escape(match.away)}</span></div></div><p class="venue">${escape(match.stadium)}${round.mode !== "result" || round.completed ? ` · ${escape(match.zone)}` : ""}</p></section>
      <p class="rules-strip">${rules}</p>
      ${round.mode === "result" && !round.completed ? `<form id="result-form" class="result-form"><label>${escape(match.home)}<input name="home" type="number" inputmode="numeric" min="0" max="99" step="1" required aria-label="Goles de ${escape(match.home)}"></label><span aria-hidden="true">—</span><label>${escape(match.away)}<input name="away" type="number" inputmode="numeric" min="0" max="99" step="1" required aria-label="Goles de ${escape(match.away)}"></label><button class="primary">Confirmar resultado</button></form>` : ""}
      <p class="notice ${tone}" id="game-message" role="status" aria-live="polite">${escape(message || (round.mode === "formation" ? `${round.solved.size} / 22 apellidos encontrados` : round.mode === "scorers" ? `${round.selected.length} / ${match.scorers.length} goles elegidos` : "La formación te puede ayudar a recordar."))}</p>
      ${round.completed ? `<section class="completion"><h2>${round.mode === "formation" ? "Planilla completa" : round.correct ? "¡Lo tenías guardado!" : "Uno más para la memoria"}</h2><p>Terminaste con <strong>${round.points} puntos</strong>. ${round.saved?.bestScore > round.points ? `Tu mejor marca: ${round.saved.bestScore} puntos.` : "Tu marca quedó en el archivo, incluso si sumaste 0 puntos."}</p>${round.mode === "scorers" ? `<div class="goal-summary">Goleadores: ${escape(match.scorers.join(", "))}.</div>` : ""}${pendingButtons(match)}<button class="primary" data-action="next" style="margin-top:18px">Siguiente partido →</button></section>` : ""}
      <div class="sheets">${sheet("home")}${sheet("away")}</div>
      <div class="game-actions">${round.mode === "scorers" && !round.completed ? `<button class="secondary" data-action="scorer-hint" ${C.scorerHintPlan(match, round.eliminated, round.scorerHints).length ? "" : "disabled"}>? Ayuda (${round.scorerHints}/3)</button><span class="muted">Acertar ahora: ${C.scoreScorers(C.actualScorers(match), match, round.scorerHints).score} puntos</span><button class="primary" data-action="confirm-scorers" ${round.selected.length !== match.scorers.length ? "disabled" : ""}>Confirmar goleadores</button>` : `<span class="muted">${round.mode === "formation" ? `${round.solved.size} / 22 apellidos` : escape(data.title)}</span>`}<button class="secondary" data-action="next">${round.completed ? "Siguiente partido →" : "Saltar partido →"}</button></div>`;
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
  }
  function complete(correct) {
    if (round.completed) return;
    round.completed = true;
    round.correct = correct;
    round.saved = progress.save(data.id, round.match.id, round.mode, round.points, data.version);
  }
  function getPlayer(key) {
    const [side, index] = key.split("-");
    return round.match[side + "XI"][Number(index)];
  }
  function hint(key) {
    if (round.completed || round.solved.has(key)) return;
    const raw = getPlayer(key),
      player = { ...raw, name: playerName(raw) },
      level = round.hints[key] === undefined ? 0 : round.hints[key] + 1;
    round.hints[key] = level;
    const letterCount = [...player.name].filter((letter) => /[\p{L}\p{N}]/u.test(letter)).length;
    if (level >= letterCount + (hiddenNumber(player) ? 1 : 0)) {
      round.solved.add(key);
      if (round.solved.size === 22) complete(true);
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
    round = null;
    const entries = records()
      .filter((entry) => scoped().some((match) => match.id === entry.matchId))
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
    app.innerHTML = `<div class="section-bar"><button class="back" data-action="home">← Volver a Campañas</button><span class="eyebrow">TU MEMORIA TIENE HISTORIA</span></div><h1 class="display" style="font-size:44px">Mi archivo</h1><p class="muted">${escape(scopeName())} · ${entries.length} desafíos completados. Guardados en este navegador.</p>${
      entries.length
        ? `<div class="archive-grid">${entries.filter((entry, index) => entries.findIndex((item) => item.matchId === entry.matchId) === index)
            .map((entry) => {
              const match = data.matches.find((item) => item.id === entry.matchId);
              const completed = entries.filter((item) => item.matchId === match.id);
              return `<article class="archive-card"><span class="eyebrow">${completed.length} RETOS COMPLETADOS</span><div class="archive-score">${crest(match.homeSlug, match.home)}<b>${escape(match.score)}</b>${crest(match.awaySlug, match.away)}</div><h2>${escape(match.home)} — ${escape(match.away)}</h2><p>${escape(match.date)}</p>${completed.map((item) => `<p>✓ ${modes[item.mode].title}: <strong>${item.bestScore} pts</strong></p>`).join("")}${pendingButtons(match)}${pending(match).length ? "" : `<button class="secondary" data-replay="${escape(match.id)}" data-replay-mode="${entry.mode}">Repetir ${modes[entry.mode].title.toLowerCase()} →</button>`}</article>`;
            })
            .join("")}</div>`
        : '<div class="empty-state"><h2>Tu primera planilla te espera</h2><p class="muted">Completá un desafío y encontralo acá.</p><button class="primary" data-action="home">Elegir un desafío →</button></div>'
    }`;
    focusMain();
  }
  app.addEventListener("change", (event) => {
    if (event.target.id === "history-club") {
      app.querySelectorAll(".historical-card").forEach(card=>{card.hidden=event.target.value!=="all"&&card.dataset.club!==event.target.value;});
      return;
    }
    if (event.target.id !== "club-select") return;
    scope = event.target.value;
    const url = new URL(location.href);
    if (scope === "all") url.searchParams.delete("club");
    else url.searchParams.set("club", scope);
    history.replaceState(null, "", url);
    showHome();
    document.getElementById("club-select").focus({ preventScroll: true });
  });
  app.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button || button.disabled) return;
    if (button.dataset.collection) return loadCollection(button.dataset.collection);
    if (button.dataset.mode) return start(button.dataset.mode);
    if (button.dataset.replay) return start(button.dataset.replayMode, button.dataset.replay);
    const action = button.dataset.action;
    if (action === "library") {
      const url = new URL(location.href);url.searchParams.delete("collection");history.replaceState(null,"",url);
      return showLibrary();
    }
    if (action === "home") {
      showHome();
      focusMain();
      return;
    }
    if (action === "archive") return showArchive();
    if (!round) return;
    if (action === "next") {
      const options = C.eligible(data.matches, scope, round.mode),
        index = options.findIndex((match) => match.id === round.match.id);
      const remaining = options.slice(index + 1).concat(options.slice(0, index + 1));
      const next =
        remaining.find(
          (match) =>
            !records().some((entry) => entry.matchId === match.id && entry.mode === round.mode),
        ) || remaining[0];
      return start(round.mode, next.id);
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
      complete(result.correct);
      renderRound(
        result.correct
          ? "¡Acertaste todos los goleadores!"
          : "No eran esos. La planilla muestra quiénes convirtieron.",
        result.correct ? "good" : "bad",
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
      round.points = correct ? 20 : -5;
      complete(correct);
      renderRound(
        correct ? "¡Resultado exacto!" : `El partido terminó ${round.match.score}.`,
        correct ? "good" : "bad",
      );
    } else if (form.dataset.playerForm) {
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
      if (round.solved.size === 22) complete(true);
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
