/* Fixed 007 example zones; trajectories and IDs are unverified. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'data/processed/site03-007-comparison'),a=require('../walkflows/hypothesis_analytics.js'),t=require('../walkflows/zone_transitions.js');
const read=name=>JSON.parse(fs.readFileSync(path.join(dir,name))),hash=name=>crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,name))).digest('hex'),manifest=read('journey-report.json');
const sets=[['baseline','baseline-hypotheses.json',manifest.methods.baseline.hypotheses_sha256],['direct','direct-hypotheses.json',manifest.methods.direct.hypotheses_sha256],['reference','reference-hypotheses.json',manifest.reference_hypotheses_sha256]];
const zones=[{id:'south',name:'South example',type:'zone',x1:-6,y1:-3,x2:3,y2:3},{id:'north',name:'North example',type:'zone',x1:-6,y1:3.4,x2:3,y2:10}],options={fps:15,margin:.1,minDuration:.2,maxInterval:.1,transitionWindow:30};
const results=sets.map(([name,file,sha])=>{if(hash(file)!==sha)throw Error('hypotheses mismatch');const result=t.summarize(read(file).hypotheses,zones,options,a);return {name,hypotheses_sha256:sha,transitions:result.events,interrupted:result.interrupted}});
const output={scope:'illustrative example regions; not actual business zones or verified people',zones,options,results};fs.writeFileSync(path.join(dir,'event-comparison.json'),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));
