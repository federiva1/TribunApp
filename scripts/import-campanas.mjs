// Mechanical import from the supplied La Planilla prototype. No network calls.
// Usage: node scripts/import-campanas.mjs "C:/path/to/mvp-la-planilla"
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = process.argv[2];
if (!source) throw new Error('Indicá la carpeta del prototipo como argumento.');
const core = createRequire(import.meta.url)('../js/campanas-core.js');
const original = JSON.parse(fs.readFileSync(path.join(source, 'app/tournament-data.json'), 'utf8'));
const page = fs.readFileSync(path.join(source, 'app/page.tsx'), 'utf8');
const start = page.indexOf('const argentinosBase =');
const end = page.indexOf('const matches: Match[] =');
if (start < 0 || end < start) throw new Error('Cambió el bloque de correcciones del prototipo. Revisar importador.');
const seedCode = page.slice(start, end).replace('const argentinosMatches: Match[] =', 'const argentinosMatches =');
const seeds = vm.runInNewContext('const xi = players => players.map(([n,name]) => ({n,name}));\n' + seedCode + '\nargentinosMatches;', {}, { timeout: 1000 });
const clubs = vm.runInNewContext(fs.readFileSync(path.join(root, 'js/clubes.js'), 'utf8') + '\nCLUBES_CONFIG;', {}, { timeout: 1000 });
const aliases = { 'Central Córdoba': 'centralcordobadesantiago', 'Gimnasia La Plata': 'gimnasialp', 'Gimnasia Mendoza': 'gimnasiamendoza', 'Instituto': 'instituto', 'Talleres': 'talleres', 'Sarmiento': 'sarmiento', 'Unión': 'union', 'Newells Old Boys': 'newellsoldboys' };
function slug(name) {
  const found = aliases[name] || Object.keys(clubs).find(key => core.normalize(clubs[key].nombre) === core.normalize(name));
  if (!found) throw new Error('Club sin slug: ' + name);
  return found;
}
let overrides = 0;
// Curated aliases supported by other entries in the supplied prototype for the
// same club/shirt, plus its explicit River and Gimnasia corrections. Keep the
// original spelling as name so import provenance remains inspectable.
const playerAliases = {
  'San Lorenzo|3|.': ['Rodríguez Pagano'],
  'Independiente|5|.': ['Fernández Cedrés'],
  'Estudiantes de La Plata|14|P.': ['González Pírez'],
  'River Plate|28|Q.': ['Martínez Quarta'],
  'Gimnasia La Plata|24|Torr.': ['Silva Torrejón'],
  'Gimnasia La Plata|10|Sch.': ['Barros Schelotto'],
  'Gimnasia La Plata|31|Sch.': ['Barros Schelotto'],
  'Gimnasia La Plata|8|Fern.': ['Fernández'],
  'Belgrano|11|M.': ['González Metilli'],
  'Rosario Central|28|Fernán.': ['Fernández'],
  'Atlético Tucumán|18|Rodrí.': ['Ruiz Rodríguez']
};
const matches = original.map(item => {
  const seed = [item.home, item.away].includes('Argentinos Juniors') && seeds.find(value => value.date.split(' · ')[0] === item.date.split(' · ')[0]);
  if (seed) overrides++;
  const match = JSON.parse(JSON.stringify(seed || item));
  match.homeSlug = slug(match.home);
  match.awaySlug = slug(match.away);
  match.legacyIds = item.id === match.id ? [] : [item.id];
  match.source = match.source || item.source || 'Prototipo La Planilla';
  for (const side of ['home', 'away']) {
    for (const player of [...match[side + 'XI'], ...(match[side + 'Subs'] || [])]) {
      const accepted = playerAliases[match[side] + '|' + player.n + '|' + player.name];
      if (accepted) player.accepted_answers = accepted;
    }
  }
  if (seed) match.provenance = { kind: 'prototype-override', originalId: item.id, originalSource: item.source || null };
  // Persist the prototype's explicit Tigre/Argentinos disambiguation in data.
  if (!match.scorerTeams) {
    match.scorerTeams = match.scorers.map((name, index) => {
      const inHome = [...match.homeXI, ...(match.homeSubs || [])].some(p => core.normalize(p.name) === core.normalize(name));
      const inAway = [...match.awayXI, ...(match.awaySubs || [])].some(p => core.normalize(p.name) === core.normalize(name));
      if (match.id === 'tigre-argentinos-apertura-2026' && index === 0) return match.away;
      if (inHome === inAway) throw new Error('Requiere revisión editorial: ' + match.id + ' / ' + name);
      return inHome ? match.home : match.away;
    });
  }
  return match;
});
const counts = { matches: matches.length, clubs: new Set(matches.flatMap(m => [m.homeSlug, m.awaySlug])).size, scorers: core.eligible(matches, 'all', 'scorers').length, overrides };
if (counts.matches !== 255 || counts.clubs !== 30 || counts.scorers !== 220) throw new Error(JSON.stringify(counts));
const homonyms = [];
const missingRosterScorers = [];
for (const match of matches) {
  match.qualityWarnings = [];
  if (match.homeXI.length !== 11 || match.awayXI.length !== 11) throw new Error('XI incompleto: ' + match.id);
  const candidates = core.scorerCandidates(match);
  candidates.filter(p => p.rosterUnknown).forEach(p => missingRosterScorers.push({ matchId: match.id, team: p.team, name: p.name }));
  if (candidates.some(p => p.rosterUnknown)) {
    match.scorerIncomplete = true;
    match.qualityWarnings.push('Hay goleadores registrados sin coincidencia exacta en la alineación de origen.');
  }
  core.actualScorers(match);
  for (const team of [match.home, match.away]) {
    const side = team === match.home ? 'home' : 'away';
    const players = [...match[side + 'XI'], ...(match[side + 'Subs'] || [])];
    const duplicate = players.filter((p, i) => players.findIndex(q => core.normalize(q.name) === core.normalize(p.name)) !== i);
    if (duplicate.length) {
      homonyms.push({ matchId: match.id, team, names: duplicate.map(p => p.name) });
      match.qualityWarnings.push('La fuente contiene apellidos repetidos en ' + team + '.');
      if (duplicate.some(p => match.scorers.some((name, index) => core.normalize(name) === core.normalize(p.name) && match.scorerTeams[index] === team))) match.scorerAmbiguous = true;
    }
    if (players.some(p => /\./.test(p.name))) match.qualityWarnings.push('La fuente contiene nombres abreviados en ' + team + '.');
  }
  if (match.scorers.length !== match.homeGoals + match.awayGoals) throw new Error('Cantidad de goles inconsistente: ' + match.id);
  if (!candidates.length) throw new Error('Sin candidatos: ' + match.id);
}
if (new Set(matches.map(m => m.id)).size !== matches.length) throw new Error('IDs duplicados');
const collection = { id: 'apertura-2026', title: 'Apertura 2026', version: 1, description: 'Los 255 partidos del campeonato, desde la primera fecha hasta la final.', provenance: 'Importado del prototipo La Planilla, incluidas sus correcciones editoriales. Pendiente de auditoría histórica independiente.', quality: { homonyms, missingRosterScorers }, matches };
const target = path.join(root, 'data/campanas/apertura-2026.json');
fs.mkdirSync(path.dirname(target), { recursive: true });
fs.writeFileSync(target, JSON.stringify(collection, null, 2) + '\n');
console.log(JSON.stringify({ ...counts, playableScorers: core.eligible(matches, 'all', 'scorers').length, homonyms: homonyms.length, missingRosterScorers: missingRosterScorers.length }, null, 2));
