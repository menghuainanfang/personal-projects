const fs=require('node:fs'),path=require('node:path');
const {randomUUID}=require('node:crypto');
const {zipSync,strToU8}=require('fflate');
const subjectSchema=`
CREATE TABLE subject_categories(id TEXT PRIMARY KEY,parent_id TEXT REFERENCES subject_categories(id),name TEXT NOT NULL,sort_order INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL);
CREATE UNIQUE INDEX subject_siblings ON subject_categories(COALESCE(parent_id,''),name COLLATE NOCASE);
CREATE TABLE book_subjects(book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,category_id TEXT NOT NULL REFERENCES subject_categories(id) ON DELETE CASCADE,is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN(0,1)),created TEXT NOT NULL,PRIMARY KEY(book_id,category_id));
CREATE UNIQUE INDEX book_primary_subject ON book_subjects(book_id) WHERE is_primary=1;
PRAGMA user_version=3;`;
function check(db){if(db.prepare('PRAGMA integrity_check').get().integrity_check!=='ok'||db.prepare('PRAGMA foreign_key_check').all().length)throw Error('资料完整性检查失败');}
function migrate(db){
 db.exec(subjectSchema);const now=new Date().toISOString();
 const values=db.prepare("SELECT DISTINCT category FROM books WHERE trim(category)<>''").all();
 if(values.length){const parent=randomUUID();db.prepare('INSERT INTO subject_categories VALUES(?,NULL,?,0,?,?)').run(parent,'旧分类/待整理',now,now);
  for(const {category} of values){const name=category.trim();let row=db.prepare('SELECT id FROM subject_categories WHERE parent_id=? AND name=? COLLATE NOCASE').get(parent,name);if(!row){row={id:randomUUID()};db.prepare('INSERT INTO subject_categories VALUES(?,?,?,0,?,?)').run(row.id,parent,name,now,now);}db.prepare('INSERT INTO book_subjects SELECT id,?,1,? FROM books WHERE category=?').run(row.id,now,category);}
 }
 check(db);
}
function backupBeforeMigration(db,root){
 const stamp=new Date().toISOString().replace(/[:.]/g,'-'),snapshot=path.join(root,'before-v3-'+stamp+'.sqlite');
 db.exec(`VACUUM INTO '${snapshot.replaceAll("'","''")}'`);const entries={'format.json':strToU8(JSON.stringify({app:'ReadingOS',version:1})),'library.sqlite':new Uint8Array(fs.readFileSync(snapshot))};
 for(const {file}of db.prepare('SELECT file FROM assets').all())entries['assets/'+file]=new Uint8Array(fs.readFileSync(path.join(root,'assets',path.basename(file))));
 fs.writeFileSync(snapshot.replace(/\.sqlite$/,'.readingos'),zipSync(entries,{level:6}));
}
function operate(store,request){
 if(!request||typeof request!=='object')throw Error('学科操作无效');
 return store.transaction(()=>{
  const db=store.db,now=new Date().toISOString(),categories=db.prepare('SELECT * FROM subject_categories').all();
  const exists=id=>categories.some(c=>c.id===id);
  if(request.action==='assign'){
   const {bookIds,categoryIds,mode,primary}=request;
   if(!Array.isArray(bookIds)||!bookIds.length||bookIds.length>500||!Array.isArray(categoryIds)||!['add','remove','replace'].includes(mode)||categoryIds.some(id=>!exists(id))||primary&&!categoryIds.includes(primary))throw Error('书籍或学科选择无效');
   for(const id of new Set(bookIds)){
    if(!db.prepare('SELECT 1 FROM books WHERE id=?').get(id))throw Error('书籍不存在');
    if(mode==='replace')db.prepare('DELETE FROM book_subjects WHERE book_id=?').run(id);
    for(const category of new Set(categoryIds))if(mode==='remove')db.prepare('DELETE FROM book_subjects WHERE book_id=? AND category_id=?').run(id,category);else db.prepare('INSERT OR IGNORE INTO book_subjects VALUES(?,?,0,?)').run(id,category,now);
    if(primary&&mode!=='remove'){db.prepare('UPDATE book_subjects SET is_primary=0 WHERE book_id=?').run(id);db.prepare('UPDATE book_subjects SET is_primary=1 WHERE book_id=? AND category_id=?').run(id,primary);}
   }return {changed:new Set(bookIds).size};
  }
  if(request.action==='delete'){
   if(!exists(request.id))throw Error('学科不存在');
   if(categories.some(c=>c.parent_id===request.id)||db.prepare('SELECT 1 FROM book_subjects WHERE category_id=?').get(request.id))throw Error('只能删除没有子类且没有书籍的学科，请先移动子类或移除归属');
   db.prepare('DELETE FROM subject_categories WHERE id=?').run(request.id);return;
  }
  if(request.action!=='save')throw Error('学科操作无效');
  const id=request.id||randomUUID(),name=String(request.name||'').normalize('NFKC').trim(),parent=request.parentId||null;
  if(!name||name.length>100||request.id&&!exists(id)||parent&&!exists(parent))throw Error('学科名称或父级无效');
  let depth=1,cursor=parent;const visited=new Set([id]);
  while(cursor){if(visited.has(cursor))throw Error('不能将学科移动到自己或后代');visited.add(cursor);depth++;cursor=categories.find(c=>c.id===cursor)?.parent_id;}
  const height=node=>1+Math.max(0,...categories.filter(c=>c.parent_id===node).map(c=>height(c.id)));
  if(depth+height(id)-1>6)throw Error('学科最多支持六层');
  if(categories.some(c=>c.id!==id&&c.parent_id===parent&&c.name.normalize('NFKC').trim().toLocaleLowerCase()===name.toLocaleLowerCase()))throw Error('同一父级下已有同名学科');
  const order=Number(request.sortOrder??0);if(!Number.isSafeInteger(order)||Math.abs(order)>100000)throw Error('排序值无效');
  db.prepare('INSERT INTO subject_categories VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET parent_id=excluded.parent_id,name=excluded.name,sort_order=excluded.sort_order,updated=excluded.updated').run(id,parent,name,order,now,now);return id;
 });
}
module.exports={migrate,check,backupBeforeMigration,operate};
