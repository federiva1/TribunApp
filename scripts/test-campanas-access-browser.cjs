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
    assert.equal(await page.locator('.hero [data-action="quick-play"], .hero-play').count(),0);
    assert.match(await page.locator('.hero-tags').textContent(),/30 CLUBES24 CAMPAÑAS HISTÓRICASFORMACIÓN \+ BONUS/);
    await page.locator('.hero-tags a').click();
    assert.equal(new URL(page.url()).hash,'#historical-campaigns');
    assert(await page.locator('#historical-campaigns').evaluate(el=>Math.abs(el.getBoundingClientRect().top-28)<2));
    assert.equal(await page.locator('.historical-card > span').count(),0,'campaign achievements no longer appear');
    await page.locator('[data-action="medals"]').click();
    assert.equal(await page.locator('.medal-card').count(),0);
    assert.match(await page.locator('.empty-state').textContent(),/Tu primera campaña/);
    await page.locator('.section-bar [data-action="quick-play"]').click();
    assert.equal(await page.locator('#quick-play-dialog select').count(),0);
    assert.equal(await page.locator('[data-quick-club]').count(),12);
    assert(await page.locator('.quick-submit').isDisabled());
    const catalog=require('../data/campanas/catalog.json').collections;
    for(const club of [...new Set(catalog.map(c=>c.clubSlug))]) {
      await page.locator(`[data-quick-club="${club}"]`).click();
      assert.equal(await page.locator('[data-quick-collection]').count(),2);
      assert.deepEqual(await page.locator('[data-quick-collection]').evaluateAll(buttons=>buttons.map(b=>b.dataset.quickCollection)),catalog.filter(c=>c.clubSlug===club).map(c=>c.id));
      assert(await page.locator('.quick-submit').isDisabled());
    }
    await page.locator('[data-quick-club="bocajuniors"]').click();
    await page.locator('[data-quick-collection="boca-libertadores-2007"]').click();
    await page.locator('[data-quick-route="complete"]').focus();await page.keyboard.press('Space');
    assert.equal(await page.locator('[data-quick-route="complete"]').getAttribute('aria-pressed'),'true');
    assert.deepEqual(await page.locator('[data-quick-route]').allTextContents(),['Clásico 7 partidos','Completo 14 partidos']);
    assert.equal(await page.locator('[data-quick-route="express"]').count(),0);
    assert.equal(await page.locator('#quick-mode').count(),0,'campaign has no mode picker');
    assert.equal(await page.locator('.quick-summary').count(),0);
    assert(await page.locator('#quick-play-dialog').evaluate(el=>el.scrollWidth<=el.clientWidth));
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-jugar-mobile.png')});
    await page.setViewportSize({width:1440,height:1100});
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-jugar-desktop.png')});
    await page.setViewportSize({width:320,height:740});
    assert(await page.locator('#quick-play-dialog').evaluate(el=>el.scrollWidth<=el.clientWidth));
    await page.setViewportSize({width:390,height:844});
    // Switching campaign types keeps the historical choice and updates tournament counts.
    await page.locator('[data-quick-kind="tournament"]').click();
    assert.equal(await page.locator('[data-quick-club]').count(),31);
    const tournament=require('../data/campanas/apertura-2026.json');
    await page.locator('[data-quick-club="all"]').click();
    assert.equal(await page.locator('[data-quick-route="complete"]').textContent(),'Completo 255 partidos');
    await page.locator('[data-quick-club="argentinosjuniors"]').click();
    assert.equal(await page.locator('[data-quick-route="complete"]').textContent(),'Completo '+core.routeMatches(tournament.matches,'argentinosjuniors','complete').length+' partidos');
    await page.locator('[data-quick-kind="history"]').click();
    assert.equal(await page.locator('[data-quick-collection][aria-pressed="true"]').getAttribute('data-quick-collection'),'boca-libertadores-2007');
    await page.locator('.quick-submit').click();
    await page.locator('#nickname-input').fill('Fede');await page.locator('#nickname-form .primary').click();
    assert.equal(await page.locator('[data-player-form]').count(),11);
    await page.locator('[data-action="medals"]').click();
    assert.equal(await page.locator('.medal-card').count(),1,'a started game belongs to the user before completion');
    assert.equal(await page.locator('[data-medal-collection="apertura-2026"]').count(),0,'unplayed tournament must stay out');
    await page.reload();await page.locator('[data-action="medals"]').click();
    assert.equal(await page.locator('.medal-card').count(),1,'started campaign survives reload');
    await page.locator('.section-bar [data-action="quick-play"]').click();
    assert.equal(await page.locator('[data-quick-collection][aria-pressed="true"]').getAttribute('data-quick-collection'),'boca-libertadores-2007','quick play remembers the last campaign');
    assert.equal(await page.locator('[data-quick-club][aria-pressed="true"]').getAttribute('data-quick-club'),'bocajuniors');
    await page.locator('.quick-submit').click();
    await page.locator('[data-player-form]').first().waitFor();
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
    assert.equal(await page.locator('.points').textContent(),'0 pts · partido','opening reference is free');
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
    await page.locator('.route-card').first().waitFor();
    assert.deepEqual(await page.locator('.route-card').allTextContents(),['Clásico 128 partidos','Completo 255 partidos']);
    assert.equal(await page.locator('[data-route="classic"]').getAttribute('aria-pressed'),'true');
    assert.equal(new URL(page.url()).searchParams.get('route'),'classic');
    await page.locator('.section-bar [data-action="quick-play"]').click();
    assert.equal(await page.locator('[data-quick-kind="tournament"]').getAttribute('aria-pressed'),'true');
    await page.keyboard.press('Escape');assert(!(await page.locator('#quick-play-dialog').isVisible()));
    await page.locator('.section-bar [data-action="quick-play"]').click();await page.locator('.quick-submit').click();
    await page.locator('[data-player-form]').first().waitFor();
    assert.equal(await page.locator('[data-player-form]').count(),22);
    assert.equal(await page.locator('[data-action="toggle-rival"]').count(),0);

    // The Madrid final remains optional and cannot be enabled after seeing the rival answers.
    const river=require('../data/campanas/river-libertadores-2018.json');
    const final=river.matches.find(m=>m.id==='espn-528144');
    const entries=river.matches.filter(m=>m.id!==final.id).map(m=>({collectionId:river.id,matchId:m.id,mode:'formation',flowVersion:2,bestScore:33,attempts:1,completedAt:'2026-10-01T10:00:00Z',updatedAt:'2026-10-01T10:00:00Z'}));
    await page.evaluate(({KEY,entries})=>localStorage.setItem(KEY,JSON.stringify({schemaVersion:1,entries})),{KEY,entries});
    await page.goto(base+'?collection='+river.id+'&route=complete');
    assert.equal(await page.locator('.campaign-hero p').count(),0);
    await page.locator('[data-action="campaign-play"]').click();
    assert.equal(await page.locator('[data-player-form]').count(),11);
    assert.equal(await page.locator('[data-action="both-teams"]').count(),1);
    await page.locator('[data-action="toggle-rival"]').click();
    assert.equal(await page.locator('[data-action="both-teams"]').count(),0);
    await page.locator('[data-action="home"]').click();await page.locator('[data-action="campaign-play"]').click();
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
