const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const C=require('../js/campanas-core.js'),catalog=require('../data/campanas/catalog.json').collections;
const root=path.resolve(__dirname,'..'),base='http://campanas.test/campanas.html',KEY='tribunapp.campanas.progress.v1';
const boca=require('../data/campanas/boca-libertadores-2007.json');
async function assets(page){await page.route('**/*',async route=>{
  const url=new URL(route.request().url());if(url.hostname!=='campanas.test')return route.abort();
  const file=path.resolve(root,'.'+decodeURIComponent(url.pathname));
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file))return route.fulfill({status:404,body:''});
  const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.webp':'image/webp'};
  return route.fulfill({body:fs.readFileSync(file),contentType:types[path.extname(file)]||'application/octet-stream'});
});}
const stamp='2026-10-31T10:00:00Z';
function entry(collection,match,mode='formation',extra={}){return {collectionId:collection.id,matchId:match.id,mode,bestScore:mode==='formation'?33:20,attempts:1,completedAt:stamp,updatedAt:stamp,flowVersion:2,...extra};}
async function seed(page,entries){await page.evaluate(({KEY,entries})=>localStorage.setItem(KEY,JSON.stringify({schemaVersion:1,entries})),{KEY,entries});}
async function open(page,data){await page.goto(base+'?collection='+data.id+'&route=complete');await page.locator('[data-action="campaign-play"]').waitFor();}
async function solve(page,match,sides){for(const side of sides)for(const [i,p] of match[side+'XI'].entries()){
  const input=page.locator(`#guess-${side}-${i}`);if(!await input.count())continue;
  await input.fill(p.accepted_answers?.[0]||p.name);await input.press('Enter');
}}
async function result(page,home,away){await page.locator('#result-form input[name="home"]').fill(String(home));await page.locator('#result-form input[name="away"]').fill(String(away));await page.locator('#result-form .primary').click();}
async function goal(page,id){await page.locator('[data-goal]').evaluateAll((buttons,id)=>buttons.find(b=>b.dataset.goal===id).click(),id);}
async function centered(page){
  const boxes=await page.evaluate(()=>{
    const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return {center:r.left+r.width/2,top:r.top,bottom:r.bottom,width:r.width};};
    return {score:rect('.score-value'),separator:rect('.result-separator'),inputs:rect('.result-inputs'),button:rect('#result-form .primary')};
  });
  assert(Math.abs(boxes.score.center-boxes.separator.center)<1,'score and editable separator share the center');
  assert(Math.abs(boxes.score.center-boxes.button.center)<1,'button is centered below');
  assert(boxes.button.top>boxes.inputs.bottom);assert(boxes.button.width<300);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
}
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));await assets(page);
  await page.goto(base);await page.locator('.historical-library').waitFor();
  assert.equal(await page.locator('.historical-card').count(),24);assert.equal(await page.locator('.crest-wall img').count(),30);
  assert.equal(await page.locator('[data-mode],[data-action="random-play"]').count(),0);
  await page.locator('[data-action="medals"]').click();assert.equal(await page.locator('.medal-card').count(),0);
  await page.locator('.section-bar [data-action="quick-play"]').click();
  assert.equal(await page.locator('#quick-mode').count(),0);
  await page.locator('[data-quick-club="bocajuniors"]').click();await page.locator(`[data-quick-collection="${boca.id}"]`).click();await page.locator('[data-quick-route="complete"]').click();
  await page.locator('.quick-submit').click();await page.locator('#nickname-input').fill('<Fede>');await page.locator('#nickname-form .primary').click();
  assert.equal(await page.locator('[data-player-form]').count(),11);assert.equal(await page.locator('.score-value').textContent(),'? — ?');
  await page.locator('[data-action="medals"]').click();assert.equal(await page.locator('.medal-card').count(),1);
  assert.equal(await page.locator('.medal-hero script').count(),0);
  // Every collection enters formation with a hidden result; no standalone/random choices remain.
  for(const item of [{id:'apertura-2026'},...catalog]){
    await open(page,item);assert.equal(await page.locator('[data-mode],[data-action="random-play"]').count(),0);
    await page.locator('[data-action="campaign-play"]').click();
    assert.equal(await page.locator('[data-player-form]').count(),item.id==='apertura-2026'?22:11,item.id);
    assert.equal(await page.locator('.score-value').textContent(),'? — ?');
    assert.equal(await page.locator('[data-bonus]').count(),0);
  }
  // Reported Toluca match: positional ordering, draft preservation and aligned opponent.
  const target=boca.matches.find(m=>m.id==='espn-213122');
  const rest=boca.matches.filter(m=>m.id!==target.id).map(m=>entry(boca,m));
  await seed(page,rest);await open(page,boca);await page.locator('[data-action="campaign-play"]').click();
  assert.equal(await page.locator('.player-row').first().getAttribute('data-player'),'away-6');
  await page.locator('#guess-away-6').fill('borrador');await page.locator('[data-action="toggle-rival"]').click();
  assert.equal(await page.locator('#guess-away-6').inputValue(),'borrador');
  const sheets=await page.locator('.team-sheet').evaluateAll(els=>els.map(el=>({top:el.getBoundingClientRect().top,width:el.getBoundingClientRect().width})));
  assert(Math.abs(sheets[0].top-sheets[1].top)<1);assert(Math.abs(sheets[0].width-sheets[1].width)<1);
  assert.equal(await page.locator('#rival-sheet input').count(),0);
  await page.locator('[data-action="toggle-rival"]').click();await page.locator('[data-hint="away-6"]').click();
  await solve(page,target,['away']);
  assert.match(await page.locator('.completion').textContent(),/32 puntos/);
  assert.equal(await page.locator('.score-value').textContent(),'? — ?');
  assert.equal(await page.locator('[data-bonus="result"]').count(),1);assert.equal(await page.locator('[data-bonus="scorers"]').count(),0);
  // Archive/reload must not spoil a result whose bonus has not been attempted.
  await page.locator('[data-action="archive"]').click();
  assert.equal(await page.locator('.archive-card').filter({has:page.locator(`[data-open-match="${target.id}"]`)}).locator('.archive-score b').textContent(),'? — ?');
  await page.reload();await page.locator('[data-action="archive"]').click();await page.locator(`[data-open-match="${target.id}"]`).click();
  assert.equal(await page.locator('.score-value').textContent(),'? — ?');
  await page.locator('[data-bonus="result"]').click();assert.equal(await page.locator('.team-sheet').count(),0);
  await centered(page);await page.screenshot({path:path.join(os.tmpdir(),'campanas-bonus-resultado-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await centered(page);
  await page.screenshot({path:path.join(os.tmpdir(),'campanas-bonus-resultado-mobile.png'),fullPage:true});
  await result(page,99,99);assert.equal(await page.locator('.points').textContent(),'32 pts · partido');
  assert.equal(await page.locator('.completion.neutral').count(),1);assert.equal(await page.locator('.score-value').textContent(),'2 — 0');
  assert.equal(await page.locator('[data-bonus="result"]').count(),0);await page.locator('[data-bonus="scorers"]').click();
  const actual=C.actualScorers(target),wrong=C.scorerCandidates(target).find(p=>!actual.includes(p.id)).id;
  await goal(page,actual[0]);await goal(page,wrong);await page.locator('[data-action="confirm-scorers"]').click();
  assert.match(await page.locator('.completion h2').textContent(),/1 de 2/);
  assert.equal(await page.locator('.points').textContent(),'42 pts · partido');
  assert.equal(await page.locator('.goal-wrong').count(),1);assert.equal(await page.locator('.goal-correct').count(),2);
  assert.equal(await page.locator('[data-bonus]').count(),0);assert.equal(await page.locator('[data-replay]').count(),0);
  await page.screenshot({path:path.join(os.tmpdir(),'campanas-bonus-parcial-mobile.png'),fullPage:true});
  let saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
  assert.equal(saved.find(e=>e.matchId===target.id&&e.mode==='result').bestScore,0);
  assert.equal(saved.find(e=>e.matchId===target.id&&e.mode==='scorers').bestScore,10);
  assert.equal(saved.find(e=>e.matchId===target.id&&e.mode==='formation').flowVersion,2);
  await page.locator('.completion [data-action="next"]').click();assert.equal(await page.locator('.medal-badge.earned').count(),3);
  // A 0–0 gets a result bonus but never a scorer bonus. Optional means no medal prerequisite.
  const zero=boca.matches[0];await seed(page,[entry(boca,zero)]);await open(page,boca);
  await page.locator('[data-action="archive"]').click();await page.locator(`[data-open-match="${zero.id}"]`).click();
  await page.locator('[data-bonus="result"]').click();await result(page,0,0);
  assert.equal(await page.locator('.points').textContent(),'53 pts · partido');assert.equal(await page.locator('[data-bonus]').count(),0);
  await page.locator('.completion [data-action="next"]').click();assert.equal(await page.locator('[data-player-form]').count(),11);
  assert.equal(await page.locator('.score-value').textContent(),'? — ?');
  // Explicitly skipping result locks it before displaying scorer candidates; third hint gives zero.
  await seed(page,[entry(boca,target)]);await open(page,boca);await page.locator('[data-action="archive"]').click();await page.locator(`[data-open-match="${target.id}"]`).click();
  await page.locator('[data-action="skip-result"]').click();
  saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
  assert(saved.find(e=>e.mode==='result').skipped);assert.equal(await page.locator('.score-value').textContent(),'2 — 0');
  for(let i=0;i<3;i++)await page.locator('[data-action="scorer-hint"]').click();
  for(const id of actual)await goal(page,id);await page.locator('[data-action="confirm-scorers"]').click();
  assert.equal(await page.locator('.points').textContent(),'33 pts · partido');
  await page.reload();await page.locator('[data-action="archive"]').click();await page.locator(`[data-open-match="${target.id}"]`).click();
  assert.equal(await page.locator('[data-bonus]').count(),0);
  // Legacy formation already showed the score, so it cannot offer a newly scored result bonus.
  const old=entry(boca,target);delete old.flowVersion;
  await seed(page,[old]);await open(page,boca);await page.locator('[data-action="archive"]').click();await page.locator(`[data-open-match="${target.id}"]`).click();
  assert.equal(await page.locator('[data-bonus="result"]').count(),0);assert.equal(await page.locator('[data-bonus="scorers"]').count(),1);
  assert.equal(await page.locator('.score-value').textContent(),'? — ?','even a saved formation opens without displaying the score');
  // Reveal during formation: keep drafts, points and help; persist only the 0-point result.
  await seed(page,rest);await open(page,boca);await page.locator('[data-action="campaign-play"]').click();
  await page.locator('[data-hint="away-6"]').click();
  await page.locator('#guess-away-6').fill('borrador');
  const hintPlaceholder=await page.locator('#guess-away-6').getAttribute('placeholder');
  assert.equal(await page.locator('.score-value').textContent(),'? — ?');
  await page.locator('[data-action="reveal-result"]').click();
  assert.equal(await page.locator('.score-value').textContent(),target.score);
  assert.equal(await page.locator('#guess-away-6').inputValue(),'borrador');
  assert.equal(await page.locator('#guess-away-6').getAttribute('placeholder'),hintPlaceholder);
  assert.equal(await page.locator('.points').textContent(),'0 pts · partido');
  assert.equal(await page.locator('[data-player-form]').count(),11);
  assert.equal(await page.locator('[data-bonus], .completion').count(),0);
  assert.match(await page.locator('.stage-trail li').nth(1).textContent(),/✓ResultadoRevelado · 0 pts/);
  saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
  assert.equal(saved.filter(e=>e.matchId===target.id).length,1);
  assert.equal(saved.find(e=>e.matchId===target.id).mode,'result');
  assert.equal(saved.find(e=>e.matchId===target.id).bestScore,0);
  assert(saved.find(e=>e.matchId===target.id).skipped);
  // Reload cannot unlock the result bonus again; re-revealing does not create another attempt.
  await page.reload();await page.locator('[data-action="campaign-play"]').click();
  assert.equal(await page.locator('.score-value').textContent(),'? — ?');
  await page.locator('[data-action="reveal-result"]').click();
  saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
  assert.equal(saved.find(e=>e.matchId===target.id&&e.mode==='result').attempts,1);
  // A planilla fully solved with hints (0 points) still offers scorers before Next.
  for(const [i,p] of target.awayXI.entries()) {
    const hint=page.locator(`[data-hint="away-${i}"]`);
    let uses=0;while(await hint.count()) {assert(++uses<60);await hint.click();}
  }
  assert.match(await page.locator('.completion').textContent(),/\+0 puntos/);
  assert.equal(await page.locator('[data-bonus="result"]').count(),0);
  assert.equal(await page.locator('[data-bonus="scorers"]').count(),1);
  assert.equal(await page.locator('.completion [data-action="next"]').count(),0);
  await page.screenshot({path:path.join(os.tmpdir(),'campanas-formacion-bonus-mobile.png'),fullPage:true});
  await page.locator('[data-bonus="scorers"]').click();
  for(const id of actual)await goal(page,id);await page.locator('[data-action="confirm-scorers"]').click();
  assert.equal(await page.locator('.points').textContent(),'20 pts · partido');
  assert.equal(await page.locator('.completion [data-action="next"]').count(),1);
  await page.locator('.completion [data-action="next"]').click();
  assert.equal(await page.locator('.medal-badge.earned').count(),3);
  // Previously earned bonus points survive an explicit reveal on an unfinished formation.
  await seed(page,[...rest,entry(boca,target,'result')]);await open(page,boca);
  await page.locator('[data-action="campaign-play"]').click();
  assert.equal(await page.locator('.score-value').textContent(),'? — ?');
  await page.locator('[data-action="reveal-result"]').click();
  assert.equal(await page.locator('.points').textContent(),'20 pts · partido');
  saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
  assert.equal(saved.find(e=>e.matchId===target.id&&e.mode==='result').attempts,1);
  // A goalless match must not leak its 0–0 through the stage trail before reveal.
  await seed(page,[]);await open(page,boca);await page.locator('[data-action="campaign-play"]').click();
  assert.equal(await page.locator('.score-value').textContent(),'? — ?');
  assert.doesNotMatch(await page.locator('.stage-trail').textContent(),/Sin goles/);
  await page.screenshot({path:path.join(os.tmpdir(),'campanas-ver-resultado-mobile.png'),fullPage:true});
  await page.locator('[data-action="reveal-result"]').click();await solve(page,zero,['away']);
  assert.equal(await page.locator('[data-bonus]').count(),0);
  assert.match(await page.locator('.completion').textContent(),/terminó sin goles/);
  assert.equal(await page.locator('.completion [data-action="next"]').count(),1);
  // Madrid's optional two-XI challenge still completes and saves the all-teams scope.
  const river=require('../data/campanas/river-libertadores-2018.json'),final=river.matches.find(m=>m.id==='espn-528144');
  await seed(page,river.matches.filter(m=>m.id!==final.id).map(m=>entry(river,m)));await open(page,river);
  await page.locator('[data-action="campaign-play"]').click();await page.locator('[data-action="both-teams"]').click();
  assert.equal(await page.locator('[data-player-form]').count(),22);await solve(page,final,['home','away']);
  assert.match(await page.locator('.completion').textContent(),/66 puntos/);
  saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
  assert.equal(saved.find(e=>e.matchId===final.id&&e.mode==='formation').formationClub,'all');
  // Storage failure keeps a playable in-memory campaign and reports the limitation.
  const blocked=await browser.newPage();await assets(blocked);
  await blocked.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw Error('blocked');}}));
  await open(blocked,boca);await blocked.locator('[data-action="campaign-play"]').click();
  await blocked.locator('#nickname-input').fill('Invitado');await blocked.locator('#nickname-form .primary').click();
  assert(await blocked.locator('#storage-notice').isVisible());await solve(blocked,zero,['away']);
  await blocked.locator('[data-bonus="result"]').click();await result(blocked,0,0);
  assert.equal(await blocked.locator('.points').textContent(),'53 pts · partido');await blocked.close();
  assert.deepEqual(errors,[]);
  console.log('PASS: 25 campaign starts; unified flow; hidden result and archive reload; centered desktop/mobile inputs; partial/zero/skip bonuses; medals; ordered aligned rival; legacy progress; Madrid 22; blocked storage.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
