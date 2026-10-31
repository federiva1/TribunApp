const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const C=require('../js/campanas-core.js'),data=require('../data/campanas/boca-libertadores-2007.json');
const root=path.resolve(__dirname,'..'),base='http://campanas.test/campanas.html';
const KEY='tribunapp.campanas.progress.v1';
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/*',async route=>{
      const url=new URL(route.request().url());if(url.hostname!=='campanas.test')return route.abort();
      const file=path.resolve(root,'.'+decodeURIComponent(url.pathname));
      if(!file.startsWith(root+path.sep)||!fs.existsSync(file))return route.fulfill({status:404,body:''});
      const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.webp':'image/webp'};
      return route.fulfill({body:fs.readFileSync(file),contentType:types[path.extname(file)]||'application/octet-stream'});
    });
    await page.addInitScript(()=>{
      Math.random=()=>window.testRandom?.shift()??0;
      localStorage.setItem('tribunapp.campanas.profile.v1',JSON.stringify({nickname:'Fede',mode:'formation',route:'complete'}));
    });
    await page.goto(base+'?collection='+data.id+'&route=complete');
    await page.locator('[data-action="random-play"]').waitFor();
    assert.equal(await page.locator('.mode-card').count(),3,'random is not a fourth card');
    // Select each of the three actual challenges on a goal-bearing match.
    const modeNames=['Formación incompleta','Goleadores','Resultado oculto'];
    for(let i=0;i<3;i++) {
      await page.evaluate(i=>{window.testRandom=[1.1/14,(i+.1)/3];},i);
      await page.locator('[data-action="random-play"]').click();
      assert.equal(await page.locator('.game-top h1').textContent(),modeNames[i]);
      assert(await page.locator('.random-label').isVisible());
      assert.deepEqual(await page.locator('.score-team span').allTextContents(),[data.matches[1].home,data.matches[1].away]);
      await page.locator('[data-action="home"]').click();
    }
    // Finish a random result challenge: persist its real mode and keep random on Next.
    await page.evaluate(()=>{window.testRandom=[1.1/14,.99];});
    await page.locator('[data-action="random-play"]').click();
    await page.locator('#result-form input[name="home"]').fill('1');
    await page.locator('#result-form input[name="away"]').fill('0');
    await page.locator('#result-form .primary').click();
    let saved=await page.evaluate(KEY=>JSON.parse(localStorage.getItem(KEY)).entries,KEY);
    assert.equal(saved.length,1);assert.equal(saved[0].mode,'result');assert.equal(saved[0].bestScore,20);
    await page.evaluate(()=>{window.testRandom=[0,.99];});
    await page.locator('.completion [data-action="next"]').click();
    assert(await page.locator('.random-label').isVisible());
    assert.deepEqual(await page.locator('.score-team span').allTextContents(),[data.matches[0].home,data.matches[0].away]);
    assert.equal(await page.locator('.game-top h1').textContent(),'Resultado oculto','0–0 only chooses eligible modes');
    await page.locator('.game-actions [data-action="next"]').click();
    assert.notDeepEqual(await page.locator('.score-team span').allTextContents(),[data.matches[0].home,data.matches[0].away],'skip chooses another match');
    assert(await page.locator('.random-label').isVisible());
    // Manual choice deliberately exits random play.
    await page.locator('[data-action="home"]').click();await page.locator('[data-mode="formation"]').click();
    assert.equal(await page.locator('.random-label').count(),0);

    // Open the reported Toluca match through the normal campaign selection.
    const target=data.matches.find(m=>m.id==='espn-213122');
    const entries=data.matches.filter(m=>m.id!==target.id).map(m=>({collectionId:data.id,matchId:m.id,mode:'result',bestScore:20,attempts:1,completedAt:'2026-10-01T10:00:00Z',updatedAt:'2026-10-01T10:00:00Z'}));
    await page.evaluate(({KEY,entries})=>localStorage.setItem(KEY,JSON.stringify({schemaVersion:1,entries})),{KEY,entries});
    await page.goto(base+'?collection='+data.id+'&route=complete');
    await page.locator('[data-mode="formation"]').click();
    const rows=page.locator('.team-sheet .player-row');
    assert.equal(await rows.first().getAttribute('data-player'),'away-6','Caranta is first with his original identity');
    await page.locator('#guess-away-6').fill('borrador');
    await page.locator('[data-action="toggle-rival"]').click();
    assert.equal(await page.locator('#guess-away-6').inputValue(),'borrador');
    const sheets=await page.locator('.team-sheet').evaluateAll(els=>els.map(el=>({top:el.getBoundingClientRect().top,width:el.getBoundingClientRect().width})));
    assert.equal(sheets.length,2);assert(Math.abs(sheets[0].top-sheets[1].top)<1);assert(Math.abs(sheets[0].width-sheets[1].width)<1);
    assert.equal(await page.locator('#rival-sheet input').count(),0);
    assert(await page.locator('.lineup-toolbar').evaluate(el=>el.getBoundingClientRect().bottom<=document.querySelector('.team-sheet').getBoundingClientRect().top));
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-rival-alineado.png'),fullPage:true});
    await page.locator('[data-hint="away-6"]').click();
    await page.locator('#guess-away-6').fill('Caranta');await page.locator('#guess-away-6').press('Enter');
    assert.equal(await rows.first().locator('.player-name').textContent(),'Caranta');
    assert.equal(await page.locator('.points').textContent(),'2 pts');
    // The scorer sheet uses the same positional order, independent of actual goal picks.
    await page.locator('[data-action="home"]').click();await page.locator('[data-mode="scorers"]').click();
    const boca=page.locator('.team-sheet').filter({has:page.locator('h2',{hasText:'Boca Juniors'})});
    assert.equal(await boca.locator('.player-name').first().textContent(),'Caranta');

    await page.locator('[data-action="medals"]').click();
    assert.equal(await page.locator('.medal-badge b').count(),0);
    assert.equal(await page.locator('.medal-track').count(),3);
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-progreso-nuevo.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-progreso-nuevo-mobile.png'),fullPage:true});
    // Random is available through the compact launcher as well.
    await page.locator('.section-bar [data-action="quick-play"]').click();
    await page.locator('#quick-mode').selectOption('random');
    assert.match(await page.locator('.quick-summary').textContent(),/reto sorpresa/);
    await page.locator('.quick-submit').click();await page.locator('.random-label').waitFor();
    await page.locator('[data-action="home"]').click();await page.locator('[data-mode="formation"]').click();
    await page.locator('[data-action="toggle-rival"]').click();
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    const mobile=await page.locator('.team-sheet').evaluateAll(els=>els.map(el=>({top:el.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom})));
    assert(mobile[1].top>=mobile[0].bottom,'mobile sheets stack without overlap');
    assert.deepEqual(errors,[]);
    console.log('PASS: random modes, eligibility, actual-mode scoring, next/skip/manual transition, launcher, Caranta identity and hints, aligned rival sheets, responsive progress rows.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
