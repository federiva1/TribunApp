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

test('bonus sequence protects unseen results, including reloads, skips and old scorer games',()=>{
  const match=collections.find(c=>c.id==='boca-libertadores-2007').matches.find(m=>m.id==='espn-213122');
  const values=new Map(),storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)},error=e=>{throw e;};
  let store=P.open(storage,error);
  assert.deepEqual(C.pendingModes(match,[]),['formation']);
  store.save('boca',match.id,'formation',33,1,'bocajuniors','bocajuniors',{flowVersion:2});
  store=P.open(storage,error);
  assert.deepEqual(C.pendingModes(match,store.list()),['result']);
  assert.equal(C.resultRevealed(match,store.list()),false);
  store.save('boca',match.id,'result',0,1,'bocajuniors','all',{flowVersion:2,skipped:true});
  store=P.open(storage,error);
  assert(store.list().find(e=>e.mode==='result').skipped);
  assert(C.resultRevealed(match,store.list()));
  assert.deepEqual(C.pendingModes(match,store.list()),['scorers']);
  store.save('boca',match.id,'scorers',10,1);
  assert.deepEqual(C.pendingModes(match,store.list()),[]);
  const legacy=[{matchId:match.id,mode:'formation',bestScore:33}];
  assert(C.resultRevealed(match,legacy),'old formation screens already exposed the result');
  assert.deepEqual(C.pendingModes(match,legacy),['scorers']);
  legacy.push({matchId:match.id,mode:'scorers',bestScore:0});
  assert.deepEqual(C.pendingModes(match,legacy),[]);
  const newClub=[{matchId:match.id,mode:'formation',flowVersion:2}];
  assert.deepEqual(C.pendingModes(match,newClub,legacy),['scorers'],'changing club cannot unlock an exposed result');
  const zero=collections[0].matches.find(m=>!m.scorers.length);
  assert.deepEqual(C.pendingModes(zero,[{matchId:zero.id,mode:'formation',flowVersion:2}]),['result']);
  assert.deepEqual(C.pendingModes(zero,[{matchId:zero.id,mode:'formation',flowVersion:2},{matchId:zero.id,mode:'result'}]),[]);
});

test('scorer bonus rewards partial goals, respects repeated scorers and never deducts points',()=>{
  const match=collections.find(c=>c.id==='boca-libertadores-2007').matches.find(m=>m.id==='espn-213122');
  const [a,b]=C.actualScorers(match);
  const wrong=C.scorerCandidates(match).find(p=>![a,b].includes(p.id)).id;
  assert.deepEqual(C.scoreScorers([a,wrong],match,0),{correct:false,score:10,matched:1,total:2,wrong:1});
  assert.deepEqual([0,1,2,3].map(h=>C.scoreScorers([a,wrong],match,h).score),[10,7,4,0]);
  assert.equal(C.scoreScorers([wrong,wrong],match,0).score,0);
  assert.equal(C.scoreScorers([a,a],match,0).score,10,'a goal cannot be counted twice');
  const double={...match,scorers:[match.scorers[0],match.scorers[0]],scorerTeams:[match.scorerTeams[0],match.scorerTeams[0]]};
  assert.equal(C.scoreScorers([a,a],double,0).score,20);
  assert.equal(C.scoreScorers([a,wrong],double,0).score,10);
});
