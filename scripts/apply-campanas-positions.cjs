// Match-scoped editorial corrections. Never changes player identities or XI membership.
const fs = require('node:fs'), path = require('node:path');
const overrides = require('./campanas-position-overrides.json');
function applyPositions(match, collectionId) {
  const rules = overrides[collectionId] || [];
  for (const side of ['home', 'away']) for (const group of ['XI', 'Subs']) {
    for (const player of match[side + group] || []) {
      const rule = rules.find(rule => rule.playerIds.includes(player.playerId));
      if (rule && player.pos !== rule.pos) {
        if (!Object.hasOwn(player, 'sourcePos')) player.sourcePos = player.pos ?? null;
        player.pos = rule.pos;
        player.positionSource = rule.source;
      }
    }
  }
  return match;
}
if (require.main === module) {
  for (const id of Object.keys(overrides)) {
    const file = path.join(__dirname, '..', 'data', 'campanas', id + '.json');
    const collection = JSON.parse(fs.readFileSync(file, 'utf8'));
    collection.matches.forEach(match => applyPositions(match, id));
    fs.writeFileSync(file, JSON.stringify(collection) + '\n');
    console.log('Posiciones verificadas: ' + id);
  }
}
module.exports = applyPositions;
