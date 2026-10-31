(function (root) {
  "use strict";
  const KEY = "tribunapp.campanas.progress.v1";
  function validEntry(entry) {
    return (
      entry &&
      typeof entry.matchId === "string" &&
      typeof entry.collectionId === "string" &&
      ["formation", "scorers", "result"].includes(entry.mode) &&
      (entry.formationClub === undefined || typeof entry.formationClub === "string") &&
      (entry.playClub === undefined || typeof entry.playClub === "string") &&
      Number.isFinite(entry.bestScore) &&
      Number.isInteger(entry.attempts) &&
      entry.attempts > 0 &&
      typeof entry.updatedAt === "string" &&
      Number.isFinite(Date.parse(entry.updatedAt)) &&
      typeof entry.completedAt === "string" &&
      Number.isFinite(Date.parse(entry.completedAt))
    );
  }
  function open(storage, onError) {
    let entries = [];
    try {
      const raw = storage.getItem(KEY);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved.schemaVersion !== 1 || !Array.isArray(saved.entries))
          throw new Error("Formato de progreso inválido");
        const unique = new Map();
        saved.entries.filter(validEntry).forEach((entry) => {
          const key = JSON.stringify([entry.collectionId, entry.matchId, entry.mode, entry.mode === "formation" ? entry.formationClub || "all" : "all"]),
            previous = unique.get(key);
          if (!previous) unique.set(key, entry);
          else
            unique.set(key, {
              ...previous,
              bestScore: Math.max(previous.bestScore, entry.bestScore),
              attempts: Math.max(previous.attempts, entry.attempts),
              updatedAt: [previous.updatedAt, entry.updatedAt].sort().pop(),
            });
        });
        entries = [...unique.values()];
      }
    } catch (error) {
      onError(error);
    }
    const list = () => entries.map((entry) => ({ ...entry }));
    return {
      list,
      save(collectionId, matchId, mode, score, dataVersion, playClub = "all", formationClub = "all") {
        const previous = entries.find(
          (entry) =>
            entry.collectionId === collectionId && entry.matchId === matchId && entry.mode === mode &&
            (mode !== "formation" || (entry.formationClub || "all") === formationClub),
        );
        const now = new Date().toISOString();
        const next = {
          collectionId,
          matchId,
          mode,
          playClub,
          ...(mode === "formation" ? { formationClub } : {}),
          bestScore: Math.max(previous ? previous.bestScore : -Infinity, score),
          lastScore: score,
          attempts: (previous?.attempts || 0) + 1,
          completedAt: previous?.completedAt || now,
          updatedAt: now,
          dataVersion,
        };
        entries = entries.filter((entry) => entry !== previous).concat(next);
        try {
          storage.setItem(KEY, JSON.stringify({ schemaVersion: 1, updatedAt: now, entries }));
        } catch (error) {
          onError(error);
        }
        return next;
      },
    };
  }
  const ACTIVITY_KEY = "tribunapp.campanas.activity.v1";
  function openActivity(storage, onError) {
    let entries = [];
    try {
      const raw = storage.getItem(ACTIVITY_KEY);
      if (raw) {
        const value = JSON.parse(raw);
        if (!Array.isArray(value)) throw new Error("Actividad inválida");
        entries = value.filter(item => item && typeof item.collectionId === "string" && typeof item.club === "string" &&
          ["express", "classic", "complete"].includes(item.route) && ["formation", "scorers", "result"].includes(item.mode) &&
          typeof item.startedAt === "string" && Number.isFinite(Date.parse(item.startedAt)));
      }
    } catch (error) { onError(error); }
    const list = () => entries.map(item => ({ ...item })).sort((a,b) => b.startedAt.localeCompare(a.startedAt));
    return {
      list,
      start(collectionId, club, route, mode) {
        entries = entries.filter(item => item.collectionId !== collectionId || item.club !== club)
          .concat({ collectionId, club, route, mode, startedAt: new Date().toISOString() });
        try { storage.setItem(ACTIVITY_KEY, JSON.stringify(entries)); } catch (error) { onError(error); }
      },
    };
  }
  const PROFILE_KEY = "tribunapp.campanas.profile.v1";
  function openProfile(storage, onError) {
    let value = { nickname: "", route: "express", mode: "formation" };
    const clean = (input) => ({
      nickname: typeof input?.nickname === "string" ? [...input.nickname.replace(/[\u0000-\u001f\u007f]/g, "").trim()].slice(0, 24).join("") : "",
      route: ["express", "classic", "complete"].includes(input?.route) ? input.route : "express",
      mode: ["formation", "scorers", "result"].includes(input?.mode) ? input.mode : "formation",
    });
    try { const raw = storage.getItem(PROFILE_KEY); if (raw) value = clean(JSON.parse(raw)); }
    catch (error) { onError(error); }
    return {
      get: () => ({ ...value }),
      save(changes) {
        value = clean({ ...value, ...changes });
        try { storage.setItem(PROFILE_KEY, JSON.stringify(value)); } catch (error) { onError(error); }
        return { ...value };
      },
    };
  }
  const api = { open, openProfile, openActivity, validEntry, KEY, PROFILE_KEY, ACTIVITY_KEY };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CampanasProgress = api;
})(typeof window !== "undefined" ? window : globalThis);
