const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {analyzeTrack,createReport}=require('../walkflows/track_events.js');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(process.argv[2]||path.join(root,'data/processed/local-review/data.json'),'utf8'));
const groups=new Map();
for(const row of data.quality_observations){const k=JSON.stringify([row.camera,row.local_id]);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(row)}
const zone={id:'probe',name:'probe',type:'zone',x1:0,y1:-2,x2:2,y2:2},options={margin:0.1,minDuration:0.2,maxInterval:0.1};
let total=0,strict=0,research=0,events=0;
for(const rows of groups.values()){
 rows.sort((a,b)=>a.frame-b.frame);
 const a=analyzeTrack(rows,zone,options,'research'),b=analyzeTrack(rows,zone,options,'strict');
 const report=createReport(rows,zone,options,'research',{scene:'site02-v1',revision:1});
 assert.equal(report.observations.length,a.total);
 assert.ok(report.observations.every(row=>/^[a-f0-9]{64}$/.test(row.source_sha256)));
 total+=a.total;research+=a.selected;strict+=b.selected;events+=a.events.length;
}
assert.deepEqual({tracks:groups.size,total,strict,research},{tracks:10,total:418,strict:0,research:357});
assert.ok(events>0);
console.log(JSON.stringify({tracks:groups.size,total,strict,research,events}));
