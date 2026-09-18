(function (root) {
  "use strict";
  const KEY = "tribunapp.campanas.progress.v1";
  function validEntry(entry) {
    return (
      entry &&
      typeof entry.matchId === "string" &&
      typeof entry.collectionId === "string" &&
      ["formation", "scorers", "result"].includes(entry.mode) &&
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
          const key = JSON.stringify([entry.collectionId, entry.matchId, entry.mode]),
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
      save(collectionId, matchId, mode, score, dataVersion) {
        const previous = entries.find(
          (entry) =>
            entry.collectionId === collectionId && entry.matchId === matchId && entry.mode === mode,
        );
        const now = new Date().toISOString();
        const next = {
          collectionId,
          matchId,
          mode,
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
  const api = { open, validEntry, KEY };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CampanasProgress = api;
})(typeof window !== "undefined" ? window : globalThis);
