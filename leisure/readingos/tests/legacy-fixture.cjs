const fs=require('node:fs');
const path=require('node:path');
const {Store}=require('../electron/store.cjs');
const {fixtures}=require('./fixtures.cjs');
async function ensureBaseline(root=path.resolve('test-results/v02-visual-before')){
  const backup=path.join(root,'baseline.readingos'),snapshot=path.join(root,'snapshot.json');
  if(fs.existsSync(backup)&&fs.existsSync(snapshot))return;
  const seedRoot=path.join(root,'generated-legacy');
  const s=new Store(path.join(seedRoot,'data'));
  try{
    const files=await fixtures(path.join(seedRoot,'originals'));
    if(!s.snapshot().books.length){
      const pdf=(await s.importFile(path.join(files,'sample.pdf'))).bookId;
      const epub=(await s.importFile(path.join(files,'sample.epub'))).bookId;
      for(const id of [pdf,epub])s.save('books',{id,status:'reading',category:'阅读方法'});
      const paper=s.save('books',{title:'慢读与实践',author:'ReadingOS 原创示例',status:'reading',category:'阅读方法'});
      s.summary(paper,'<h2>把阅读变成自己的理解</h2><p>慢一点，把重要想法写下来，再用行动检验。</p>');
      const assets=s.snapshot().assets;
      const annotation=s.save('annotations',{asset_id:assets.find(a=>a.book_id===pdf).id,kind:'highlight',anchor:JSON.stringify({page:1,rects:[[.109,.229,.517,.024]]}),color:'#dcc776',text:'Reading invites us to pause and make an idea our own.'});
      s.save('annotations',{asset_id:assets.find(a=>a.book_id===epub).id,kind:'highlight',anchor:JSON.stringify({cfi:'epubcfi(/6/2!/4/4,/1:0,/1:132)'}),color:'#dcc776',text:'Paragraph 0. Reading invites us to pause and make an idea our own. We read slowly, reflect honestly, and practice a little each day.'});
      const journal=s.save('journals',{book_id:pdf,title:'原文与实践',date:'2026-10-11',content:'<p>一次实际尝试</p>',source:annotation});
      const insight=s.save('insights',{title:'理解需要实际尝试',content:'用自己的话解释，再在生活中验证。'});
      s.save('insight_links',{insight_id:insight,book_id:pdf,annotation_id:annotation,journal_id:journal});
      const action=s.save('actions',{insight_id:insight,book_id:pdf,description:'写一次复盘',planned:'2026-10-18',status:'planned'});
      s.save('feedback',{action_id:action,content:'先从一个问题开始。',date:'2026-10-11'});
      s.save('bookmarks',{asset_id:assets.find(a=>a.book_id===pdf).id,location:JSON.stringify({page:1}),label:'书签 1'});
      s.progress(assets.find(a=>a.book_id===pdf).id,JSON.stringify({page:1}));
      for(const title of ['纸上思考','观察的练习','日常的秩序'])s.save('books',{title,author:'ReadingOS 原创示例',status:'want'});
      s.goal('2026',12);s.goal('2026-10',2);s.plan(paper,'2026-10',true);
    }
    const state=s.snapshot();delete state.reader_preferences;
    s.db.exec('DROP TABLE reader_preferences; PRAGMA user_version=1');
    fs.mkdirSync(root,{recursive:true});await s.backup(backup);
    fs.writeFileSync(snapshot,JSON.stringify(state,null,2));
  }finally{s.close();}
}
module.exports={ensureBaseline};
