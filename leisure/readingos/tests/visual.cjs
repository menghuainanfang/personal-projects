const { _electron: electron } = require('playwright');
const { expect } = require('playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { Store } = require('../electron/store.cjs');
const { fixtures } = require('./fixtures.cjs');
const {ensureBaseline}=require('./legacy-fixture.cjs');
const mode = process.argv[2] || 'after';
if (!['before','after'].includes(mode)) throw Error('Choose before or after');
const root = path.resolve('test-results/v02-visual-' + mode);
const output = path.resolve('screenshots/' + mode);
const baseline = path.resolve('test-results/v02-visual-before/baseline.readingos');
fs.mkdirSync(root,{recursive:true}); fs.mkdirSync(output,{recursive:true});
let app, page;
async function capture(name, directory=output) {
  const png = await app.evaluate(async ({BrowserWindow}) => {
    const window = BrowserWindow.getAllWindows()[0];
    window.showInactive();
    await new Promise(resolve=>setTimeout(resolve,250));
    const result = await window.webContents.capturePage();
    window.hide();
    return result.toPNG().toString('base64');
  });
  fs.mkdirSync(directory,{recursive:true});
  fs.writeFileSync(path.join(directory,name+'.png'),Buffer.from(png,'base64'));
}
async function library() {
  if (await page.getByRole('button',{name:'← 书籍主页'}).count()) {
    await page.getByRole('button',{name:'← 书籍主页'}).click();
    await expect(page.getByRole('button',{name:'返回书库'})).toBeVisible();
  }
  if (await page.getByRole('button',{name:'返回书库'}).count()) await page.getByRole('button',{name:'返回书库'}).click();
  await expect(page.getByRole('heading',{name:'我的书库'})).toBeVisible();
}
async function open(title) {
  await library();
  await page.getByRole('button').filter({has:page.getByRole('heading',{name:title,exact:true})}).first().click();
}
(async()=>{
  if(mode==='after')await ensureBaseline();
  const store = new Store(path.join(root,'data'));
  if(mode==='after') await store.restore(baseline);
  else if(!store.snapshot().books.length){
    const originals = await fixtures(path.join(root,'originals'));
    const pdf=(await store.importFile(path.join(originals,'sample.pdf'))).bookId;
    const epub=(await store.importFile(path.join(originals,'sample.epub'))).bookId;
    store.save('books',{id:pdf,status:'reading',category:'阅读方法',tags:'慢读, 实践'});
    store.save('books',{id:epub,status:'reading',category:'随笔',tags:'思考'});
    const paper=store.save('books',{title:'慢读与实践',author:'ReadingOS 原创示例',status:'reading',category:'阅读方法',tags:'理解, 实践'});
    store.summary(paper,'<h2>把阅读变成自己的理解</h2><p>一本书的价值，不只在于读完，也在于读后如何生活。慢一点，允许问题停留；把重要的想法写下来，再用一个小行动检验它。</p><p>我的阅读习惯：先标记触动自己的句子，再用自己的话整理。每周回看一次，让笔记成为下一次实践的起点。</p>');
    const j=store.save('journals',{book_id:paper,title:'读到这里，停一停',date:'2026-10-11',content:'<p>今天重新读了关于实践的章节。比起记住很多结论，我更想把其中一个想法用于真实问题。</p>',source:'第 2 章 · 阅读与生活'});
    const i=store.save('insights',{title:'理解需要一次实际尝试',content:'用自己的话解释，再在生活中验证，让知识成为可以反复使用的经验。'});
    store.save('insight_links',{insight_id:i,book_id:paper,journal_id:j,annotation_id:null});
    store.save('actions',{insight_id:i,book_id:paper,description:'本周用一篇短日志复盘一次实际尝试',planned:'2026-10-18',status:'planned'});
    store.save('books',{title:'纸上思考',author:'ReadingOS 原创示例',status:'want',category:'随笔'});
    store.save('books',{title:'观察的练习',author:'ReadingOS 原创示例',status:'completed',completed:'2026-10-08',category:'方法'});
    store.save('books',{title:'日常的秩序',author:'ReadingOS 原创示例',status:'paused',category:'生活'});
    store.goal('2026',12); store.goal('2026-10',2); store.plan(paper,'2026-10',true);
  }
  for (const journal of store.snapshot().journals.filter(j=>j.title==='把想法带回生活')) store.remove('journals',journal.id);
  store.close();
  app=await electron.launch({args:[path.resolve('.')],env:{...process.env,READINGOS_TEST_DATA:path.join(root,'data'),READINGOS_TEST_HEADLESS:'1'}});
  page=await app.firstWindow();
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.setSize(1366,768);w.webContents.setBackgroundThrottling(false);});
  await expect(page.getByRole('heading',{name:'我的书库'})).toBeVisible();
  await page.evaluate(()=>{localStorage.setItem('readingos.theme','light')});
  await page.reload();
  await expect(page.locator('.book-card')).toHaveCount(6);
  await capture('bookshelf');
  if(mode==='after'){
    const candidates=path.resolve('screenshots/candidates');
    await capture('quiet-paper',candidates);
    const alternate=await page.addStyleTag({content:':root {--bg:#f1f3f4;--panel:#fff;--side:#e5e9ec;--ink:#242b32;--muted:#5b6269;--accent:#40586b;--accent-soft:#e1e8ee} h1 {font-family:var(--font-ui);font-size:26px} .sidebar {width:176px;padding-top:24px} .main-area {margin-left:176px;padding:24px 28px} .book-grid {gap:20px}.tabs {margin-bottom:20px;gap:20px}.page-heading {margin-bottom:16px}'});
    await capture('scholarly-neutral',candidates);await alternate.evaluate(e=>e.remove());
  }
  await open('慢读与实践');
  await expect(page.getByRole('textbox',{name:'主读后感',exact:true})).toContainText('把阅读变成自己的理解');
  await capture('book-home');
  await page.getByRole('button',{name:'写一篇日志'}).click();
  await page.getByRole('textbox',{name:'日志标题'}).fill('把想法带回生活');
  await page.getByRole('textbox',{name:'日志正文'}).fill('今天的阅读让我留意到：一个好的问题，比急于找到答案更重要。先把问题写下来，明天再试一次。');
  await expect(page.locator('.modal .format-bar span')).toHaveText('已保存');
  await capture('journal-editor');
  await page.getByRole('button',{name:'保存',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await open('The Art of Slow Reading');
  await page.getByRole('button',{name:/继续阅读 · PDF/}).click();
  await expect(page.locator('.textLayer span').first()).toBeVisible();
  if(mode==='before' && !(await page.evaluate(()=>window.readingos.snapshot())).annotations.length) {
    await page.locator('.textLayer span').filter({hasText:'Reading invites'}).first().evaluate(span=>{const r=document.createRange();r.selectNodeContents(span);const s=getSelection();s.removeAllRanges();s.addRange(r);span.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));});
    await page.getByRole('button',{name:'高亮选文'}).click();
    await expect(page.locator('.reader-header small')).toHaveText('已保存');
  }
  await capture('pdf-reader');
  await open('A Small Book of Reflection');
  await page.getByRole('button',{name:/继续阅读 · EPUB/}).click();
  await expect(page.frameLocator('iframe').locator('p').first()).toBeVisible();
  if(mode==='before'){
    await page.frameLocator('iframe').locator('p').first().evaluate(p=>{const r=document.createRange();r.selectNodeContents(p);const s=getSelection();s.removeAllRanges();s.addRange(r);p.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));});
    await page.getByRole('button',{name:'高亮选文'}).click();
    await expect(page.locator('.reader-header small')).toHaveText('已保存');
  }
  await expect(page.locator('.epub-host svg rect').first()).toBeVisible();
  await capture('epub-reader');
  await library();
  await page.getByRole('button',{name:'阅读计划'}).click();
  await capture('reading-plan');
  await app.close();app=null;
  if(mode==='before'){const s=new Store(path.join(root,'data'));await s.backup(baseline);fs.writeFileSync(path.join(root,'snapshot.json'),JSON.stringify(s.snapshot(),null,2));s.close();}
  fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({mode,window:[1366,768],screenshots:fs.readdirSync(output)},null,2));
  console.log('Visual capture passed: '+mode);
})().catch(async e=>{console.error(e);await app?.close().catch(()=>{});process.exitCode=1});
