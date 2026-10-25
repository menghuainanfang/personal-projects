const {test}=require('node:test');
const assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const {localDate,parseDate,validMonth,addMonths}=require('../shared/dates.mjs');

test('Local dates round trip leap days, historical and future dates',()=>{
  for(const value of ['2028-02-29','2025-12-31','2029-01-01'])assert.equal(localDate(parseDate(value)),value);
});
test('Invalid and empty dates are rejected without normalization',()=>{
  for(const value of ['2027-02-29','2026-04-31','2026-13-01','2026-2-03','', '2026-01-00'])assert.equal(parseDate(value),undefined);
});
test('Month arithmetic preserves cross-year ordering and string format',()=>{
  assert.equal(addMonths('2026-12',1),'2027-01');assert.equal(addMonths('2027-01',-1),'2026-12');
  assert.ok(validMonth('2026-12'));for(const value of ['2026-13','2026-1',''])assert.equal(validMonth(value),false);
});
test('Local calendar dates stay unchanged in positive and negative UTC offsets',()=>{
  for(const TZ of ['UTC','Asia/Shanghai','America/Los_Angeles']){
    const result=spawnSync(process.execPath,['-e',"const{localDate,parseDate}=require('./shared/dates.mjs');console.log(localDate(new Date(2028,1,29,0,30)));console.log(localDate(parseDate('2028-02-29')));"],{cwd:process.cwd(),env:{...process.env,TZ},encoding:'utf8'});
    assert.equal(result.status,0);assert.deepEqual(result.stdout.trim().split(/\r?\n/),['2028-02-29','2028-02-29']);
  }
});
