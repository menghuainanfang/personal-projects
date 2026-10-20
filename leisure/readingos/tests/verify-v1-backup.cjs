const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {DatabaseSync}=require('node:sqlite');
const JSZip=require('jszip');
const {Store}=require('../electron/store.cjs');
(async()=>{
  if(!process.argv[2])throw Error('Provide a v1 .readingos backup');
  const input=path.resolve(process.argv[2]);
  const root=path.resolve('test-results/v02-v1-workflow-validation');
  fs.mkdirSync(root,{recursive:true});
  const zip=await JSZip.loadAsync(fs.readFileSync(input));
  const legacyFile=path.join(root,'original.sqlite');
  fs.writeFileSync(legacyFile,await zip.file('library.sqlite').async('nodebuffer'));
  const old=new DatabaseSync(legacyFile,{readOnly:true});
  const s=new Store(path.join(root,'restored'));
  try{
    assert.equal(old.prepare('PRAGMA user_version').get().user_version,1);
    await s.restore(input);
    const current=s.snapshot(),counts={};
    const tables=old.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").all();
    assert.equal(tables.length,14);
    for(const {name}of tables){const rows=old.prepare('SELECT * FROM '+name).all();assert.deepEqual(current[name],rows,name);counts[name]=rows.length;}
    for(const asset of current.assets)assert.ok(s.readAsset(asset.id).equals(await zip.file('assets/'+asset.file).async('nodebuffer')),asset.name);
    assert.equal(s.db.prepare('PRAGMA user_version').get().user_version,2);
    fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({schemaBefore:1,schemaAfter:2,counts,originalFiles:current.assets.length,allRowsEqual:true,allFilesEqual:true},null,2));
    console.log('Actual v1 backup: all 14 tables and '+current.assets.length+' original files preserved');
  }finally{old.close();s.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
