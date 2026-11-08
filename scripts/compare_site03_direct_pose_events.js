/* Optional fixed-sample region comparison, not validated customer journeys. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),p=path.join(root,'data/processed'),a=require('../walkflows/hypothesis_analytics.js'),t=require('../walkflows/zone_transitions.js');
const read=x=>JSON.parse(fs.readFileSync(path.join(p,x))),hash=x=>crypto.createHash('sha256').update(fs.readFileSync(path.join(p,x))).digest('hex');
const report=read('site03-direct-pose-journeys/report.json');
if(hash('site03-hypotheses/hypotheses.json')!==report.baseline_hypotheses_sha256||hash('site03-direct-pose-journeys/hypotheses.json')!==report.hypotheses_sha256)throw Error('hypothesis provenance mismatch');
const zones=[{id:'south',name:'South example',type:'zone',x1:-6,y1:-3,x2:3,y2:3},{id:'north',name:'North example',type:'zone',x1:-6,y1:3.4,x2:3,y2:10}],options={fps:15,margin:.1,minDuration:.2,maxInterval:.1,transitionWindow:30};
const results=[];for(const [name,file] of [['baseline','site03-hypotheses/hypotheses.json'],['direct_mixed','site03-direct-pose-journeys/hypotheses.json']]){const h=read(file).hypotheses,r=t.summarize(h,zones,options,a);results.push({name,hash:hash(file),hypotheses:h.length,transitions:r.events,interrupted:r.interrupted})}
const output={scope:'Illustrative regions and experimental tracks; not actual business zones or confirmed transitions.',zones,options,results};fs.writeFileSync(path.join(p,'site03-direct-pose-journeys/events.json'),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));
