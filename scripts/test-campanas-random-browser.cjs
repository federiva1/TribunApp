// Regression for retired random/standalone preferences: old profiles must enter the unified campaign.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base='http://campanas.test/campanas.html';
const data=require('../data/campanas/boca-libertadores-2007.json');
const KEY='tribunapp.campanas.progress.v1',PROFILE='tribunapp.campanas.profile.v1',ACTIVITY='tribunapp.campanas.activity.v1';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url());if(url.hostname!=='campanas.test')return route.abort();
   const file=path.resolve(root,'.'+decodeURIComponent(url.pathname));if(!file.startsWith(root+path.sep)||!fs.existsSync(file))return route.fulfill({status:404,body:''});
   const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.webp':'image/webp'};
   return route.fulfill({body:fs.readFileSync(file),contentType:types[path.extname(file)]||'application/octet-stream'});
  });
  await page.goto(base);await page.locator('.historical-library').waitFor();
  for(const mode of ['random','result','scorers']){
   await page.evaluate(({PROFILE,ACTIVITY,mode,id})=>{
    localStorage.setItem(PROFILE,JSON.stringify({nickname:'Fede',route:'complete',mode}));
    localStorage.setItem(ACTIVITY,JSON.stringify([{collectionId:id,club:'bocajuniors',route:'complete',mode,startedAt:'2026-10-01T10:00:00Z'}]));
   },{PROFILE,ACTIVITY,mode,id:data.id});
   await page.reload();await page.locator('.section-bar [data-action="quick-play"]').click();
   assert.equal(await page.locator('#quick-mode').count(),0);assert.equal(await page.locator('[data-quick-collection][aria-pressed="true"]').getAttribute('data-quick-collection'),data.id);
   await page.locator('.quick-submit').click();await page.locator('[data-player-form]').first().waitFor();
   assert.equal(await page.locator('[data-player-form]').count(),11);assert.equal(await page.locator('.random-label,[data-mode],[data-action="random-play"]').count(),0);
   assert.equal(await page.locator('#result-form,[data-goal],[data-bonus]').count(),0,'no bonus before completing formation');
   assert.equal(await page.locator('.score-value').textContent(),'? — ?');
   const first=await page.locator('.score-team span').allTextContents();
   await page.locator('.game-actions [data-action="next"]').click();
   assert.notDeepEqual(await page.locator('.score-team span').allTextContents(),first);
   assert.equal(await page.locator('[data-player-form]').count(),11,'skipping remains in formation');
   assert.equal(await page.evaluate(PROFILE=>JSON.parse(localStorage.getItem(PROFILE)).mode,PROFILE),'formation');
   await page.locator('[data-action="home"]').click();
  }
  // Seeing a result in an older rival-club run cannot unlock it again under Boca.
  const target=data.matches.find(m=>m.id==='espn-213122'),stamp='2026-10-01T10:00:00Z';
  const entries=data.matches.map(m=>({collectionId:data.id,matchId:m.id,mode:'formation',bestScore:33,attempts:1,completedAt:stamp,updatedAt:stamp,formationClub:m.id===target.id?target.homeSlug:'bocajuniors',...(m.id===target.id?{}:{flowVersion:2})}));
  await page.evaluate(({KEY,entries})=>localStorage.setItem(KEY,JSON.stringify({schemaVersion:1,entries})),{KEY,entries});
  await page.goto(base+'?collection='+data.id+'&route=complete');await page.locator('[data-action="campaign-play"]').click();
  assert.equal(await page.locator('.score-value').textContent(),'? — ?','old rival records must not expose the score on a new lineup');
  assert.equal(await page.locator('.player-row').first().getAttribute('data-player'),'away-6');
  await page.locator('[data-action="toggle-rival"]').click();
  const tops=await page.locator('.team-sheet').evaluateAll(els=>els.map(el=>el.getBoundingClientRect().top));assert(Math.abs(tops[0]-tops[1])<1);
  assert.equal(await page.locator('#rival-sheet input').count(),0);
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  for(const [i,p] of target.awayXI.entries()) {const input=page.locator('#guess-away-'+i);await input.fill(p.accepted_answers?.[0]||p.name);await input.press('Enter');}
  assert.equal(await page.locator('.points').textContent(),'33 pts · partido','rival formation points are not duplicated');
  assert.equal(await page.locator('[data-bonus="result"]').count(),0);assert.equal(await page.locator('[data-bonus="scorers"]').count(),1);
  await page.locator('[data-action="medals"]').click();assert.equal(await page.locator('.medal-track').count(),2);
  assert.deepEqual(errors,[]);
  console.log('PASS: retired random/result/scorers preferences, remembered launcher, formation-only skips, cross-club result exposure, preserved sheet ordering/alignment and mobile medal rows.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
