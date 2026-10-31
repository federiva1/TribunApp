// Small spoiler-free index: medals load IDs and eligibility, never every lineup.
const fs = require('node:fs');
const path = require('node:path');
const core = require('../js/campanas-core.js');
const root = path.resolve(__dirname, '..');
function build() {
  const catalog = require('../data/campanas/catalog.json').collections;
  return { version: 1, collections: [{ id: 'apertura-2026', title: 'Apertura 2026', file: 'data/campanas/apertura-2026.json' }, ...catalog].map(item => {
    const data = JSON.parse(fs.readFileSync(path.join(root, item.file), 'utf8'));
    return { id: item.id, title: item.title, club: item.club, clubSlug: item.clubSlug,
      matches: data.matches.map(m => ({ id: m.id, homeSlug: m.homeSlug, awaySlug: m.awaySlug,
        ...(item.id === 'apertura-2026' ? {home:m.home,away:m.away} : {}), modes: core.matchModes(m) })) };
  }) };
}
if (require.main === module) {
  const output = JSON.stringify(build());
  fs.writeFileSync(path.join(root, 'data/campanas/recorridos.json'), output + '\n');
  console.log('Índice de recorridos:', Buffer.byteLength(output), 'bytes');
}
module.exports = build;
