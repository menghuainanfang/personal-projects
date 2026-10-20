const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {Store}=require('../electron/store.cjs');
const {parseText,parseDelimited,mapColumns,guessMapping,identifyBook,arrangeBooks,monthRange}=require('../shared/booklist.mjs');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'readingos-booklists-'));
function store(name){return new Store(path.join(root,name));}
function row(title,month='2026-11',author='原创作者'){return {title,author,month,mode:'auto'};}
function csv(input,delimiter=''){const table=parseDelimited(input,delimiter);return mapColumns(table,guessMapping(table.records[0]));}

test('Plain titles retain punctuation; Tab alone separates author; blank lines and BOM are handled',()=>{
  const rows=parseText('\uFEFF时间,与理解：关于（停顿）—实践\n\n关于"慢读"的笔记\t原创作者\r\n');
  assert.equal(rows.length,2);assert.equal(rows[0].title,'时间,与理解：关于（停顿）—实践');assert.equal(rows[0].author,'');assert.equal(rows[1].title,'关于"慢读"的笔记');assert.equal(rows[1].author,'原创作者');
  assert.match(parseText('甲\t乙\t丙')[0].error,/最多两列/);
});
test('PapaParse handles commas, escaped quotes, quoted line breaks, BOM and whitespace-only rows',()=>{
  const rows=csv('\uFEFF书名,作者,月份\r\n"时间,与理解","原创""作者",2026/11\r\n  ,  , \r\n"第一行\n第二行",001,2027-01\r\n');
  assert.equal(rows.length,2);assert.equal(rows[0].title,'时间,与理解');assert.equal(rows[0].author,'原创"作者');assert.equal(rows[0].sourceMonth,'2026-11');assert.equal(rows[1].title,'第一行\n第二行');assert.equal(rows[1].author,'001');assert.ok(rows.every(r=>!r.error));
});
test('CSV and TSV mapping supports aliases, explicit columns, no headers and parser errors',()=>{
  assert.equal(csv('title\tauthor\n原创书\t原创者','\t')[0].title,'原创书');
  const table=parseDelimited('编号;作品;撰写者;计划\n1;书甲;作者甲;2026年12月');
  assert.deepEqual(mapColumns(table,{title:1,author:2,month:3})[0],{title:'书甲',author:'作者甲',sourceMonth:'2026-12',error:''});
  assert.equal(mapColumns(parseDelimited('甲,乙\n丙,丁'),{title:0,author:1,month:-1},false).length,2);
  assert.match(csv('title,author\n甲,乙,丙')[0].error,/列数/);
  assert.match(csv('title,author\n"未闭合,乙')[0].error,/MissingQuotes/);
  assert.match(csv('title,month\n甲,2026-13')[0].error,/月份/);
  assert.match(csv('title,author\n,乙')[0].error,/书名/);
});
test('Supported import limits reject oversized input without silently truncating records',()=>{
  assert.throws(()=>parseText('甲'.repeat(800000)),/2 MiB/);
  assert.throws(()=>parseText(Array.from({length:501},(_,i)=>'书'+i).join('\n')),/500/);
  assert.throws(()=>csv('title\n'+Array.from({length:501},(_,i)=>'书'+i).join('\n')),/500/);
  assert.equal(csv('title\n'+Array.from({length:500},(_,i)=>'书'+i).join('\n')).length,500);
  assert.match(parseText('甲'.repeat(501))[0].error,/500/);
  assert.throws(()=>parseText('甲\0乙'),/UTF-8/);
});
test('Matching distinguishes exact identity, ambiguous titles and separate authors',()=>{
  const books=[{id:'a',title:'慢读',author:'甲'},{id:'b',title:'慢读',author:'乙'}];
  assert.equal(identifyBook({title:' 慢读 ',author:'甲'},books).bookId,'a');
  assert.equal(identifyBook({title:'慢读',author:''},books).status,'possible');
  assert.equal(identifyBook({title:'慢读',author:'丙'},books).status,'possible');
  assert.equal(identifyBook({title:'新书',author:'甲'},books).status,'new');
});
test('Balanced quotas preserve input order and include existing month load',()=>{
  const rows=Array.from({length:10},(_,i)=>({key:String(i),active:true}));
  const options={start:'2026-11',end:'2027-01'};
  const a=arrangeBooks(rows,[],options);assert.deepEqual(a.assigned,['2026-11','2026-11','2026-11','2026-11','2026-12','2026-12','2026-12','2027-01','2027-01','2027-01']);
  const existing=[{book_id:'old1',month:'2026-11'},{book_id:'old2',month:'2026-11'}];
  const b=arrangeBooks(rows,existing,options);assert.equal(b.assigned.filter(m=>m==='2026-11').length,2);assert.equal(b.assigned.filter(m=>m==='2026-12').length,4);assert.equal(b.assigned.filter(m=>m==='2027-01').length,4);
  assert.deepEqual(b,arrangeBooks(rows,existing,options));
});
test('Capacity leaves visible waiting rows; manual and existing months are retained',()=>{
  const rows=Array.from({length:10},(_,i)=>({key:String(i),active:true}));
  const options={start:'2026-11',end:'2027-01',limit:2};
  const result=arrangeBooks(rows,[],options);assert.equal(result.assigned.filter(Boolean).length,6);assert.equal(result.assigned.filter(m=>!m).length,4);
  rows[0].month='2027-01';rows[1].bookId='old';
  const b=arrangeBooks(rows,[{book_id:'old',month:'2026-12'}],options);assert.equal(b.assigned[0],'2027-01');assert.equal(b.assigned[1],'2026-12');
  rows[1].month='2027-01';rows[2].month='2027-01';assert.deepEqual(arrangeBooks(rows,[],options).overCapacity,['2027-01']);
  assert.throws(()=>monthRange('2026-13','2027-01'),/有效/);assert.throws(()=>monthRange('2027-01','2026-11'),/早于/);
});
test('Repeated automatic entries share a month instead of consuming another month quota',()=>{
  const result=arrangeBooks([{key:'same',active:true},{key:'same',active:true},{key:'different',active:true}],[],{start:'2026-11',end:'2027-01',limit:1});
  assert.deepEqual(result.assigned,['2026-11','2026-11','2026-12']);
});
test('Batch creates only missing books, preserves all existing rows and is idempotent after restart',()=>{
  const s=store('batch');
  try{
    const old=s.save('books',{title:'已有书',author:'原作者',status:'completed',completed:'2026-09-18'});
    s.summary(old,'<p>原心得</p>');s.save('journals',{book_id:old,title:'原日志',date:'2026-10-20',content:'<p>原内容</p>'});s.preferences(old,{fontSize:26,color:'#aabbcc'});s.goal('2026',20);s.plan(old,'2026-10',true);
    const before=s.snapshot();
    const payload={rows:[{...row('已有书','2026-11',''),mode:'link',bookId:old},row('新书'),row('新书'),{...row('无效'),mode:'invalid'},{...row('排除'),mode:'skip'}]};
    const result=s.batchPlans(payload);assert.equal(result.created,1);assert.equal(result.scheduled,2);assert.equal(result.duplicates,1);assert.equal(result.failed,1);assert.equal(result.skipped,2);
    const after=s.snapshot();assert.equal(after.books.length,2);assert.deepEqual(after.books.find(b=>b.id===old),before.books[0]);
    for(const key of Object.keys(before).filter(k=>!['books','plans'].includes(k)))assert.deepEqual(after[key],before[key]);
    const added=after.books.find(b=>b.id!==old);assert.equal(added.status,'want');assert.equal(added.completed,'');assert.equal(s.db.prepare('PRAGMA user_version').get().user_version,2);
    const second=s.batchPlans(payload);assert.equal(second.created,0);assert.equal(second.scheduled,0);assert.equal(second.duplicates,3);assert.deepEqual(s.snapshot(),after);
    s.close();const reopened=new Store(path.join(root,'batch'));assert.deepEqual(reopened.snapshot(),after);reopened.close();
  }finally{if(s.db.isOpen)s.close();}
});
test('Ambiguous books require confirmation and never overwrite existing metadata',()=>{
  const s=store('ambiguous');try{
    s.save('books',{title:'同名书',author:'甲',status:'reading'});const before=s.snapshot();
    assert.throws(()=>s.batchPlans({rows:[row('同名书','2026-11','乙')]}),/可能重复/);assert.deepEqual(s.snapshot(),before);
    assert.equal(s.batchPlans({rows:[{...row('同名书','2026-11','乙'),mode:'create'}]}).created,1);
    assert.equal(s.batchPlans({rows:[{...row('同名书','2026-11','乙'),mode:'create'}]}).created,0);
    assert.throws(()=>s.batchPlans({rows:[row('非法月份','2026-99')]}),/月份/);
  }finally{s.close();}
});
test('A real SQLite error rolls back earlier book and plan inserts atomically',()=>{
  const s=store('rollback');try{
    s.save('books',{title:'原书'});const before=s.snapshot();
    s.db.exec("CREATE TRIGGER fail_batch BEFORE INSERT ON plans WHEN NEW.month='2026-12' BEGIN SELECT RAISE(ABORT,'test transaction failure'); END;");
    assert.throws(()=>s.batchPlans({rows:[row('先插入','2026-11'),row('后失败','2026-12')]}),/test transaction failure/);assert.deepEqual(s.snapshot(),before);
    assert.throws(()=>s.batchPlans({rows:[row('超额一'),row('超额二')],limit:1}),/新增上限/);assert.deepEqual(s.snapshot(),before);
  }finally{s.close();}
});
