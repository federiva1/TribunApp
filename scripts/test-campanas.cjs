const assert = require('node:assert/strict');
const test = require('node:test');
const core = require('../js/campanas-core.js');
const collection = require('../data/campanas/apertura-2026.json');
const progress = require('../js/campanas-progress.js');
test('normalization accepts accents, case, whitespace and explicit aliases without fuzzy false positives', () => {
  assert(core.acceptedAnswer('  LOPEZ   MUÑOZ ', 'López Muñoz'));
  assert(core.acceptedAnswer('Cortez', 'Cortés'));
  assert(core.acceptedAnswer('Nacho', { name: 'Fernández', accepted_answers: ['Nacho'] }));
  assert(!core.acceptedAnswer('Lopez', 'López Muñoz'));
  assert(!core.acceptedAnswer('', ''));
});
test('formation hint penalties match the prototype', () => {
  assert.deepEqual([undefined, 0, 1, 2, 9].map(core.pointsForPlayer), [3, 2, 1, 0, 0]);
});
test('collection retains all matches, clubs, sources, complete starters and unique IDs', () => {
  assert.equal(collection.matches.length, 255);
  assert.equal(new Set(collection.matches.flatMap(m => [m.homeSlug, m.awaySlug])).size, 30);
  assert.equal(new Set(collection.matches.map(m => m.id)).size, 255);
  assert.equal(collection.matches.filter(m => m.scorers.length).length, 220);
  for (const m of collection.matches) {
    assert.equal(m.homeXI.length, 11, m.id);
    assert.equal(m.awayXI.length, 11, m.id);
    assert(m.source, m.id);
    assert.equal(m.scorers.length, m.homeGoals + m.awayGoals, m.id);
  }
});
test('all eligible scorer challenges are solvable including substitutes and repeated goals', () => {
  const eligible = core.eligible(collection.matches, 'all', 'scorers');
  assert.equal(eligible.length, 193);
  for (const m of eligible) {
    const actual = core.actualScorers(m);
    const candidates = core.scorerCandidates(m);
    assert(actual.every(id => candidates.some(p => p.id === id)), m.id);
    assert.deepEqual(core.scoreScorers(actual.slice().reverse(), m, 0), { correct: true, score: 20 });
    assert.deepEqual([0, 1, 2, 3].map(h => core.scoreScorers(actual, m, h).score), [20, 14, 8, 0]);
    assert.equal(core.scoreScorers(actual.slice(1), m).correct, false);
  }
  const repeated = eligible.find(m => new Set(core.actualScorers(m)).size < m.scorers.length);
  assert(repeated);
  assert.equal(core.scoreScorers([...new Set(core.actualScorers(repeated))], repeated).score, -5);
});
test('club filters accept slugs or names; no-goal and ambiguous games stay out of scorer mode', () => {
  assert.deepEqual(core.eligible(collection.matches, 'aldosivi', 'result'), core.eligible(collection.matches, 'Aldosivi', 'result'));
  assert.equal(core.eligible(collection.matches, 'all', 'formation').length, 255);
  assert(core.eligible(collection.matches, 'all', 'scorers').every(m => !m.scorerAmbiguous && !m.scorerIncomplete && m.scorers.length));
  const zero = collection.matches.find(m => !m.scorers.length);
  assert.equal(core.scoreScorers([], zero).correct, false);
});
test('effective prototype overrides retain original IDs and explicit team disambiguation', () => {
  assert.equal(collection.matches.filter(m => m.legacyIds.length).length, 10);
  const tigre = collection.matches.find(m => m.home === 'Tigre' && m.away === 'Argentinos Juniors');
  assert.equal(core.actualScorers(tigre)[0], 'Argentinos Juniors|Álvarez');
  assert.equal(core.actualScorers(tigre)[1], 'Tigre|Oviedo');
});
test('missing roster authors are selectable without fabricated shirt numbers or roles', () => {
  const m = collection.matches.find(m => core.scorerCandidates(m).some(p => p.rosterUnknown));
  const p = core.scorerCandidates(m).find(p => p.rosterUnknown);
  assert.equal(p.n, null);
  assert.equal(p.substitute, false);
  assert(core.actualScorers(m).includes(p.id));
  assert(m.qualityWarnings.length);
  assert.equal(core.eligible([m], 'all', 'scorers').length, 0);
  assert.equal(core.eligible([m], 'all', 'formation').length, 1);
  assert.equal(core.eligible([m], 'all', 'result').length, 1);
});
test('curated aliases accept complete names while preserving abbreviated source names', () => {
  const players = collection.matches.flatMap(m => m.homeXI.concat(m.awayXI));
  for (const [abbreviation, answer] of [['Sch.', 'Barros Schelotto'], ['Q.', 'Martínez Quarta'], ['P.', 'González Pírez'], ['Torr.', 'Silva Torrejón']]) {
    const player = players.find(p => p.name === abbreviation && p.accepted_answers);
    assert(player, abbreviation);
    assert(core.acceptedAnswer(answer, player));
    assert.equal(player.name, abbreviation);
  }
});
test('progress persists best scores and attempts independently for each mode and collection', () => {
  const values = new Map();
  const storage = { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value) };
  const store = progress.open(storage, error => { throw error; });
  store.save('apertura-2026', 'match-1', 'result', -5, 1);
  assert.equal(store.list()[0].bestScore, -5, 'a wrong first answer must not become a zero-point record');
  store.save('apertura-2026', 'match-1', 'result', 20, 1);
  store.save('apertura-2026', 'match-1', 'result', -5, 1);
  store.save('apertura-2026', 'match-1', 'formation', 66, 1);
  store.save('otra-campana', 'match-1', 'result', 0, 1);
  const restored = progress.open(storage, error => { throw error; }).list();
  assert.equal(restored.length, 3);
  const result = restored.find(entry => entry.collectionId === 'apertura-2026' && entry.mode === 'result');
  assert.equal(result.bestScore, 20);
  assert.equal(result.lastScore, -5);
  assert.equal(result.attempts, 3);
  assert(result.completedAt <= result.updatedAt);
  const copy = store.list(); copy[0].bestScore = 999;
  assert(!store.list().some(entry => entry.bestScore === 999));
});
test('unavailable storage preserves progress in memory and reports failure', () => {
  const errors = [];
  const store = progress.open({ getItem() { throw new Error('blocked'); }, setItem() { throw new Error('quota'); } }, error => errors.push(error));
  store.save('apertura-2026', 'match-1', 'result', 20, 1);
  assert.equal(store.list()[0].bestScore, 20);
  assert.equal(errors.length, 2);
});
test('corrupt JSON is recoverable and malformed records are omitted', () => {
  const errors = [];
  const corrupt = progress.open({ getItem: () => '{broken', setItem() {} }, error => errors.push(error));
  assert.deepEqual(corrupt.list(), []);
  assert.equal(errors.length, 1);
  const malformed = progress.open({ getItem: () => JSON.stringify({ schemaVersion: 1, entries: [{ matchId: 'a', collectionId: 'a', mode: 'unknown', bestScore: 20, attempts: 1 }, null] }), setItem() {} }, error => errors.push(error));
  assert.deepEqual(malformed.list(), []);
});
test('stored records require usable completion and update timestamps', () => {
  const valid = { collectionId: 'apertura-2026', matchId: 'match-1', mode: 'result', bestScore: 20, attempts: 1,
    updatedAt: '2026-09-18T12:00:00.000Z', completedAt: '2026-09-18T11:00:00.000Z' };
  assert(progress.validEntry(valid));
  const invalid = [];
  for (const field of ['updatedAt', 'completedAt']) {
    for (const value of [undefined, null, 123, '', 'not-a-date']) {
      const entry = { ...valid, [field]: value };
      assert(!progress.validEntry(entry), field + ': ' + value);
      invalid.push(entry);
    }
  }
  const storage = { getItem: () => JSON.stringify({ schemaVersion: 1, entries: [...invalid, valid] }), setItem() {} };
  const records = progress.open(storage, error => { throw error; }).list();
  assert.deepEqual(records, [valid]);
  assert.doesNotThrow(() => records.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)));
});
test('duplicate stored keys merge best score and attempts without inflating completion counts', () => {
  const early = { collectionId: 'apertura-2026', matchId: 'match-1', mode: 'result', bestScore: 20, attempts: 2,
    updatedAt: '2026-09-17T12:00:00.000Z', completedAt: '2026-09-17T11:00:00.000Z' };
  const late = { ...early, bestScore: -5, attempts: 4, updatedAt: '2026-09-18T12:00:00.000Z' };
  let raw = JSON.stringify({ schemaVersion: 1, entries: [early, late, { ...early, mode: 'formation' }] });
  const storage = { getItem: () => raw, setItem: (key, value) => { raw = value; } };
  const store = progress.open(storage, error => { throw error; });
  assert.equal(store.list().length, 2);
  const result = store.list().find(entry => entry.mode === 'result');
  assert.equal(result.bestScore, 20);
  assert.equal(result.attempts, 4);
  assert.equal(result.updatedAt, late.updatedAt);
  store.save('apertura-2026', 'match-1', 'result', 14, 1);
  assert.equal(store.list().length, 2);
  assert.equal(store.list().find(entry => entry.mode === 'result').attempts, 5);
  assert.equal(progress.open(storage, error => { throw error; }).list().length, 2);
});
