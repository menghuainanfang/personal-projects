const {_electron:electron}=require('playwright');
const {expect}=require('playwright/test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {Store}=require('../electron/store.cjs');
const {DatabaseSync}=require('node:sqlite');
const baseline=process.argv.includes('--baseline');
const packaged=!!process.env.READINGOS_EXECUTABLE;
fs.mkdirSync(path.resolve('test-results'),{recursive:true});
const root=fs.mkdtempSync(path.resolve('test-results/micro002-'+(baseline?'baseline':packaged?'installed':'development')+'-'));
const shots=path.resolve('screenshots/micro-002');fs.mkdirSync(shots,{recursive:true});
const titles=['纸上观察','慢读的练习','时间,与理解','关于"停顿"的笔记','日常里的问题','书页之间','把想法带到生活里','在散步时思考','一次漫长而温柔的中文阅读与实践记录：关于耐心、记忆和生活中的小小发现','明天再读一页'];
const input=titles.map((title,i)=>title+'\t原创作者'+(i+1)).join('\n');
let app,page;const passed=[],errors=[],viewports=[];
async function snapshot(){return page.evaluate(()=>window.readingos.snapshot());}
async function capture(name,directory=shots){const png=await app.evaluate(async({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.showInactive();await new Promise(r=>setTimeout(r,250));const image=await w.webContents.capturePage();w.hide();return image.toPNG().toString('base64');});fs.writeFileSync(path.join(directory,name+'.png'),Buffer.from(png,'base64'));}
async function launch(){const options={env:{...process.env,READINGOS_TEST_DATA:path.join(root,'data'),READINGOS_TEST_HEADLESS:'1'}};if(packaged){options.executablePath=path.resolve(process.env.READINGOS_EXECUTABLE);options.args=[];}else options.args=[path.resolve('.')];app=await electron.launch(options);page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.setSize(1380,920);w.webContents.setBackgroundThrottling(false);});await expect(page.getByRole('heading',{name:'我的书库'})).toBeVisible();await page.context().setOffline(true);}
async function step(name,fn){await fn();passed.push(name);console.log('PASS '+name);}
async function open(){await page.getByRole('button',{name:'导入与安排书单',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();}
async function paste(value,start='2026-11',end='2027-01'){await page.getByRole('textbox',{name:'粘贴书单',exact:true}).fill(value);await page.getByLabel('排期开始月份').fill(start);await page.getByLabel('排期结束月份').fill(end);await page.getByRole('button',{name:'生成预览',exact:true}).click();}
async function finish(){await page.getByRole('button',{name:'完成',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);}
(async()=>{
  fs.mkdirSync(path.resolve('test-results'),{recursive:true});
  const store=new Store(path.join(root,'data'));
  for(let i=0;i<4;i++)store.save('books',{title:titles[i],author:'原创作者'+(i+1),status:i===1?'reading':i===2?'completed':'want',completed:i===2?'2026-10-08':''});
  const existing=store.snapshot().books;store.plan(existing[0].id,'2026-11',true);store.plan(existing[1].id,'2026-11',true);store.plan(existing[2].id,'2026-12',true);store.goal('2026',18);store.goal('2026-11',4);
  await store.backup(path.join(root,'before.readingos'));store.close();
  await launch();await page.getByRole('button',{name:'阅读计划',exact:true}).click();await page.getByLabel('计划月份').fill('2026-11');
  if(baseline){
    await step('v0.2 plan changes preserve existing months, goals and completion',async()=>{const before=await snapshot();await expect(page.locator('.plan-list input').first()).toBeChecked();await page.locator('.plan-list input').last().click();await expect.poll(async()=>(await snapshot()).plans.length).toBe(4);const after=await snapshot();assert.deepEqual(after.books,before.books);assert.deepEqual(after.goals,before.goals);for(const plan of before.plans)assert.ok(after.plans.some(p=>p.book_id===plan.book_id&&p.month===plan.month));await capture('before');});
  }
  else {
    const original=await snapshot();
    await step('Ten pasted books preview without writes; four known books retain their IDs',async()=>{
      await open();await paste(input);await expect(page.getByRole('heading',{name:'书单预览 · 10 条'})).toBeVisible();await expect(page.locator('.import-row')).toHaveCount(10);
      await expect(page.locator('.import-row .status').filter({hasText:'已存在'})).toHaveCount(4);await expect(page.locator('.import-row .status').filter({hasText:'待创建'})).toHaveCount(6);assert.deepEqual(await snapshot(),original);
      const months=await page.locator('.import-row input[type="month"]').evaluateAll(items=>items.map(e=>e.value));assert.ok(months.every(m=>['2026-11','2026-12','2027-01'].includes(m)));
      await page.getByLabel('每月新增上限').fill('1');await expect(page.getByRole('status').filter({hasText:'待安排 4 条'})).toBeVisible();await expect(page.getByRole('button',{name:'确认保存'})).toBeDisabled();await page.getByLabel('参与第10条',{exact:true}).click();await expect(page.getByRole('status').filter({hasText:'待安排 3 条'})).toBeVisible();await page.getByLabel('参与第10条',{exact:true}).click();await page.getByLabel('每月新增上限').fill('');
      await page.getByLabel('第5条目标月份',{exact:true}).fill('2027-01');await expect(page.getByLabel('第5条目标月份',{exact:true})).toHaveValue('2027-01');
      await capture('preview');
      for(const zoom of [1.25,1.5]){
      await app.evaluate(({BrowserWindow},zoom)=>{const w=BrowserWindow.getAllWindows()[0];w.setSize(1280,720);w.webContents.setZoomFactor(zoom);},zoom);
      await expect.poll(()=>page.evaluate(()=>innerWidth)).toBeLessThan(Math.ceil(1280/zoom));
      await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
      const overflow=await page.getByRole('dialog').evaluate(e=>e.scrollWidth>e.clientWidth+1);assert.equal(overflow,false);
      await page.getByLabel('第5条目标月份',{exact:true}).scrollIntoViewIfNeeded();await page.getByLabel('第5条目标月份',{exact:true}).focus();await page.getByRole('button',{name:'确认保存'}).scrollIntoViewIfNeeded();await capture('preview-'+Math.round(zoom*100));viewports.push({zoom,...await page.evaluate(()=>({width:innerWidth,height:innerHeight,dpr:devicePixelRatio}))});
      }
      await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.setSize(1380,920);w.webContents.setZoomFactor(1);});
      await page.getByRole('button',{name:'确认保存',exact:true}).click();await expect(page.locator('.import-result')).toContainText('新建 6 本');
      const after=await snapshot();assert.equal(after.books.length,10);for(const book of original.books)assert.deepEqual(after.books.find(b=>b.id===book.id),book);
      for(const plan of original.plans)assert.ok(after.plans.some(p=>p.book_id===plan.book_id&&p.month===plan.month));
      for(const key of Object.keys(original).filter(k=>!['books','plans'].includes(k)))assert.deepEqual(after[key],original[key]);
      const manual=after.books.find(b=>b.title===titles[4]);assert.ok(after.plans.some(p=>p.book_id===manual.id&&p.month==='2027-01'));await finish();await capture('after');
    });
    await step('Repeated import creates neither books nor plans',async()=>{
      const before=await snapshot();await open();await paste(input);await page.getByRole('button',{name:'确认保存'}).click();await expect(page.locator('.import-result')).toContainText('已安排 0 条');await expect(page.locator('.import-result')).toContainText('重复 10 条');assert.deepEqual(await snapshot(),before);await finish();
    });
    await step('Missing authors require explicit matching; keyboard focus and Esc return correctly',async()=>{
      await open();await paste(titles[0]);await expect(page.locator('.import-row .status')).toHaveText('可能重复');await expect(page.getByRole('button',{name:'确认保存'})).toBeDisabled();
      await page.getByLabel('第1条匹配方式').selectOption('link:'+original.books[0].id);await expect(page.getByRole('button',{name:'确认保存'})).toBeEnabled();
      for(let i=0;i<16;i++){await page.keyboard.press('Tab');assert.ok(await page.evaluate(()=>!!document.activeElement.closest('[role="dialog"]')));}
      await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByRole('button',{name:'导入与安排书单',exact:true})).toBeFocused();
    });
    await step('Within-file duplicates are visible and share one book and month after confirmation',async()=>{
      const before=await snapshot();await open();await paste('本批重复书\t原创作者\n本批重复书\t原创作者');await expect(page.locator('.import-row').last()).toContainText('与第1条相同');await expect(page.getByLabel('参与第2条',{exact:true})).not.toBeChecked();await page.getByLabel('参与第2条',{exact:true}).click();assert.equal(await page.getByLabel('第1条目标月份',{exact:true}).inputValue(),await page.getByLabel('第2条目标月份',{exact:true}).inputValue());await page.getByRole('button',{name:'确认保存'}).click();await expect(page.locator('.import-result')).toContainText('新建 1 本');await expect(page.locator('.import-result')).toContainText('重复 1 条');assert.equal((await snapshot()).books.length,before.books.length+1);await finish();
      await open();await paste('同名不同作者的新书\t作者甲\n同名不同作者的新书\t作者乙');await expect(page.locator('.import-row').last()).toContainText('可能重复');await page.getByLabel('第2条匹配方式').selectOption('create');await page.getByRole('button',{name:'确认保存'}).click();await expect(page.locator('.import-result')).toContainText('新建 2 本');assert.equal((await snapshot()).books.filter(b=>b.title==='同名不同作者的新书').length,2);await finish();
    });
    await step('CSV File mapping preserves commas, quotes, long titles and explicit months; invalid rows are skipped',async()=>{
      await open();await page.getByRole('button',{name:'CSV / TSV 文件',exact:true}).click();
      const long='新的中文长标题：在日常生活、阅读与实践之间建立耐心而细致的联系，以及一次完整的个人观察记录';
      const content='\uFEFF编号,作品,撰写者,计划\r\n1,"时间,与理解",原创作者3,2026-12\r\n2,"关于""停顿""的笔记",原创作者4,2027-01\r\n3,"'+long+'","作者""五",2027/02\r\n4,,未知,2026-13';
      await page.getByLabel('书单文件').setInputFiles({name:'original-books.csv',mimeType:'text/csv',buffer:Buffer.from(content)});
      await expect(page.getByLabel('书名列')).toBeVisible();await page.getByLabel('书名列').selectOption('1');await page.getByLabel('作者列').selectOption('2');await page.getByLabel('月份列').selectOption('3');await page.getByRole('button',{name:'生成预览'}).click();
      await expect(page.locator('.import-row')).toHaveCount(4);await expect(page.locator('.import-row').nth(0)).toContainText('时间,与理解');await expect(page.locator('.import-row').nth(1)).toContainText('关于"停顿"的笔记');await expect(page.locator('.import-row').nth(2)).toContainText('作者"五');await expect(page.getByLabel('第3条目标月份',{exact:true})).toHaveValue('2027-02');await expect(page.locator('.import-row').last()).toContainText('无效');
      await capture('csv-mapping');await page.getByRole('button',{name:'确认保存'}).click();await expect(page.locator('.import-result')).toContainText('失败 1 条');assert.ok((await snapshot()).books.some(b=>b.title===long&&b.author==='作者"五'));await finish();
    });
    await step('TSV files and selecting existing library books use the same preview/save flow',async()=>{
      await open();await page.getByRole('button',{name:'CSV / TSV 文件',exact:true}).click();await page.getByLabel('书单文件').setInputFiles({name:'original.tsv',mimeType:'text/tab-separated-values',buffer:Buffer.from('title\tauthor\tmonth\nTSV里的新书\t原创TSV作者\t2027-01')});
      await expect(page.getByLabel('书名列')).toHaveValue('0');await page.getByRole('button',{name:'生成预览'}).click();await expect(page.locator('.import-row')).toContainText('TSV里的新书');await page.getByRole('button',{name:'确认保存'}).click();await expect(page.locator('.import-result')).toContainText('新建 1 本');await finish();
      const before=await snapshot();await open();await page.getByRole('button',{name:'从书库选择',exact:true}).click();for(const title of titles.slice(0,2))await page.locator('.import-library label').filter({hasText:title}).getByRole('checkbox').click();
      await page.getByLabel('排期开始月份').fill('2027-03');await page.getByLabel('排期结束月份').fill('2027-05');await page.getByRole('button',{name:'生成预览'}).click();await expect(page.locator('.import-row')).toHaveCount(2);await page.getByRole('button',{name:'确认保存'}).click();await expect(page.locator('.import-result')).toContainText('新建 0 本');assert.deepEqual((await snapshot()).books,before.books);await finish();
    });
    await step('Oversized, malformed and invalid-encoding imports never write data',async()=>{
      const before=await snapshot();await open();await page.getByRole('button',{name:'CSV / TSV 文件',exact:true}).click();
      await page.getByLabel('书单文件').setInputFiles({name:'too-large.csv',mimeType:'text/csv',buffer:Buffer.alloc(2*1024*1024+1,65)});await expect(page.getByRole('alert')).toContainText('2 MiB');await expect(page.getByRole('alert')).toBeFocused();
      await page.getByLabel('书单文件').setInputFiles({name:'invalid.csv',mimeType:'text/csv',buffer:Buffer.from([0xff,0xfe,0x41,0x00])});await expect(page.getByRole('alert')).toContainText('UTF-8');
      await page.getByLabel('书单文件').setInputFiles({name:'unclosed.csv',mimeType:'text/csv',buffer:Buffer.from('title,author\n"未闭合,作者')});await expect(page.getByLabel('书名列')).toHaveValue('0');await page.getByRole('button',{name:'生成预览'}).click();await expect(page.locator('.import-row')).toContainText('MissingQuotes');await expect(page.getByRole('button',{name:'确认保存'})).toBeDisabled();assert.deepEqual(await snapshot(),before);await page.keyboard.press('Escape');
    });
    await step('A real database error rolls back the entire Electron IPC batch',async()=>{
      await open();await paste('事务前一条\t测试作者\n<img src=x onerror="globalThis.booklistExecuted=true">\t测试作者','2027-06','2027-07');await expect(page.locator('.import-preview img,.import-preview script')).toHaveCount(0);assert.equal(await page.evaluate(()=>globalThis.booklistExecuted),undefined);
      const before=await snapshot();const fault=new DatabaseSync(path.join(root,'data','library.sqlite'));fault.exec("CREATE TRIGGER fail_micro002 BEFORE INSERT ON plans WHEN NEW.month='2027-07' BEGIN SELECT RAISE(ABORT,'test batch rollback'); END;");fault.close();
      await page.getByRole('button',{name:'确认保存'}).click();await expect(page.getByRole('alert')).toContainText('已写入 0 条');assert.deepEqual(await snapshot(),before);
      const cleanup=new DatabaseSync(path.join(root,'data','library.sqlite'));cleanup.exec('DROP TRIGGER fail_micro002');cleanup.close();await page.keyboard.press('Escape');
    });
    await step('Books, month assignments, goals and prior records survive application restart',async()=>{
      const before=await snapshot();await app.close();await launch();assert.deepEqual(await snapshot(),before);await page.getByRole('button',{name:'阅读计划',exact:true}).click();await page.getByLabel('计划月份').fill('2027-01');await capture(packaged?'installed-plan':'restart-plan');
    });
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({passed,errors,viewports,info:await page.evaluate(()=>window.readingos.info())},null,2));await app.close();console.log('Micro 002 acceptance passed: '+passed.length);
})().catch(async e=>{console.error(e);await capture('failure',root).catch(()=>{});await app?.close().catch(()=>{});process.exitCode=1;});
