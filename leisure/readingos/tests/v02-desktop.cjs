const { _electron: electron } = require('playwright');
const { expect } = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {Store} = require('../electron/store.cjs');
const {ensureBaseline}=require('./legacy-fixture.cjs');
const root=path.resolve('test-results/v02-'+(process.env.READINGOS_EXECUTABLE?'installed':'development'));
fs.mkdirSync(root,{recursive:true});
const store=new Store(path.join(root,'data'));
const baseline=path.resolve('test-results/v02-visual-before/baseline.readingos');
let app,page;const passed=[],dimensions=[],errors=[];
async function launch(){
  const opts={env:{...process.env,READINGOS_TEST_DATA:path.join(root,'data'),READINGOS_TEST_HEADLESS:'1'}};
  if(process.env.READINGOS_EXECUTABLE){opts.executablePath=path.resolve(process.env.READINGOS_EXECUTABLE);opts.args=[];}else opts.args=[path.resolve('.')];
  app=await electron.launch(opts);page=await app.firstWindow();
  await page.context().setOffline(true);
  page.on('pageerror',e=>errors.push(e.message));
  await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].webContents.setBackgroundThrottling(false));
  await expect(page.getByRole('heading',{name:'我的书库'})).toBeVisible();
}
async function state(){return page.evaluate(()=>window.readingos.snapshot());}
async function saved(){await expect(page.locator('.reader-header small')).toHaveText('已保存');}
async function step(name,fn){await fn();passed.push(name);console.log('PASS '+name);}
async function library(){
  if(await page.getByRole('button',{name:'← 书籍主页'}).count()){
    await page.getByRole('button',{name:'← 书籍主页'}).click();await expect(page.getByRole('button',{name:'返回书库'})).toBeVisible();
  }
  if(await page.getByRole('button',{name:'返回书库'}).count())await page.getByRole('button',{name:'返回书库'}).click();
  await expect(page.getByRole('heading',{name:'我的书库'})).toBeVisible();
}
async function capture(name){
  const png=await app.evaluate(async({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.showInactive();await new Promise(r=>setTimeout(r,250));const im=await w.webContents.capturePage();w.hide();return im.toPNG().toString('base64');});
  fs.writeFileSync(path.join(root,name+'.png'),Buffer.from(png,'base64'));
}
async function viewport(scene,size,zoom){
  const content=await app.evaluate(({BrowserWindow},{size,zoom})=>{const w=BrowserWindow.getAllWindows()[0];w.setSize(...size);w.webContents.setZoomFactor(zoom);return w.getContentSize();},{size,zoom});
  await expect.poll(()=>page.evaluate(w=>Math.abs(innerWidth-w),content[0]/zoom)).toBeLessThanOrEqual(2);
  await expect.poll(()=>page.evaluate(h=>Math.abs(innerHeight-h),content[1]/zoom)).toBeLessThanOrEqual(2);
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  const data=await page.evaluate(()=>({width:innerWidth,height:innerHeight,dpr:devicePixelRatio}));
  dimensions.push({scene,window:size,chromiumZoom:zoom,...data});
  if(scene==='reader'){
    await expect.poll(()=>page.locator('.reader-header button,.reader-tools button,.reader-tools summary').evaluateAll(items=>items.every(e=>{const b=e.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&b.bottom<=innerHeight;}))).toBe(true);
    assert.ok((await page.locator('.reader-content').boundingBox()).height>120);
  }
  await capture(scene+'-'+size.join('x')+'-'+zoom);
}
const sizes=[[1280,720],[1366,768],[1920,1080]],zooms=[1,1.25,1.5];
async function matrix(scene){for(const size of sizes)for(const zoom of zooms)await viewport(scene,size,zoom);await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.setSize(1366,768);w.webContents.setZoomFactor(1);});await expect.poll(()=>page.evaluate(()=>innerWidth)).toBeGreaterThan(1300);}
(async()=>{
  await ensureBaseline();await store.restore(baseline);store.close();await launch();
  if(!process.argv.includes('--layout-only')){
  await step('v1 backup opens with every original record and original file',async()=>{
    const old=JSON.parse(fs.readFileSync('test-results/v02-visual-before/snapshot.json','utf8')),now=await state();
    for(const [key,value]of Object.entries(old))assert.deepEqual(now[key],value,key);
    assert.deepEqual(now.reader_preferences,[]);
    const zip=await require('jszip').loadAsync(fs.readFileSync(baseline));
    for(const asset of now.assets){
      const bytes=await page.evaluate(id=>window.readingos.readAsset(id),asset.id);
      assert.ok(Buffer.from(bytes).equals(await zip.file('assets/'+asset.file).async('nodebuffer')));
    }
  });
  await step('Shelf opens PDF in one click; selection comment and journal preserve source',async()=>{
    await page.getByRole('button',{name:'继续阅读《The Art of Slow Reading》',exact:true}).click();
    await expect(page.locator('.textLayer span').first()).toBeVisible();
    await expect(page.getByRole('button',{name:'选择文字',exact:true})).toHaveAttribute('aria-pressed','true');
    await page.locator('.textLayer span').filter({hasText:'Reading invites'}).first().evaluate(span=>{const range=document.createRange();range.selectNodeContents(span);const sel=getSelection();sel.removeAllRanges();sel.addRange(range);span.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));});
    await page.getByRole('button',{name:'写批注',exact:true}).click();
    await page.getByRole('textbox',{name:'选文批注'}).fill('慢读：先提出问题，再做一次尝试。');
    await page.getByRole('button',{name:'保存批注'}).click();await saved();
    const ann=(await state()).annotations.find(a=>a.comment.includes('慢读：'));
    assert.ok(ann&&ann.text.includes('Reading invites'));
    await page.locator('.annotation-card').last().getByRole('button',{name:'引用到日志'}).click();
    await expect(page.getByRole('textbox',{name:'日志正文'})).toContainText(ann.text);
    await expect(page.getByRole('textbox',{name:'日志正文'})).toContainText(ann.comment);
    await page.getByRole('textbox',{name:'日志标题'}).fill('可回到原文的日志');
    await page.getByRole('button',{name:'保存',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
    const journal=(await state()).journals.find(j=>j.title==='可回到原文的日志');assert.equal(journal.source,ann.id);
    await page.getByLabel('PDF 页码').fill('3');
    await page.getByLabel('PDF 页码').press('Enter');
    await page.getByRole('button',{name:'← 书籍主页'}).click();
    await expect(page.getByRole('button',{name:'返回书库'})).toBeVisible();
    await page.locator('.journal-card').filter({has:page.getByRole('heading',{name:journal.title})}).getByRole('button',{name:'返回引用原文'}).click();
    await expect(page.locator('.textLayer span').first()).toBeVisible();
    await expect(page.getByLabel('PDF 页码')).toHaveValue(String(JSON.parse(ann.anchor).page));
    await page.getByLabel('PDF 页码').fill('3');
    await page.locator('.annotation-card').last().getByRole('button',{name:'引用到日志'}).click();
    await page.getByRole('dialog').getByRole('button',{name:'返回引用原文'}).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.getByLabel('PDF 页码')).toHaveValue(String(JSON.parse(ann.anchor).page));
  });
  await step('PDF preferences save and remain independent from EPUB',async()=>{
    await page.getByLabel('PDF 缩放',{exact:true}).selectOption('1.25');
    await page.getByLabel('绘图线宽').selectOption('4');
    await page.getByLabel('自定义高亮颜色').fill('#aabb88');
    await page.locator('.reader-preferences summary').click();await page.getByLabel('阅读配色').selectOption('custom');
    await page.getByLabel('阅读背景颜色').fill('#e8dfca');await page.getByLabel('阅读文字颜色').fill('#242925');await saved();
    await library();await page.getByRole('button',{name:'继续阅读《A Small Book of Reflection》',exact:true}).click();
    await expect(page.frameLocator('iframe').locator('p').first()).toBeVisible();
    await expect(page.getByLabel('EPUB 字号')).toHaveValue('20');await page.getByLabel('EPUB 字号').fill('24');await page.getByLabel('EPUB 行距').selectOption('2.2');
    await page.getByLabel('自定义高亮颜色').fill('#bb9988');await saved();
    await expect(page.locator('.epub-host svg rect').first()).toBeVisible();
    await library();await app.close();await launch();
    await page.getByRole('button',{name:'继续阅读《The Art of Slow Reading》',exact:true}).click();
    await expect(page.getByLabel('PDF 缩放',{exact:true})).toHaveValue('1.25');await expect(page.getByLabel('绘图线宽')).toHaveValue('4');await expect(page.getByLabel('自定义高亮颜色')).toHaveValue('#aabb88');
    await page.locator('.reader-preferences summary').click();await expect(page.getByLabel('阅读配色')).toHaveValue('custom');await expect(page.getByLabel('阅读背景颜色')).toHaveValue('#e8dfca');
    await library();await page.getByRole('button',{name:'继续阅读《A Small Book of Reflection》',exact:true}).click();
    await expect(page.getByLabel('EPUB 字号')).toHaveValue('24');await expect(page.getByLabel('EPUB 行距')).toHaveValue('2.2');await expect(page.getByLabel('自定义高亮颜色')).toHaveValue('#bb9988');
    await expect(page.locator('.epub-host svg rect').first()).toBeVisible();await library();
  });
  }
  await step('Library, home, journal and reader fit nine viewport/zoom combinations each',async()=>{
    await matrix('shelf');
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'慢读与实践',exact:true})}).click();await matrix('home');
    const trigger=page.getByRole('button',{name:'写一篇日志'});await trigger.click();
    for(let i=0;i<22;i++){await page.keyboard.press('Tab');assert.ok(await page.evaluate(()=>!!document.activeElement.closest('[role="dialog"]')),'Focus stays inside dialog');}
    await matrix('journal');await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await expect(trigger).toBeFocused();
    await library();await page.getByRole('button',{name:'继续阅读《The Art of Slow Reading》',exact:true}).click();await expect(page.locator('.textLayer span').first()).toBeVisible();
    await matrix('reader');await library();
  });
  await step('Light/dark normal text meets AA; reduced motion removes transitions',async()=>{
    for(const theme of ['light','dark']){
      if(await page.evaluate(()=>document.documentElement.dataset.theme)!==theme)await page.getByRole('button',{name:/^(深色主题|浅色主题)$/}).click();
      await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
      const tokens=await page.evaluate(()=>{const s=getComputedStyle(document.documentElement);return Object.fromEntries(['bg','panel','side','ink','muted','accent','accent-soft'].map(k=>[k,s.getPropertyValue('--'+k).trim()]));});
      const lum=hex=>{const rgb=hex.match(/[a-f\d]{2}/gi).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;};
      const ratio=(a,b)=>{const x=lum(tokens[a]),y=lum(tokens[b]);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
      for(const [a,b]of [['ink','bg'],['muted','bg'],['muted','panel'],['muted','side'],['accent','accent-soft'],['panel','accent']])assert.ok(ratio(a,b)>=4.5,theme+' '+a+'/'+b+' '+ratio(a,b));
      await capture('shelf-'+theme);
      await page.getByRole('button').filter({has:page.getByRole('heading',{name:'慢读与实践',exact:true})}).click();
      await capture('home-'+theme);await page.getByRole('button',{name:'写一篇日志'}).click();await capture('journal-'+theme);
      await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await library();
      await page.getByRole('button',{name:'继续阅读《The Art of Slow Reading》',exact:true}).click();
      await expect(page.locator('.textLayer span').first()).toBeVisible();
      await page.locator('.reader-preferences summary').click();await page.getByLabel('阅读配色').selectOption('system');await saved();await page.locator('.reader-preferences summary').click();
      await capture('pdf-'+theme);await library();
      await page.getByRole('button',{name:'继续阅读《A Small Book of Reflection》',exact:true}).click();await expect(page.frameLocator('iframe').locator('p').first()).toBeVisible();
      await expect.poll(()=>page.frameLocator('iframe').locator('body').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe(theme==='dark'?'rgb(34, 39, 33)':'rgb(255, 253, 246)');
      await capture('epub-'+theme);await library();
    }
    await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await page.locator('button').first().evaluate(e=>getComputedStyle(e).transitionDuration),'0s');
  });
  if(!process.argv.includes('--layout-only'))await step('Deleted annotation source stays explicit and never opens another location',async()=>{
    await page.getByRole('button',{name:'继续阅读《The Art of Slow Reading》',exact:true}).click();
    await expect(page.locator('.textLayer span').first()).toBeVisible();
    await page.locator('.annotation-card').last().getByRole('button',{name:'删除',exact:true}).click();await saved();
    await page.getByRole('button',{name:'← 书籍主页'}).click();await expect(page.getByRole('button',{name:'返回书库'})).toBeVisible();
    const journal=page.locator('.journal-card').filter({has:page.getByRole('heading',{name:'可回到原文的日志',exact:true})});
    await expect(journal).toContainText('关联批注已删除');
    await expect(journal.getByRole('button',{name:'返回引用原文'})).toHaveCount(0);
    await expect(page.locator('.reader-shell')).toHaveCount(0);
  });
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({passed,dimensions,errors,info:await page.evaluate(()=>window.readingos.info())},null,2));
  await app.close();console.log('v0.2 acceptance passed: '+passed.length);
})().catch(async e=>{console.error(e);await capture('failure').catch(()=>{});await app?.close().catch(()=>{});process.exitCode=1;});
