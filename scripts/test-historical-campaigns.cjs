const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const core = require('../js/campanas-core.js');
const catalog = require('../data/campanas/catalog.json').collections;
const definitions = require('./historical-campaigns.json');
const collections = catalog.map(item => JSON.parse(fs.readFileSync(path.join(__dirname,'..',item.file),'utf8')));

test('24 historical collections cover exactly the requested 12 clubs twice', () => {
  assert.equal(catalog.length,24);
  const clubs = Object.groupBy(catalog,item=>item.clubSlug);
  assert.deepEqual(Object.keys(clubs).sort(), ['bocajuniors','riverplate','sanlorenzo','racingclub','independiente','rosariocentral','newellsoldboys','argentinosjuniors','gimnasialp','estudiantes','huracan','lanus'].sort());
  for (const group of Object.values(clubs)) assert.equal(group.length,2);
  assert.equal(new Set(catalog.map(c=>c.id)).size,24);
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
  assert.equal(all.length,323);
  assert.equal(all.filter(m=>m.availability.formation).length,322);
  assert.equal(all.filter(m=>m.availability.scorers).length,289);
  assert.equal(all.filter(m=>m.availability.result).length,322);
  const supplements=all.filter(m=>m.supplementalSources);
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
