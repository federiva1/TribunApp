// Requires Playwright via PLAYWRIGHT_MODULE or a locally installed package.
// Uses an isolated browser context and intercepted local assets, never production votes.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const catalog = require('../data/campanas/catalog.json').collections;
const core = require('../js/campanas-core.js');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname !== 'campanas.test') return route.abort();
      const file = path.resolve(root, '.' + decodeURIComponent(url.pathname));
      if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: '' });
      const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg' };
      await route.fulfill({ body: fs.readFileSync(file), contentType: types[path.extname(file)] || 'application/octet-stream' });
    });
    await page.goto('http://campanas.test/campanas.html');
    await page.locator('.historical-card').first().waitFor();
    assert.equal(await page.locator('.historical-card').count(), 24);
    assert.match(await page.locator('.hero h1').innerText(), /¿Cuánto sabés\s+de fútbol argentino\?/);
    assert.equal(await page.locator('.crest-wall img').count(), 30);
    assert.equal(await page.locator('[data-mode]').count(), 3);
    assert(await page.locator('.crest-wall img').evaluateAll(images => images.every(img=>img.complete && img.naturalWidth>0)), 'all 30 local crests must load');
    assert(await page.locator('.historical-library').evaluate(section => section.getBoundingClientRect().top > document.querySelector('.mode-grid').getBoundingClientRect().bottom));
    assert(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth), 'mobile home must not overflow');
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-portada-mobile.png')});
    await page.setViewportSize({width:1440,height:1200});
    await page.screenshot({path:path.join(os.tmpdir(),'campanas-portada-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    await page.locator('#club-select').selectOption('argentinosjuniors');
    await page.locator('[data-mode="formation"]').click();
    assert.match(await page.locator('.game-top').textContent(), /Apertura 2026/);
    assert((await page.locator('.score-team span').allTextContents()).includes('Argentinos Juniors'));
    await page.locator('[data-action="home"]').click();
    assert.equal(await page.locator('.historical-card').count(),24);
    await page.locator('#history-club').selectOption('argentinosjuniors');
    assert.equal(await page.locator('.historical-card:visible').count(), 2);
    await page.locator('[data-collection="argentinos-clausura-2010"]').click();
    await page.getByRole('heading',{name:'Argentinos · Clausura 2010',exact:true}).waitFor();
    assert.equal(await page.locator('.historical-card').count(),0);
    await page.locator('[data-action="library"]').click();
    await page.locator('.historical-library').waitFor();
    assert.equal(await page.locator('.crest-wall img').count(),30);
    assert.equal(await page.locator('#club-select').inputValue(),'argentinosjuniors');
    await page.locator('[data-collection="argentinos-clausura-2010"]').click();
    await page.getByRole('heading',{name:'Argentinos · Clausura 2010',exact:true}).waitFor();
    await page.locator('[data-mode="formation"]').click();
    const input = page.locator('#guess-home-0');
    await page.locator('[data-hint="home-0"]').click();
    assert.match(await input.getAttribute('placeholder'), /_/);
    assert.equal(await page.locator('.letter-hint').count(), 0, 'clue must not render outside input');
    await page.locator('[data-hint="home-0"]').click();
    assert.match(await input.getAttribute('placeholder'), /\p{L}/u);
    await input.fill('respuesta parcial');
    await page.locator('[data-hint="home-0"]').click();
    assert.equal(await input.inputValue(), 'respuesta parcial');
    assert.match(await page.locator('#game-message').textContent(), /vale 0 puntos/);
    await input.fill('');
    await page.locator('[data-player="home-0"]').screenshot({ path: path.join(os.tmpdir(), 'campanas-pista-input.png') });

    for (const [i, item] of catalog.entries()) {
      await page.goto('http://campanas.test/campanas.html?collection=' + item.id);
      await page.locator('[data-mode="formation"]').click();
      assert.equal(await page.locator('[data-player-form]').count(), 22, item.id);
      assert.equal(await page.locator('#result-form').count(), 0);
      assert((await page.locator('.game-top').textContent()).includes(item.title));
      await page.locator('[data-action="home"]').click();
      await page.locator('[data-mode="scorers"]').click();
      let visible = await page.locator('.player-row:not(.eliminated) [data-goal]').count();
      for (let h = 0; h < 3; h++) {
        await page.locator('[data-action="scorer-hint"]').click();
        const next = await page.locator('.player-row:not(.eliminated) [data-goal]').count();
        assert(next < visible, item.id + ': hint must eliminate a visible candidate'); visible = next;
      }
      assert(await page.locator('[data-action="scorer-hint"]').isDisabled());
      await page.locator('[data-action="home"]').click();
      await page.locator('[data-mode="result"]').click();
      assert.equal(await page.locator('#result-form input').count(), 2);
      assert.equal(await page.locator('.score-value').textContent(), '? — ?');
      if (i % 6 === 5) console.log('Browser campaigns:', i + 1, '/24');
    }
    await page.goto('http://campanas.test/campanas.html?collection=boca-libertadores-2007');
    await page.locator('[data-mode="scorers"]').click();
    const collection = require('../data/campanas/boca-libertadores-2007.json');
    const names = await page.locator('.score-team span').allTextContents();
    const match = collection.matches.find(m => m.home === names[0] && m.away === names[1]);
    for (let h = 0; h < 3; h++) await page.locator('[data-action="scorer-hint"]').click();
    for (const id of core.actualScorers(match)) await page.locator('[data-goal]').evaluateAll((buttons, id) => buttons.find(b => b.dataset.goal === id).click(), id);
    await page.locator('[data-action="confirm-scorers"]').click();
    assert.match(await page.locator('.completion').textContent(), /0 puntos/);
    await page.locator('[data-action="archive"]').click();
    assert.equal(await page.locator('[data-replay-mode="scorers"]').count(), 0);
    await page.reload(); await page.locator('[data-action="archive"]').click();
    assert.equal(await page.locator('.archive-card').count(), 1);
    assert.equal(await page.locator('[data-replay-mode="scorers"]').count(), 0);
    await page.goto('http://campanas.test/campanas.html?collection=boca-liga-2022');
    await page.locator('[data-action="archive"]').click();
    assert.equal(await page.locator('.archive-card').count(), 0, 'campaign progress must be independent');
    await page.goto('http://campanas.test/campanas.html?collection=apertura-2026');
    await page.locator('[data-mode="formation"]').click();
    assert.equal(await page.locator('[data-player-form]').count(), 22);
    assert.deepEqual(errors, []);
    console.log('PASS: 24 campaigns / 72 mode starts, original tournament, input clue, effective hints, zero-score persistence and isolated progress.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
