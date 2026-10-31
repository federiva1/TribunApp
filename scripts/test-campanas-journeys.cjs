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
    const matches=Array.from({length:n},(_,i)=>({id:String(i),modes:['formation','result']}));
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
test('only formations advance campaigns; optional bonus scores never double completion', () => {
  const matches=[{id:'a',modes:['formation','result']},{id:'b',modes:['formation','result']}];
  const entries=[{collectionId:'one',matchId:'a',mode:'result',bestScore:20},
    {collectionId:'two',matchId:'b',mode:'formation',bestScore:33}];
  assert.equal(core.routeStatus(matches,entries,'one').done,0);
  entries.push({collectionId:'one',matchId:'a',mode:'formation',bestScore:0});
  let state=core.routeStatus(matches,entries,'one');
  assert.equal(state.done,1);assert.equal(state.score,20);assert(!state.complete);
  assert.deepEqual(state.remaining,[matches[1]]);
  entries.push({collectionId:'one',matchId:'b',mode:'formation',bestScore:33});
  entries.push({collectionId:'one',matchId:'b',mode:'result',bestScore:-5});
  state=core.routeStatus(matches,entries,'one');
  assert(state.complete);assert.equal(state.score,53,'legacy negative scores do not reduce the new campaign total');
  assert(!core.routeStatus([],entries,'one').complete);
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
test('formation challenges follow the selected club at home or away, or both with all teams', () => {
  const match={homeSlug:'bocajuniors',awaySlug:'arsenal'};
  assert.deepEqual(core.formationSides(match,'bocajuniors'),['home']);
  assert.deepEqual(core.formationSides(match,'arsenal'),['away']);
  assert.deepEqual(core.formationSides(match,'all'),['home','away']);
  assert.deepEqual(core.formationSides(match,'unknown'),[]);
});
test('one-club lineups do not complete another club or both teams; old 22-player records stay valid', () => {
  const values=new Map(),storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};
  const store=progress.open(storage,e=>{throw e;});
  store.save('one','a','formation',33,1,'bocajuniors','bocajuniors');
  assert.equal(core.progressForClub(store.list(),'bocajuniors').length,1);
  assert.equal(core.progressForClub(store.list(),'arsenal').length,0);
  assert.equal(core.progressForClub(store.list(),'all').length,0);
  store.save('one','a','formation',30,1,'arsenal','arsenal');
  store.save('one','a','formation',25,1,'bocajuniors','bocajuniors');
  assert.equal(store.list().length,2);
  assert.equal(core.progressForClub(store.list(),'bocajuniors')[0].bestScore,33);
  assert.equal(core.progressForClub(store.list(),'arsenal')[0].bestScore,30);
  assert.equal(core.routeStatus([{id:'a',modes:['formation']}],store.list(),'one').score,33,'totals use best mark without counting separate scopes twice');
  const legacy={...store.list()[0],bestScore:66};delete legacy.formationClub;delete legacy.playClub;
  for(const club of ['all','bocajuniors','arsenal']) assert.equal(core.progressForClub([legacy,...store.list()],club)[0].bestScore,66);
  assert.equal(progress.open(storage,e=>{throw e;}).list().length,2);
});
test('personal campaigns include starts and legacy results, never unplayed catalog entries or rival contexts', () => {
  const historical=index.collections.find(c=>c.id==='boca-libertadores-2007');
  const tournament=index.collections.find(c=>c.id==='apertura-2026');
  const started={collectionId:tournament.id,club:'bocajuniors',route:'express',mode:'formation',startedAt:'2026-10-30T12:00:00Z'};
  assert.deepEqual(core.personalCampaigns(index.collections,[],[]),[]);
  let mine=core.personalCampaigns(index.collections,[started],[]);
  assert.equal(mine.length,1);assert.equal(mine[0].club,'bocajuniors');
  const old={collectionId:historical.id,matchId:historical.matches[0].id,mode:'result',bestScore:20,updatedAt:'2026-10-29T12:00:00Z'};
  mine=core.personalCampaigns(index.collections,[started],[old]);
  assert.equal(mine.length,2);assert(mine.every(c=>c.club==='bocajuniors'));
  assert(!mine.some(c=>c.item.id==='boca-liga-2022'));
  const newer={...old,playClub:'bocajuniors',collectionId:tournament.id,matchId:tournament.matches.find(m=>[m.homeSlug,m.awaySlug].includes('bocajuniors')).id};
  assert.equal(core.personalCampaigns(index.collections,[started],[newer]).length,1,'activity and scores merge the same campaign context');
});
test('activity survives reload, tracks only the latest visit per campaign and works without storage', () => {
  const raw=new Map(),storage={getItem:k=>raw.get(k),setItem:(k,v)=>raw.set(k,v)};
  const store=progress.openActivity(storage,e=>{throw e;});
  store.start('one','bocajuniors','express','formation');
  store.start('one','bocajuniors','classic','result');
  assert.equal(store.list().length,1);assert.equal(store.list()[0].route,'classic');
  assert.equal(progress.openActivity(storage,e=>{throw e;}).list().length,1);
  const errors=[],blocked=progress.openActivity({getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}},e=>errors.push(e));
  blocked.start('one','all','express','formation');assert.equal(blocked.list().length,1);assert.equal(errors.length,2);
});
