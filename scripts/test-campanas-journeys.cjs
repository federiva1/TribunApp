const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../js/campanas-core.js');
const progress = require('../js/campanas-progress.js');
const index = require('../data/campanas/recorridos.json');
const build = require('./build-campanas-journeys.cjs');

test('medal index matches source collections, has no answers, and excludes suspended games', () => {
  assert.deepEqual(index, JSON.parse(JSON.stringify(build())));
  for (const collection of index.collections) {
    for (const m of collection.matches) {
      assert(!('score' in m)); assert(!('scorers' in m)); assert(!('homeXI' in m));
    }
    const full = core.routeMatches(collection.matches, 'all', 'complete');
    assert(full.every(m => m.modes.length));
    assert.equal(new Set(full.map(m => m.id)).size, full.length);
  }
  const river = index.collections.find(c=>c.id==='river-libertadores-2015');
  assert.equal(core.routeMatches(river.matches,'all','complete').length,13);
});
test('route lengths are proportional, nested, stable, chronological and include the last match', () => {
  for (let n=0;n<=255;n++) {
    const matches=Array.from({length:n},(_,i)=>({id:String(i),modes:['result']}));
    const express=core.routeMatches(matches,'all','express');
    const classic=core.routeMatches(matches,'all','classic');
    const full=core.routeMatches(matches,'all','complete');
    assert.equal(express.length,Math.min(5,Math.ceil(n/3)));
    assert.equal(classic.length,Math.ceil(n/2));
    assert.equal(full.length,n);
    assert(express.every(m=>classic.includes(m)));
    assert(classic.every(m=>full.includes(m)));
    for (const route of [express,classic,full]) {
      assert.equal(new Set(route.map(m=>m.id)).size,route.length);
      assert.deepEqual(route.map(m=>Number(m.id)),route.map(m=>Number(m.id)).sort((a,b)=>a-b));
      if (n) assert(route.includes(matches.at(-1)));
    }
  }
});
test('one finished challenge per match earns medals, independent of score, with no mode or collection inflation', () => {
  const matches=[{id:'a',modes:['formation','result']},{id:'b',modes:['result']}];
  const records=[{collectionId:'one',matchId:'a',mode:'result',bestScore:-5},{collectionId:'one',matchId:'a',mode:'formation',bestScore:0},
    {collectionId:'two',matchId:'b',mode:'result',bestScore:20},{collectionId:'one',matchId:'b',mode:'scorers',bestScore:20}];
  const state=core.routeStatus(matches,records,'one');
  assert.equal(state.done,1);assert.equal(state.score,-5);assert(!state.complete);
  assert.deepEqual(state.remaining,[matches[1]]);
  records.push({collectionId:'one',matchId:'b',mode:'result',bestScore:0});
  assert(core.routeStatus(matches,records,'one').complete);
  assert(!core.routeStatus([],records,'one').complete);
});
test('Apertura club routes only include that club and unavailable scorer modes stay unavailable', () => {
  const collection=require('../data/campanas/apertura-2026.json');
  const mirror=index.collections.find(c=>c.id===collection.id);
  for(const route of ['express','classic','complete']) {
    const selected=core.routeMatches(collection.matches,'argentinosjuniors',route);
    assert(selected.every(m=>[m.homeSlug,m.awaySlug].includes('argentinosjuniors')));
    assert.deepEqual(selected.map(m=>m.id),core.routeMatches(mirror.matches,'argentinosjuniors',route).map(m=>m.id));
    assert(core.eligible(selected,'all','scorers').every(m=>m.scorers.length));
  }
});
test('nickname and preferences preserve existing progress and best marks across shorter and longer routes', () => {
  const raw=new Map(); const storage={getItem:key=>raw.get(key),setItem:(key,value)=>raw.set(key,value)};
  const saved=progress.open(storage,e=>{throw e;});
  saved.save('one','a','result',20,1);
  const original=raw.get(progress.KEY);
  const profile=progress.openProfile(storage,e=>{throw e;});
  profile.save({nickname:'  Fede  ',route:'classic'});
  assert.equal(raw.get(progress.KEY),original);
  assert.deepEqual(progress.openProfile(storage,e=>{throw e;}).get(),{nickname:'Fede',route:'classic',mode:'formation'});
  profile.save({nickname:'Otro apodo'});
  assert.equal(raw.get(progress.KEY),original);
  saved.save('one','a','result',20,1);saved.save('one','a','result',-5,1);
  assert.equal(saved.list().length,1);assert.equal(saved.list()[0].bestScore,20);
});
test('local profile validates preferences, bounds nicknames and survives unavailable storage in memory', () => {
  const errors=[];
  const profile=progress.openProfile({getItem:()=>JSON.stringify({nickname:123,route:'unknown',mode:'bad'}),setItem(){throw Error('quota');}},e=>errors.push(e));
  assert.deepEqual(profile.get(),{nickname:'',route:'express',mode:'formation'});
  profile.save({nickname:'X'.repeat(100),mode:'result'});
  assert.equal(profile.get().nickname.length,24);assert.equal(profile.get().mode,'result');assert.equal(errors.length,1);
  const malformed=progress.openProfile({getItem:()=>'{bad'},e=>errors.push(e));
  assert.equal(malformed.get().nickname,'');assert.equal(errors.length,2);
});
