const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const assert=require('node:assert/strict');
const core=require('../js/campanas-core.js');
const root=path.resolve(__dirname,'..'),base='http://campanas.test/campanas.html';
const KEY='tribunapp.campanas.progress.v1';
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.route('**/*',async route=>{
      const url=new URL(route.request().url());if(url.hostname!=='campanas.test') return route.abort();
      const file=path.resolve(root,'.'+decodeURIComponent(url.pathname));
      if(!file.startsWith(root+path.sep)||!fs.existsSync(file)) return route.fulfill({status:404,body:''});
      const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.webp':'image/webp'};
      return route.fulfill({body:fs.readFileSync(file),contentType:types[path.extname(file)]||'application/octet-stream'});
    });
    await page.goto(base);await page.locator('.historical-library').waitFor();
    assert(await page.locator('.section-bar [data-action="quick-play"]').evaluate(el=>el.getBoundingClientRect().bottom<innerHeight),'play is above the fold');
    assert(await page.locator('.hero [data-action="quick-play"]').evaluate(el=>el.getBoundingClientRect().bottom<innerHeight));
    assert.equal(await page.locator('.historical-card > span').count(),0,'campaign achievements no longer appear');
    await page.locator('[data-action="medals"]').click();
    assert.equal(await page.locator('.medal-card').count(),0);
    assert.match(await page.locator('.empty-state').textContent(),/Tu primera campaña/);
    await page.locator('.section-bar [data-action="quick-play"]').click();
    await page.locator('#quick-collection').selectOption('boca-libertadores-2007');
    await page.locator('#quick-route').selectOption('complete');
    await page.locator('#quick-mode').selectOption('formation');
    assert(await page.locator('#quick-club-label').isHidden());
    assert.match(await page.locator('.quick-summary').textContent(),/sólo el once/);
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-jugar-mobile.png')});
    await page.locator('.quick-submit').click();
    await page.locator('#nickname-input').fill('Fede');await page.locator('#nickname-form .primary').click();
    assert.equal(await page.locator('[data-player-form]').count(),11);
    await page.locator('[data-action="medals"]').click();
    assert.equal(await page.locator('.medal-card').count(),1,'a started game belongs to the user before completion');
    assert.equal(await page.locator('[data-medal-collection="apertura-2026"]').count(),0,'unplayed tournament must stay out');
    await page.reload();await page.locator('[data-action="medals"]').click();
    assert.equal(await page.locator('.medal-card').count(),1,'started campaign survives reload');
    await page.locator('.section-bar [data-action="quick-play"]').click();
    assert.equal(await page.locator('#quick-collection').inputValue(),'boca-libertadores-2007','quick play remembers the last campaign');
    await page.locator('.quick-submit').click();
    const data=require('../data/campanas/boca-libertadores-2007.json');
    const names=await page.locator('.score-team span').allTextContents();
    const match=data.matches.find(m=>m.home===names[0]&&m.away===names[1]);
    const side=match.homeSlug===data.clubSlug?'home':'away',rival=side==='home'?'away':'home';
    assert.equal(await page.locator(`[data-player-form^="${rival}-"]`).count(),0);
    assert.equal(await page.locator('.team-sheet').count(),1);
    assert.match(await page.locator('#game-message').textContent(),/0 \/ 11/);
    const input=page.locator(`#guess-${side}-0`);
    await input.fill('respuesta en curso');
    await page.locator('[data-action="toggle-rival"]').click();
    assert.equal(await input.inputValue(),'respuesta en curso');
    assert.equal(await page.locator('#rival-sheet .player-name').count(),11);
    assert.equal(await page.locator('#rival-sheet input').count(),0);
    assert.equal(await page.locator('#rival-sheet [data-hint]').count(),0);
    assert.equal(await page.locator('.points').textContent(),'0 pts','opening reference is free');
    await page.locator('[data-action="toggle-rival"]').click();
    assert.equal(await input.inputValue(),'respuesta en curso');
    await page.locator(`[data-hint="${side}-0"]`).click();
    await input.fill('');
    assert.match(await input.getAttribute('placeholder'),/_/);
    assert.equal(await page.locator('[data-player-form]').count(),11);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-once-mobile.png'),fullPage:true});
    await page.setViewportSize({width:1440,height:1100});
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-once-desktop.png'),fullPage:true});
    for(const [i,player] of match[side+'XI'].entries()) {
      await page.locator(`#guess-${side}-${i}`).fill(player.accepted_answers?.[0]||player.name);
      await page.locator(`#guess-${side}-${i}`).press('Enter');
    }
    assert.match(await page.locator('.completion').textContent(),/32 puntos/);
    assert.match(await page.locator('#game-message').textContent(),/Bien/);
    const saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
    assert.equal(saved.length,1);assert.equal(saved[0].formationClub,'bocajuniors');assert.equal(saved[0].bestScore,32);
    await page.locator('[data-action="archive"]').click();
    assert.equal(await page.locator('[data-replay-mode="formation"]').count(),0);

    // Selecting all clubs keeps the original two-lineup game.
    await page.goto(base+'?collection=apertura-2026&club=all&route=express');
    await page.locator('[data-mode="formation"]').click();
    assert.equal(await page.locator('[data-player-form]').count(),22);
    assert.equal(await page.locator('[data-action="toggle-rival"]').count(),0);

    // The Madrid final remains optional and cannot be enabled after seeing the rival answers.
    const river=require('../data/campanas/river-libertadores-2018.json');
    const final=river.matches.find(m=>m.id==='espn-528144');
    const entries=river.matches.filter(m=>m.id!==final.id).map(m=>({collectionId:river.id,matchId:m.id,mode:'result',bestScore:20,attempts:1,completedAt:'2026-10-01T10:00:00Z',updatedAt:'2026-10-01T10:00:00Z'}));
    await page.evaluate(({KEY,entries})=>localStorage.setItem(KEY,JSON.stringify({schemaVersion:1,entries})),{KEY,entries});
    await page.goto(base+'?collection='+river.id+'&route=complete');
    assert.equal(await page.locator('.campaign-hero p').count(),0);
    await page.locator('[data-mode="formation"]').click();
    assert.equal(await page.locator('[data-player-form]').count(),11);
    assert.equal(await page.locator('[data-action="both-teams"]').count(),1);
    await page.locator('[data-action="toggle-rival"]').click();
    assert.equal(await page.locator('[data-action="both-teams"]').count(),0);
    await page.locator('[data-action="home"]').click();await page.locator('[data-mode="formation"]').click();
    await page.locator('[data-action="both-teams"]').click();
    assert.equal(await page.locator('[data-player-form]').count(),22);
    assert.equal(await page.locator('[data-action="toggle-rival"]').count(),0);
    for(const s of ['home','away']) for(const [i,player] of final[s+'XI'].entries()) {
      const input=page.locator(`#guess-${s}-${i}`);
      await input.fill(player.accepted_answers?.[0]||player.name);await input.press('Enter');
    }
    assert.match(await page.locator('.completion').textContent(),/66 puntos/);
    const finalRecord=await page.evaluate(({KEY,id})=>JSON.parse(localStorage.getItem(KEY)).entries.find(e=>e.matchId===id),{KEY,id:final.id});
    assert.equal(finalRecord.formationClub,'all');
    assert.deepEqual(errors,[]);
    console.log('PASS: visible play access, compact launcher, personal-only campaigns, 11-player completion, free rival reference, saved drafts, club scoring and optional 22-player Madrid final.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
