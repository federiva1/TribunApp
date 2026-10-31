const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const core = require('../js/campanas-core.js');
const catalog = require('../data/campanas/catalog.json').collections;
const definitions = require('./historical-campaigns.json');
const collections = catalog.map(item => JSON.parse(fs.readFileSync(path.join(__dirname,'..',item.file),'utf8')));

test('26 historical collections cover 12 clubs and Argentina twice', () => {
  assert.equal(catalog.length,26);
  const clubs = Object.groupBy(catalog,item=>item.clubSlug);
  assert.deepEqual(Object.keys(clubs).sort(), ['bocajuniors','riverplate','sanlorenzo','racingclub','independiente','rosariocentral','newellsoldboys','argentinosjuniors','gimnasialp','estudiantes','huracan','lanus','argentina'].sort());
  for (const group of Object.values(clubs)) assert.equal(group.length,2);
  assert.equal(new Set(catalog.map(c=>c.id)).size,26);
});

test('complete fixtures, provenance and honest mode coverage in every campaign', () => {
  for(const c of collections) {
    const def=definitions.find(d=>d.id===c.id),meta=catalog.find(d=>d.id===c.id);
    assert.equal(c.matches.length,def.expected,c.id);
    assert.equal(new Set(c.matches.map(m=>m.id)).size,c.matches.length,c.id);
    for(const mode of ['formation','scorers','result']) {
      const playable=core.eligible(c.matches,'all',mode);
      assert.equal(playable.length,c.coverage[mode],c.id+'/'+mode);
      assert.equal(playable.length,meta.coverage[mode]);
      assert(playable.length>0,c.id+' must offer '+mode);
    }
    for(const m of c.matches) {
      assert([m.homeSlug,m.awaySlug].includes(c.clubSlug));
      assert.match(m.source,/^https:\/\/www\.espn\.com\/soccer\/match\//);
      assert(m.sourceApi && m.retrievedAt);
      assert.equal(m.score,`${m.homeGoals} — ${m.awayGoals}`);
      if(m.availability.formation) for(const side of ['home','away']) {
        assert.equal(m[side+'XI'].length,11,m.id);
        assert.equal(new Set(m[side+'XI'].map(p=>p.playerId)).size,11,m.id);
      }
      if(m.availability.scorers) {
        assert(m.scorers.length>0);
        assert.equal(m.scorers.length,m.homeGoals+m.awayGoals,m.id);
        const totals={home:0,away:0};
        for(const g of m.goalEvents){let s=g.team===m.home?'home':'away';if(g.ownGoal)s=s==='home'?'away':'home';totals[s]++;}
        assert.deepEqual(totals,{home:m.homeGoals,away:m.awayGoals},m.id);
        const actual=core.actualScorers(m);
        assert.equal(core.scoreScorers(actual,m,0).score,20);
        const eliminated=new Set();
        for(let used=0;used<3;used++)for(const id of core.scorerHintPlan(m,eliminated,used))eliminated.add(id);
        assert.deepEqual(new Set(core.scorerCandidates(m).filter(p=>!eliminated.has(p.id)).map(p=>p.id)),new Set(actual));
      }
    }
  }
});

test('known finals keep match goals separate from shootouts and include extra time',()=>{
  const chivilcoy = collections.find(c=>c.id==='estudiantes-copaargentina-2023').matches.find(m=>m.id==='espn-659119');
  assert.match(chivilcoy.away,/Chivilcoy/);
  assert.notEqual(chivilcoy.awaySlug,'independiente');
  const last=id=>collections.find(c=>c.id===id).matches.at(-1);
  assert.equal(last('boca-libertadores-2007').score,'0 — 2');
  assert.deepEqual(last('boca-libertadores-2007').scorers,['Riquelme','Riquelme']);
  assert.equal(last('river-libertadores-2018').score,'3 — 1');
  assert.equal(last('central-copaargentina-2018').score,'1 — 1');
  assert.equal(last('huracan-copaargentina-2014').score,'0 — 0');
  assert.equal(last('huracan-copaargentina-2014').availability.scorers,false);
  const suspended=collections.find(c=>c.id==='river-libertadores-2015').matches.filter(m=>!m.availability.result);
  assert.equal(suspended.length,1);
  assert.equal(suspended[0].availability.formation,false);
});

test('editorial supplements complete every finished lineup with explicit sources',()=>{
  const all=collections.flatMap(c=>c.matches);
  assert.equal(all.length,337);
  assert.equal(all.filter(m=>m.availability.formation).length,336);
  assert.equal(all.filter(m=>m.availability.scorers).length,302);
  assert.equal(all.filter(m=>m.availability.result).length,336);
  const supplements=all.filter(m=>m.supplementalSources && ![m.homeSlug,m.awaySlug].includes("argentina"));
  assert.equal(supplements.length,7);
  for(const m of all) if(m.availability.result) assert.equal(m.availability.formation,true,m.id);
  for(const m of supplements) {
    assert(m.supplementalSources.every(url=>url.startsWith('https://')));
    for(const side of ['home','away']) for(const p of [...m[side+'XI'],...m[side+'Subs']]) {
      assert.equal(p.n,null,'Do not invent historical shirt numbers');
      assert(p.playerId.startsWith('editorial-'));
    }
  }
  const central=supplements.find(m=>m.id==='espn-508553');
  assert.equal(central.homeSubs.find(p=>p.name==='Herrera').playerId,central.goalEvents[2].playerId);
  assert.equal(central.goalEvents[2].playerId,central.goalEvents[5].playerId);
});


test('Argentina World Cups preserve verified lineups, substitutions, own goals and shootouts',()=>{
  const c90=collections.find(c=>c.id==='argentina-mundial-1990');
  const c22=collections.find(c=>c.id==='argentina-mundial-2022');
  for(const c of [c90,c22]) {
    assert.equal(c.matches.length,7);
    assert.equal(core.routeMatches(c.matches,'argentina','classic').length,4);
    assert.equal(core.routeMatches(c.matches,'argentina','complete').length,7);
    for(const m of c.matches) {
      assert.deepEqual(m.qualityWarnings,[]);
      const side=m.homeSlug==='argentina'?'home':'away';
      assert.deepEqual(core.formationSides(m,'argentina'),[side]);
      const xi=m[side+'XI'];
      assert.equal(xi.length,11);
      assert(xi.every(p=>Number.isInteger(p.n)&&p.n>0));
      assert.equal(core.positionRank(core.orderedLineup(xi)[0].player.pos),0);
    }
  }
  const soviet=c90.matches.find(m=>m.id==='espn-197984');
  assert(soviet.homeXI.some(p=>p.name==='Pumpido'&&p.n===1));
  assert(soviet.homeSubs.some(p=>p.name==='Goycochea'&&p.n===12));
  assert(soviet.homeXI.some(p=>p.name==='Troglio'&&p.pos==='M'));
  assert(c90.matches[0].homeXI.some(p=>p.name==='Fabbri'&&p.n===11));
  assert.equal(c90.matches.find(m=>m.id==='espn-198011').stadium,'Delle Alpi');
  const yug=c90.matches.find(m=>m.id==='espn-198016');
  assert(yug.homeXI.some(p=>p.name==='Stojković'));
  assert(!yug.homeXI.some(p=>p.fullName.includes('Stanojkov')));
  assert.equal(yug.score,'0 — 0');assert.equal(yug.availability.scorers,false);
  assert.deepEqual(yug.shootout,{home:2,away:3});
  assert.deepEqual(c22.matches.at(-1).shootout,{home:4,away:2});
  assert.equal(c22.matches.at(-1).score,'3 — 3');
  assert.equal(c22.matches.at(-1).goalEvents.length,6);
  const mexico=c22.matches.find(m=>m.id==='espn-633807');
  assert(mexico.homeSubs.some(p=>p.name==='Fernández'));
  assert(core.actualScorers(mexico).includes('Selección Argentina|Fernández'));
  const australia=c22.matches.find(m=>m.id==='espn-633836');
  assert.equal(australia.goalEvents.filter(g=>g.ownGoal).length,1);
  assert.equal(c90.coverage.scorers,6);assert.equal(c22.coverage.scorers,7);
});
