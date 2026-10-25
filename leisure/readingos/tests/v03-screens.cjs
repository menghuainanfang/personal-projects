const {_electron:electron}=require('playwright');
const {expect}=require('playwright/test');
const fs=require('node:fs'),path=require('node:path');
const {Store}=require('../electron/store.cjs');
const {ensureBaseline}=require('./legacy-fixture.cjs');
const mode=process.argv[2]||'after';if(!['before','after'].includes(mode))throw Error('Choose before/after');
fs.mkdirSync('test-results',{recursive:true});const root=fs.mkdtempSync(path.resolve('test-results/v03-screens-'+mode+'-'));
const out=path.resolve('screenshots/iterations/003',mode);fs.mkdirSync(out,{recursive:true});let app,page;
async function capture(name){const png=await app.evaluate(async({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.showInactive();await new Promise(r=>setTimeout(r,250));const im=await w.webContents.capturePage();w.hide();return im.toPNG().toString('base64');});fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(png,'base64'));}
async function library(){if(await page.getByRole('button',{name:'← 书籍主页',exact:true}).count()){await page.getByRole('button',{name:'← 书籍主页',exact:true}).click();await expect(page.getByRole('button',{name:'返回书库',exact:true}).first()).toBeVisible();}await page.getByRole('button',{name:'书库',exact:true}).click();await expect(page.getByRole('heading',{name:'我的书库'})).toBeVisible();}
async function open(title){await library();await page.locator('.book-card').filter({has:page.getByRole('heading',{name:title,exact:true})}).click();}
(async()=>{
 await ensureBaseline();const s=new Store(path.join(root,'data'));await s.restore(path.resolve('test-results/v02-visual-before/baseline.readingos'));s.close();
 const opts={args:[path.resolve('.')],env:{...process.env,READINGOS_TEST_DATA:path.join(root,'data'),READINGOS_TEST_HEADLESS:'1'}};if(process.env.READINGOS_EXECUTABLE){opts.executablePath=path.resolve(process.env.READINGOS_EXECUTABLE);opts.args=[];}
 app=await electron.launch(opts);page=await app.firstWindow();await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.setSize(1366,768);w.webContents.setBackgroundThrottling(false);});await expect(page.getByRole('heading',{name:'我的书库'})).toBeVisible();await capture('library');
 await open('慢读与实践');await capture('book');await page.getByRole('button',{name:'编辑资料',exact:true}).click();await capture('date-form');if(mode==='after'){await page.getByRole('button',{name:'选择开始日期日期',exact:true}).click();await capture('date-popup');await page.keyboard.press('Escape');}await page.keyboard.press('Escape');
 await library();await page.getByRole('button',{name:'洞见与实践',exact:true}).click();await capture('insights');await page.getByRole('button',{name:'阅读计划',exact:true}).click();await capture('plan');
 await open('The Art of Slow Reading');await page.getByRole('button',{name:/继续阅读 · PDF/}).click();await expect(page.locator('.textLayer span').first()).toBeVisible();await capture('reader');
 fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({mode,viewport:await page.evaluate(()=>({width:innerWidth,height:innerHeight,dpr:devicePixelRatio})),info:await page.evaluate(()=>window.readingos.info())},null,2));await app.close();console.log('v0.3 screenshots: '+mode);
})().catch(async e=>{console.error(e);await app?.close().catch(()=>{});process.exitCode=1;});
