const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const C=require('../js/campanas-core.js');
const root=path.resolve(__dirname,'..'),base='http://campanas.test/campanas.html',KEY='tribunapp.campanas.progress.v1';
const collections=[1990,2022].map(year=>require('../data/campanas/argentina-mundial-'+year+'.json'));
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const u=new URL(route.request().url());if(u.hostname!=='campanas.test')return route.abort();
   const f=path.resolve(root,'.'+decodeURIComponent(u.pathname));
   if(!f.startsWith(root+path.sep)||!fs.existsSync(f))return route.fulfill({status:404,body:''});
   const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp'};
   return route.fulfill({body:fs.readFileSync(f),contentType:types[path.extname(f)]||'application/octet-stream'});
  });
  await page.goto(base);const card=page.locator('.club-campaign-card[data-club="argentina"]');await card.waitFor();
  assert.equal(await card.locator('.historical-card').count(),2);
  assert(await card.locator('img').evaluate(img=>img.complete&&img.naturalWidth>0&&img.src.endsWith('/argentina.svg')));
  await card.screenshot({path:path.join(os.tmpdir(),'campanas-argentina-card.png')});
  await page.setViewportSize({width:390,height:844});
  await page.locator('.section-bar [data-action="quick-play"]').click();
  await page.locator('[data-quick-club="argentina"]').click();
  assert(await page.locator('[data-quick-club="argentina"] img').evaluate(img=>img.naturalWidth>0));
  await page.locator('[data-quick-collection="argentina-mundial-2022"]').click();
  assert.deepEqual(await page.locator('[data-quick-route]').allTextContents(),['Clásico 4 partidos','Completo 7 partidos']);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(os.tmpdir(),'campanas-argentina-selector-mobile.png'),fullPage:true});
  await page.locator('[data-close-quick]').click();
  const cases=[[collections[0],'espn-197984'],[collections[0],'espn-198016'],[collections[1],'espn-633807'],[collections[1],'espn-633836'],[collections[1],'espn-633850']];
  for(const [collection,id] of cases) {
   const match=collection.matches.find(m=>m.id===id),stamp='2026-10-31T12:00:00Z';
   const entries=collection.matches.filter(m=>m.id!==id).map(m=>({collectionId:collection.id,matchId:m.id,mode:'formation',bestScore:33,attempts:1,completedAt:stamp,updatedAt:stamp,flowVersion:2,formationClub:'argentina'}));
   await page.evaluate(({KEY,entries})=>localStorage.setItem(KEY,JSON.stringify({schemaVersion:1,entries})),{KEY,entries});
   await page.goto(base+'?collection='+collection.id+'&route=complete');
   await page.locator('.route-card').first().waitFor();
   assert.deepEqual(await page.locator('.route-card').allTextContents(),['Clásico 4 partidos','Completo 7 partidos']);
   await page.locator('[data-action="campaign-play"]').click();
   if(await page.locator('#nickname-input').count()){await page.locator('#nickname-input').fill('Prueba Argentina');await page.locator('#nickname-form .primary').click();}
   assert.equal(await page.locator('[data-player-form]').count(),11);
   assert.equal(await page.locator('.score-value').textContent(),'? — ?');
   if(id==='espn-197984')await page.screenshot({path:path.join(os.tmpdir(),'campanas-argentina-1990-mobile.png'),fullPage:true});
   const side=match.homeSlug==='argentina'?'home':'away';
   for(const [i,p] of match[side+'XI'].entries()){await page.locator('#guess-'+side+'-'+i).fill(p.accepted_answers[0]);await page.locator('#guess-'+side+'-'+i).press('Enter');}
   assert.match(await page.locator('.completion').textContent(),/33 puntos/);
   await page.locator('[data-bonus="result"]').click();
   await page.locator('#result-form input[name="home"]').fill(String(match.homeGoals));await page.locator('#result-form input[name="away"]').fill(String(match.awayGoals));await page.locator('#result-form .primary').click();
   assert.equal(await page.locator('.points').textContent(),'53 pts · partido');
   if(match.availability.scorers){
    await page.locator('[data-bonus="scorers"]').click();
    for(const goal of C.actualScorers(match))await page.locator('[data-goal]').evaluateAll((buttons,id)=>{const b=buttons.find(b=>b.dataset.goal===id);if(!b)throw Error('Missing scorer '+id);b.click();},goal);
    await page.locator('[data-action="confirm-scorers"]').click();
    assert.equal(await page.locator('.points').textContent(),'73 pts · partido');
   }else assert.equal(await page.locator('[data-bonus="scorers"]').count(),0);
   const saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
   assert.equal(saved.filter(e=>e.matchId===id).length,match.availability.scorers?3:2);
   assert.equal(await page.locator('[data-bonus]').count(),0);
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: AFA card and mobile selector; 4/7 routes; Argentina XI only; USSR 1990, goalless shootout, substitute scorer, own goal and 2022 final; scores and saved progress.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
