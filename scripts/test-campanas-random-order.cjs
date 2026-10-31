const test = require('node:test'), assert = require('node:assert/strict');
const path = require('node:path');
const C = require('../js/campanas-core.js'), P = require('../js/campanas-progress.js');
const catalog = require('../data/campanas/catalog.json').collections;
const collections = [require('../data/campanas/apertura-2026.json'), ...catalog.map(c=>require(path.join('..',c.file)))];

test('every team renders known positions in order without changing source indices, membership or data',()=>{
  for(const collection of collections) for(const match of collection.matches) for(const side of ['home','away']) {
    const players=match[side+'XI']||[], before=JSON.stringify(players), ordered=C.orderedLineup(players);
    assert.equal(JSON.stringify(players),before);
    assert.equal(ordered.length,players.length);
    assert.equal(new Set(ordered.map(row=>row.index)).size,players.length);
    for(const row of ordered) assert.equal(row.player,players[row.index]);
    const ranks=ordered.map(row=>C.positionRank(row.player.pos)).filter(rank=>rank>=0);
    assert.deepEqual(ranks,ranks.slice().sort((a,b)=>a-b),match.id+' / '+side);
    // Equal-position players retain the source order; unreported roles aren't invented.
    for(let rank=0;rank<4;rank++) {
      const indices=ordered.filter(row=>C.positionRank(row.player.pos)===rank).map(row=>row.index);
      assert.deepEqual(indices,indices.slice().sort((a,b)=>a-b));
    }
    if(players.every(p=>C.positionRank(p.pos)<0)) assert.deepEqual(ordered.map(row=>row.player),players);
  }
});

test('Caranta is first and Boca role corrections retain their sources and survive another import',()=>{
  const data=collections.find(c=>c.id==='boca-libertadores-2007');
  const apply=require('./apply-campanas-positions.cjs');
  for(const match of data.matches) for(const side of ['home','away']) {
    const players=match[side+'XI'];
    assert.equal(players.filter(p=>C.positionRank(p.pos)===0).length,1,match.id);
    assert.equal(C.positionRank(C.orderedLineup(players)[0].player.pos),0);
    for(const p of players) if(Object.hasOwn(p,'sourcePos')) assert.match(p.positionSource,/^https:\/\//);
  }
  const match=data.matches.find(m=>m.id==='espn-213122');
  const first=C.orderedLineup(match.awayXI)[0];
  assert.equal(first.player.name,'Caranta');assert.equal(first.index,6);
  const raw=structuredClone(match);raw.awayXI[6].pos='M';apply(raw,data.id);
  assert.deepEqual(raw,match);
});

test('random challenges use only eligible modes across all campaigns including 0–0s and incomplete games',()=>{
  for(const collection of collections) for(const match of collection.matches) {
    const eligible=C.matchModes(match),seen=new Set();
    for(let n=0;n<12;n++) {
      const pick=C.randomChallenge([match],[],null,()=>n/12);
      if(!eligible.length) {assert.equal(pick,null);continue;}
      assert.equal(pick.match,match);assert(eligible.includes(pick.mode));seen.add(pick.mode);
      if(!match.scorers.length) assert.notEqual(pick.mode,'scorers');
    }
    assert.deepEqual([...seen].sort(),eligible.slice().sort());
  }
});

test('random campaign avoids completed matches and immediate skip repeats, then prefers pending modes',()=>{
  const games=[{id:'a',modes:['formation','result']},{id:'b',modes:['result','scorers']},{id:'c',modes:['result']}];
  const entries=[{matchId:'a',mode:'formation'}];
  assert.equal(C.randomChallenge(games,entries,null,()=>0).match.id,'b');
  assert.equal(C.randomChallenge(games,entries,'b',()=>0).match.id,'c');
  assert.equal(C.randomChallenge([games[0]],entries,null,()=>0).mode,'result');
  assert.equal(C.randomChallenge([games[0]],[...entries,{matchId:'a',mode:'result'}],null,()=>0).mode,'formation');
  assert.equal(C.randomChallenge([],[],null),null);
  assert.equal(C.randomChallenge(games,[],null,()=>0.999).match.id,'c');
});

test('random is a persistent preference while scores remain attached to the actual challenge',()=>{
  const values=new Map(),storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)},error=e=>{throw e;};
  P.openProfile(storage,error).save({nickname:'Fede',mode:'random'});
  P.openActivity(storage,error).start('boca','bocajuniors','express','random');
  assert.equal(P.openProfile(storage,error).get().mode,'random');
  assert.equal(P.openActivity(storage,error).list()[0].mode,'random');
  P.open(storage,error).save('boca','match','result',20,1,'bocajuniors');
  assert.equal(P.open(storage,error).list()[0].mode,'result');
});
