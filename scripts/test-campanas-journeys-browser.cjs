const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const assert=require('node:assert/strict');
const core=require('../js/campanas-core.js');
const root=path.resolve(__dirname,'..');
const url='http://campanas.test/campanas.html';
const KEY='tribunapp.campanas.progress.v1', PROFILE='tribunapp.campanas.profile.v1';
function entry(collection,match,mode='result',score=20) {
  return {collectionId:collection.id,matchId:match.id,mode,bestScore:score,lastScore:score,attempts:1,
    completedAt:'2026-10-01T10:00:00.000Z',updatedAt:'2026-10-01T10:00:00.000Z'};
}
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844}}), errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/*',async route=>{
      const target=new URL(route.request().url());
      if(target.hostname!=='campanas.test') return route.abort();
      const file=path.resolve(root,'.'+decodeURIComponent(target.pathname));
      if(!file.startsWith(root+path.sep)||!fs.existsSync(file)) return route.fulfill({status:404,body:''});
      const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.webp':'image/webp'};
      return route.fulfill({body:fs.readFileSync(file),contentType:types[path.extname(file)]||'application/octet-stream'});
    });
    const collection=require('../data/campanas/argentinos-clausura-2010.json');
    const express=core.routeMatches(collection.matches,'all','express');
    await page.goto(url);await page.locator('.historical-library').waitFor();
    await page.evaluate(({KEY,record})=>localStorage.setItem(KEY,JSON.stringify({schemaVersion:1,entries:[record]})),{KEY,record:entry(collection,express[0])});
    await page.goto(url+'?collection='+collection.id+'&route=express');
    await page.locator('[data-route="express"]').waitFor();
    for(const [key,count] of [['express',5],['classic',10],['complete',19]]) assert.match(await page.locator(`[data-route="${key}"]`).textContent(),new RegExp(count+' partidos'));
    assert.match(await page.locator('.route-status').textContent(),/1 de 5/);
    await page.locator('[data-mode="result"]').click();
    await page.locator('#nickname-cancel').click();
    assert.equal(await page.locator('#result-form').count(),0,'cancel must not start a round');
    await page.locator('[data-mode="result"]').click();
    await page.locator('#nickname-input').fill('  ');await page.locator('#nickname-form .primary').click();
    assert(await page.locator('#nickname-dialog').isVisible());
    await page.locator('#nickname-input').fill('<Fede>');await page.locator('#nickname-form .primary').click();
    assert.equal(await page.locator('.nickname').textContent(),'<Fede>','nickname must be rendered as text');
    assert.equal(await page.locator('.nickname fede').count(),0);
    assert.equal(await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries.length,KEY),1,'old records survive nickname creation');
    const seen=new Set([express[0].id]);
    for(let i=1;i<5;i++) {
      const names=await page.locator('.score-team span').allTextContents();
      const match=express.find(m=>m.home===names[0]&&m.away===names[1]);
      assert(match);assert(!seen.has(match.id),'next must prioritize an unplayed route match');seen.add(match.id);
      await page.locator('#result-form input[name="home"]').fill(String(i===1?99:match.homeGoals));
      await page.locator('#result-form input[name="away"]').fill(String(i===1?99:match.awayGoals));
      await page.locator('#result-form .primary').click();
      assert.match(await page.locator('.journey-strip').textContent(),new RegExp((i+1)+' / 5'));
      await page.locator('.completion [data-action="next"]').click();
    }
    await page.locator('.medal-hero').waitFor();
    const medal=page.locator(`[data-medal-collection="${collection.id}"]`);
    assert(await medal.evaluate(el=>el.classList.contains('complete')));
    assert.equal(await medal.locator('.medal-badge.earned').count(),1);
    assert.equal(await medal.locator('.medal-badge.started').count(),2);
    assert.match(await medal.textContent(),/5\/10/);assert.match(await medal.textContent(),/5\/19/);
    assert.match(await page.locator('.medal-hero').textContent(),/75 PUNTOS/,'wrong result counts completion but still deducts points');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-medallero-mobile.png'),fullPage:true});
    await page.locator('#medal-club').selectOption('all');
    assert.equal(await page.locator('.medal-card').count(),1,'only played campaigns belong in the medal cabinet');
    await page.setViewportSize({width:1440,height:1100});
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-medallero-desktop.png'),fullPage:true});
    await page.locator('#medal-state').selectOption('complete');
    assert.equal(await page.locator('.medal-card').count(),1);
    await page.locator('#medal-route').selectOption('complete');
    assert.equal(await page.locator('.medal-card').count(),0);
    await page.locator('#medal-state').selectOption('started');
    assert.equal(await page.locator('.medal-card').count(),1);
    await page.locator('[data-medal-open]').click();
    assert.equal(await page.locator('[data-route="complete"]').getAttribute('aria-pressed'),'true');
    assert.match(await page.locator('.route-status').textContent(),/5 de 19/);
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-recorridos-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-recorridos-mobile.png'),fullPage:true});
    await page.locator('[data-action="archive"]').click();
    const firstRecord=page.locator('.archive-card').first();
    assert.equal(await firstRecord.locator('[data-replay-mode="result"]').count(),0,'archive offers only unplayed challenges');
    await firstRecord.locator('[data-replay-mode="formation"]').click();
    assert.equal(await page.locator('[data-player-form]').count(),11);
    await page.locator('[data-action="home"]').click();
    await page.locator('[data-action="profile"]').click();
    await page.locator('#nickname-input').fill('Bicho');await page.locator('#nickname-form .primary').click();
    await page.reload();await page.locator('.route-status').waitFor();
    assert.equal(await page.locator('.nickname').textContent(),'Bicho');
    assert.match(await page.locator('.route-status').textContent(),/5 de 19/);

    // A 0–0 must not trap a scorers-only player in an endless repeat loop.
    const central=require('../data/campanas/central-copaargentina-2018.json');
    const goals=core.eligible(central.matches,'all','scorers');
    const last=goals.at(-1);
    await page.evaluate(({KEY,records})=>localStorage.setItem(KEY,JSON.stringify({schemaVersion:1,entries:records})),{KEY,records:goals.slice(0,-1).map(m=>entry(central,m,'scorers'))});
    await page.goto(url+'?collection='+central.id+'&route=complete');
    await page.locator('[data-mode="scorers"]').click();
    assert.deepEqual(await page.locator('.score-team span').allTextContents(),[last.home,last.away]);
    for (const id of core.actualScorers(last)) await page.locator('[data-goal]').evaluateAll((buttons,id)=>buttons.find(b=>b.dataset.goal===id).click(),id);
    await page.locator('[data-action="confirm-scorers"]').click();
    await page.locator('.completion [data-action="next"]').click();
    assert.match(await page.locator('h1').textContent(),/Seguimos con otro reto/);
    assert.equal(await page.locator('[data-replay-mode="scorers"]').count(),0);
    await page.locator('[data-replay-mode="result"]').click();
    await page.locator('#result-form input[name="home"]').fill('0');
    await page.locator('#result-form input[name="away"]').fill('0');
    await page.locator('#result-form .primary').click();
    assert.match(await page.locator('.medal-earned').textContent(),/Completaste Completo/);
    await page.locator('.completion [data-action="next"]').click();
    const centralMedal=page.locator(`[data-medal-collection="${central.id}"]`);
    assert.equal(await centralMedal.locator('.medal-badge.earned').count(),3);

    // No profile or storage access must still allow a complete in-memory session.
    const blocked=await browser.newPage();
    await blocked.route('**/*',async route=>{
      const target=new URL(route.request().url());if(target.hostname!=='campanas.test') return route.abort();
      const file=path.resolve(root,'.'+decodeURIComponent(target.pathname));
      if(!file.startsWith(root+path.sep)||!fs.existsSync(file)) return route.fulfill({status:404,body:''});
      const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.webp':'image/webp'};
      return route.fulfill({body:fs.readFileSync(file),contentType:types[path.extname(file)]||'application/octet-stream'});
    });
    await blocked.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw Error('blocked')}}));
    await blocked.goto(url+'?collection=central-copaargentina-2018&route=express');
    await blocked.locator('[data-mode="result"]').click();
    await blocked.locator('#nickname-input').fill('Invitado');await blocked.locator('#nickname-form .primary').click();
    assert(await blocked.locator('#storage-notice').isVisible());
    assert.equal(await blocked.locator('#result-form').count(),1);
    await blocked.close();
    assert.deepEqual(errors,[]);
    console.log('PASS: route completion, all medal states/filters, old progress, nickname cancellation/rename, no XSS, resume, responsive layouts, 0–0 transition and blocked storage.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
