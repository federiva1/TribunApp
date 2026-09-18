// Public ESPN match facts, cached outside the repository. Never imports annual squads.
// node scripts/import-historical-campaigns.cjs [--inventory]
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const definitions = require('./historical-campaigns.json');
const lineupOverrides = require('./historical-lineup-overrides.json');
const core = require('../js/campanas-core.js');
const cache = path.join(os.tmpdir(), 'tribunapp-historical-espn-v1');
fs.mkdirSync(cache, { recursive: true });
const base = 'https://site.api.espn.com/apis/site/v2/sports/soccer/';
async function get(url) {
  const file = path.join(cache, crypto.createHash('sha256').update(url).digest('hex') + '.json');
  if (fs.existsSync(file)) return JSON.parse(fs.readFileSync(file, 'utf8'));
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(30000) });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
      const data = await res.json();
      fs.writeFileSync(file, JSON.stringify(data));
      return data;
    } catch (error) { if (attempt === 2) throw error; await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1))); }
  }
}
const original = require('../data/campanas/apertura-2026.json');
const localTeams = new Map();
for (const m of original.matches) for (const side of ['home', 'away']) localTeams.set(core.normalize(m[side]).replace(/[^a-z0-9]/g, ''), { name: m[side], slug: m[side+'Slug'] });
for (const c of definitions) localTeams.set(core.normalize(c.club).replace(/[^a-z0-9]/g, ''), { name: c.club, slug: c.clubSlug });
function teamInfo(team) {
  const known = definitions.find(d => d.team === String(team.id));
  if (known) return { name: known.club, slug: known.clubSlug, crest: null };
  // Location suffixes distinguish different clubs (e.g. Independiente Chivilcoy).
  const normalized = core.normalize(team.displayName).replace(/[^a-z0-9]/g, '');
  const candidate = localTeams.get(normalized);
  const found = candidate && !definitions.some(d => d.clubSlug === candidate.slug) ? candidate : null;
  return { name: found?.name || team.displayName, slug: found?.slug || 'espn-' + team.id, crest: found ? null : (team.logo || team.logos?.[0]?.href || `https://a.espncdn.com/i/teamlogos/soccer/500/${team.id}.png`) };
}
function player(raw) {
  const a = raw.athlete;
  return { playerId: String(a.id), n: raw.jersey && /^\d+$/.test(raw.jersey) ? Number(raw.jersey) : null, name: a.lastName || a.displayName, fullName: a.displayName, accepted_answers: [...new Set([a.lastName, a.displayName, a.fullName].filter(Boolean))], pos: raw.position?.abbreviation || null };
}
function convert(summary, event, def, sourceApi) {
  const competition = summary.header?.competitions?.[0] || event.competitions[0];
  const type = competition.status?.type || {};
  const standard = ['STATUS_FULL_TIME','STATUS_FINAL','STATUS_FINAL_AET','STATUS_FINAL_PEN'].includes(type.name);
  const match = { id: 'espn-' + event.id, dateISO: event.date, date: new Intl.DateTimeFormat('es-AR', { timeZone:'America/Argentina/Buenos_Aires', day:'2-digit', month:'short', year:'numeric' }).format(new Date(event.date)), zone: summary.header?.season?.name || def.title, stadium: summary.gameInfo?.venue?.fullName || competition.venue?.fullName || 'Estadio no informado', source: `https://www.espn.com/soccer/match/_/gameId/${event.id}`, sourceApi, retrievedAt: new Date().toISOString(), scorers: [], scorerTeams: [], goalEvents: [], incidents: [], qualityWarnings: [], availability: { formation:false, scorers:false, result:false } };
  const rosters = new Map(), idPlayers = new Map();
  const incomingIds = new Set((summary.keyEvents || []).filter(e=>e.type?.type==='substitution' && !e.shootout).map(e=>String(e.participants?.[0]?.athlete?.id)));
  for (const side of ['home','away']) {
    const comp = competition.competitors.find(c => c.homeAway === side);
    const info = teamInfo(comp.team);
    match[side] = info.name; match[side+'Slug'] = info.slug; if (info.crest) match[side+'Crest'] = info.crest;
    match[side+'Goals'] = Number(comp.score);
    if (comp.shootoutScore != null) (match.shootout ||= {})[side] = Number(comp.shootoutScore);
    const rawRoster = summary.rosters?.find(r => String(r.team.id) === String(comp.id))?.roster || [];
    const uniqueRoster = new Map();
    for (const raw of rawRoster) {
      const previous = uniqueRoster.get(String(raw.athlete.id));
      if (!previous || (raw.stats?.length || 0) > (previous.stats?.length || 0)) uniqueRoster.set(String(raw.athlete.id),raw);
    }
    const roster = [...uniqueRoster.values()];
    rosters.set(side, roster);
    const players = roster.map(player);
    for (const p of players) {
      if (players.filter(q => core.normalize(q.name) === core.normalize(p.name)).length > 1) {
        p.name = p.fullName;
        p.accepted_answers = [p.fullName];
      }
      idPlayers.set(p.playerId, {p,side,team:info.name});
    }
    match[side+'XI'] = roster.filter(p => p.starter).map(r=>idPlayers.get(String(r.athlete.id)).p);
    // Some legacy feeds flag substitutes/unused players as starters. A recorded
    // appearance with zero substitute appearances independently identifies a start.
    const statisticalStarters = roster.filter(r=>r.stats?.some(s=>s.name==='appearances'&&s.value===1) && r.stats?.some(s=>s.name==='subIns'&&s.value===0));
    if (statisticalStarters.length === 11) {
      match[side+'XI'] = statisticalStarters.map(r=>idPlayers.get(String(r.athlete.id)).p);
      match[side+'LineupEvidence'] = 'appearance=1, subIns=0 in match statistics';
    }
    if (match[side+'XI'].length > 11) {
      const starters = match[side+'XI'].filter(p=>!incomingIds.has(p.playerId));
      if (starters.length === 11) match[side+'XI'] = starters;
    }
    // subbedIn is missing in some old records; substitution events supplement it below.
    match[side+'Subs'] = roster.filter(p => !p.starter && p.subbedIn).map(r=>idPlayers.get(String(r.athlete.id)).p);
  }
  // Older feeds repeat the same event under different IDs. Use clock seconds,
  // period, event kind and primary player; distinct goals stay distinct.
  const keys = [...new Map((summary.keyEvents || []).map(e=>[JSON.stringify([e.type?.type,e.period?.number,e.clock?.value,e.team?.id,e.participants?.[0]?.athlete?.id,e.shootout]),e])).values()];
  for (const e of keys.filter(e=>e.type?.type==='substitution' && !e.shootout)) {
    const incoming = e.participants?.[0]?.athlete;
    if (!incoming) continue;
    let found = idPlayers.get(String(incoming.id));
    if (!found) {
      const side = competition.competitors.find(c=>String(c.id)===String(e.team?.id))?.homeAway;
      if (!side) continue;
      const p = player({athlete:incoming}); found = {p,side,team:match[side]}; idPlayers.set(p.playerId,found);
    }
    if (!match[found.side+'XI'].some(p=>p.playerId===found.p.playerId) && !match[found.side+'Subs'].some(p=>p.playerId===found.p.playerId)) match[found.side+'Subs'].push(found.p);
  }
  for (const e of keys) {
    const kind = e.type?.type || '';
    if (e.shootout || Number(e.period?.number) === 5) continue;
    if (/goal|card|substitution/.test(kind)) match.incidents.push({type:kind,minute:e.clock?.displayValue || '',playerIds:(e.participants||[]).map(p=>String(p.athlete?.id)).filter(Boolean)});
    if (!e.scoringPlay || !(kind.startsWith('goal') || ['own-goal','penalty---scored','penalty-scored'].includes(kind))) continue;
    const found = idPlayers.get(String(e.participants?.[0]?.athlete?.id));
    if (!found) { match.qualityWarnings.push('Autor de gol sin ficha de jugador: '+e.id); continue; }
    const ownGoal = kind === 'own-goal';
    match.scorers.push(found.p.name); match.scorerTeams.push(found.team);
    match.goalEvents.push({playerId:found.p.playerId,team:found.team,minute:e.clock?.displayValue || '',ownGoal,penalty:/penalty/.test(kind)});
  }
  const supplement = lineupOverrides[match.id];
  if (supplement) {
    match.supplementalSources = [supplement.source, supplement.additionalSource].filter(Boolean);
    match.editorialNote = supplement.note || 'XI, ingresados y goles contrastados en crónica del partido; dorsales y posiciones no informados se conservan nulos.';
    for (const side of ['home','away']) for (const group of ['XI','Subs']) {
      match[side+group] = supplement[side+group].map((entry,index)=>{
        const [fullName,name]=entry.split('|');
        return {playerId:`editorial-${event.id}-${side}-${group}-${index}`,name,fullName,accepted_answers:[name,fullName],n:null,pos:group==='XI'&&index===0?'GK':null};
      });
      match[side+'LineupEvidence'] = supplement.source;
    }
    match.scorers=[];match.scorerTeams=[];match.goalEvents=[];
    for(const [side,name,minute,penalty] of supplement.goals){
      const author=[...match[side+'XI'],...match[side+'Subs']].find(p=>p.name===name);
      if(!author) throw new Error('Autor editorial sin identidad: '+match.id+'/'+name);
      match.scorers.push(name);match.scorerTeams.push(match[side]);
      match.goalEvents.push({playerId:author.playerId,team:match[side],minute,penalty:!!penalty,ownGoal:false});
    }
    // ESPN has no roster here; its orphan event IDs cannot describe these players.
    match.incidents=[];
    match.qualityWarnings=[];
  }
  match.score = `${match.homeGoals} — ${match.awayGoals}`;
  if (!standard) match.qualityWarnings.push('Estado excepcional: '+type.name+'; fuera de los retos hasta revisión.');
  match.availability.result = standard && [match.homeGoals,match.awayGoals].every(n=>Number.isInteger(n)&&n>=0);
  match.availability.formation = match.availability.result && ['home','away'].every(side => match[side+'XI'].length===11 && new Set(match[side+'XI'].map(p=>p.playerId)).size===11 && match[side+'XI'].every(p=>p.name && !/[\uFFFD]/.test(p.name)));
  if (!match.availability.formation) match.qualityWarnings.push('No hay once completo verificable de ambos equipos o el partido no terminó normalmente.');
  const goalTotals = {home:0,away:0};
  for (const g of match.goalEvents) {let side=g.team===match.home?'home':'away';if(g.ownGoal)side=side==='home'?'away':'home';goalTotals[side]++;}
  const goalsOK = goalTotals.home===match.homeGoals && goalTotals.away===match.awayGoals;
  let identitiesOK = false;
  try { const authors=core.actualScorers(match); identitiesOK=authors.length===match.scorers.length && !core.scorerCandidates(match).some(p=>p.rosterUnknown); } catch (_) {}
  match.availability.scorers = match.availability.formation && match.scorers.length>0 && goalsOK && identitiesOK;
  if (!goalsOK) match.qualityWarnings.push('Los eventos de gol no coinciden con el marcador; goleadores deshabilitado.');
  return match;
}
async function main() {
  const index = [], audit = [];
  for (const def of definitions) {
    const scoreboard = await get(base + def.league + '/scoreboard?dates=' + def.year + '&limit=1000');
    const events = (scoreboard.events||[]).filter(e => e.competitions?.[0]?.competitors.some(c=>String(c.id)===def.team) && (!def.from||e.date>=def.from) && (!def.to||e.date<def.to));
    console.log(def.id, 'fixture', events.length, '/', def.expected);
    if (events.length !== def.expected) {audit.push({id:def.id,error:'Cantidad de partidos distinta de la esperada',expected:def.expected,actual:events.length,events:events.map(e=>({id:e.id,name:e.name,date:e.date}))});continue;}
    if (process.argv.includes('--inventory')) continue;
    const matches = [];
    for (let offset=0;offset<events.length;offset+=3) {
      const batch=await Promise.all(events.slice(offset,offset+3).map(async event=>{
        const url=base+def.league+'/summary?event='+event.id;
        try { return convert(await get(url),event,def,url); }
        catch(error) {
          console.log('  pendiente',event.id,error.message);
          const match=convert({},event,def,url);
          match.qualityWarnings.push('Ficha detallada no disponible al importar.');
          return match;
        }
      })); matches.push(...batch);
    }
    matches.sort((a,b)=>a.dateISO.localeCompare(b.dateISO));
    const coverage = Object.fromEntries(['formation','scorers','result'].map(mode=>[mode,matches.filter(m=>m.availability[mode]).length]));
    const collection = {id:def.id,title:def.title,version:1,club:def.club,clubSlug:def.clubSlug,year:def.year,achievement:def.achievement,description:def.achievement+'. El recorrido completo, partido por partido.',provenance:'Fichas públicas de ESPN. Cobertura y validación estructural por reto; sin reconstruir alineaciones desde planteles anuales.',expectedMatches:def.expected,coverage,matches};
    fs.writeFileSync(path.join(root,'data/campanas',def.id+'.json'),JSON.stringify(collection)+'\n');
    index.push({id:def.id,title:def.title,club:def.club,clubSlug:def.clubSlug,year:def.year,achievement:def.achievement,matchCount:matches.length,coverage,file:'data/campanas/'+def.id+'.json'});
    audit.push({id:def.id,coverage,warnings:matches.filter(m=>m.qualityWarnings.length).map(m=>({id:m.id,source:m.source,warnings:m.qualityWarnings}))});
    console.log('  retos',JSON.stringify(coverage));
  }
  fs.writeFileSync(path.join(cache,'audit.json'),JSON.stringify(audit,null,2));
  console.log('Auditoría:',path.join(cache,'audit.json'));
  if (process.argv.includes('--inventory')) return;
  if(index.length!==24) throw new Error('No publicar catálogo incompleto: '+index.length+'/24. Revisar auditoría.');
  fs.writeFileSync(path.join(root,'data/campanas/catalog.json'),JSON.stringify({version:1,collections:index})+'\n');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
