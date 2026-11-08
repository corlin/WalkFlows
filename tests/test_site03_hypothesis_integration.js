const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),data=JSON.parse(fs.readFileSync(path.join(root,'data/processed/site03-review/data.json'))),source=fs.readFileSync(path.join(root,'data/processed/site03-hypotheses/hypotheses.json'));
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),data.research_metadata.hypothesis_sha256);
const originals=new Map();for(const [cam,rows] of Object.entries(data.cameras))for(const r of rows)if(r.pose_candidate)originals.set(JSON.stringify([cam,r.id,r.frame]),r);
const seen=new Set();let samples=0,conflicts=0;
for(const h of data.hypotheses){assert.equal(new Set(h.members.map(m=>m.camera)).size,h.members.length);for(const sample of h.samples){samples++;if(sample.status==='spatial_conflict'){conflicts++;assert.equal(sample.x,null);assert.equal(sample.y,null)}for(const p of sample.sources){const k=JSON.stringify([p.camera,p.id,sample.frame]);assert.ok(originals.has(k));assert.ok(!seen.has(k));seen.add(k);let origin=originals.get(k);assert.equal(p.x,origin.pose_x);assert.equal(p.y,origin.pose_y)}}}
assert.equal(seen.size,originals.size);assert.equal(data.hypotheses.length,9);assert.equal(originals.size,549);assert.equal(conflicts,1);
const {heatmap,createResearchReport}=require('../walkflows/hypothesis_analytics.js');
const layout={schema_version:1,scene:data.scene,revision:1,items:[{id:'example',name:'example',type:'zone',x1:-3,y1:1,x2:0,y2:3}]};
const result=createResearchReport(data,layout,{margin:.1,minDuration:.2,maxInterval:.1,columns:18,rows:26});
assert.equal(result.hypotheses.length,data.hypotheses.length);assert.equal(result.routes.length,data.hypotheses.length);assert.equal(result.areas[0].hypotheses.length,data.hypotheses.length);assert.equal(result.scope,'unverified_research_hypotheses_not_customer_counts');
const grid=heatmap(data.hypotheses,data.bounds,{columns:18,rows:26,fps:data.fps});assert.equal(grid.samples.flat().reduce((a,b)=>a+b,0),samples-conflicts);
const {buildFunnel}=require('../walkflows/research_funnel.js');
const regions=[{id:'a',name:'A',type:'zone',x1:-3,y1:3,x2:0,y2:7},{id:'b',name:'B',type:'zone',x1:-3,y1:1,x2:0,y2:3}];
const funnel=buildFunnel(data.hypotheses,regions,['a','b'],{margin:.1,minDuration:.2,maxInterval:.1,fps:data.fps,window_s:30});
assert.deepEqual(funnel.steps.map(s=>s.hypotheses),[2,0]);
for(const track of funnel.tracks){assert.equal(track.reached,track.evidence.length);for(let i=1;i<track.evidence.length;i++)assert.ok(track.evidence[i].frame>track.evidence[i-1].frame)}
console.log(JSON.stringify({hypotheses:data.hypotheses.length,source_observations:seen.size,samples,conflicts,areas:result.areas.length}));
const diagnosticPath=path.join(root,'data/processed/site03-association-diagnostic/summary.json');
const diagnostic=JSON.parse(fs.readFileSync(diagnosticPath));
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(diagnosticPath)).digest('hex'),data.association_review_sha256);
assert.equal(data.association_review.length,diagnostic.results.find(x=>x.radius===.5).same_reference_multiple_hypothesis_frames);
for(const event of data.association_review){
 assert.ok(event.hypotheses.length>=2);
 for(const source of event.sources){const h=data.hypotheses.find(x=>x.id===source.hypothesis_id);assert.ok(h);const sample=h.samples.find(x=>x.frame===event.frame);assert.ok(sample);assert.ok(sample.sources.some(x=>x.camera===source.camera&&x.id===source.local_id));}
}
const published=require('../walkflows/hypothesis_analytics.js').referenceTracks(data.reference,data.reference_frames);
assert.deepEqual(published.map(h=>h.samples.length),[399,355,295,1]);
assert.ok(published.every(h=>h.samples.every(s=>s.frame<399)));
const referenceZones=[{id:'south',name:'South',type:'zone',x1:-6,y1:-3,x2:3,y2:3},{id:'north',name:'North',type:'zone',x1:-6,y1:3.4,x2:3,y2:10}];
const trans=require('../walkflows/zone_transitions.js').summarize(published,referenceZones,{fps:15,margin:.1,minDuration:.2,maxInterval:.1,transitionWindow:30},require('../walkflows/hypothesis_analytics.js'));
assert.ok(trans.events.some(e=>e.hypothesis_id==='reference-0'&&e.from_id==='north'&&e.to_id==='south'&&e.exit_frame===99&&e.arrival_frame===114));
const c=require('../walkflows/source_comparison.js').compareSources(data.hypotheses,published,referenceZones,{start:0,end:399,referenceFrames:data.reference_frames},{fps:15,margin:.1,minDuration:.2,maxInterval:.1,transitionWindow:30},require('../walkflows/hypothesis_analytics.js'),require('../walkflows/zone_transitions.js'));
assert.equal(c.status,'ok');assert.equal(c.coverage.excluded_reference_missing_frames,1);assert.equal(c.reference.transitions.events.length,1);assert.equal(c.model.transitions.events.length,0);
const linkedFile=path.join(root,'data/processed/site03-tracklet-experiment/pose-linked.json');
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(linkedFile)).digest('hex'),data.research_metadata.linked_hypothesis_sha256);
const linkedResult=require('../walkflows/zone_transitions.js').summarize(data.linked_hypotheses,referenceZones,{fps:15,margin:.1,minDuration:.2,maxInterval:.1,transitionWindow:30},require('../walkflows/hypothesis_analytics.js'));
assert.equal(linkedResult.events.length,0);
assert.ok(linkedResult.interrupted.some(e=>e.from_id==='north'&&e.to_id==='south'&&e.exit_frame===102&&e.arrival_frame===127&&e.gap_resume_frames.includes(108)));
const linkedData={...data,hypotheses:data.linked_hypotheses,research_metadata:{...data.research_metadata,analysis_source:'experimental_linked'}};
const linkedReport=require('../walkflows/hypothesis_analytics.js').createResearchReport(linkedData,layout,{margin:.1,minDuration:.2,maxInterval:.1,columns:18,rows:26});
assert.equal(linkedReport.scope,'experimental_linked_not_validated_customer_counts');assert.equal(linkedReport.source.linked_hypothesis_sha256,data.research_metadata.linked_hypothesis_sha256);
const exampleFlow=require('../walkflows/layout.js').exampleFlow(data.scene,data.bounds);
const demo=require('../walkflows/source_comparison.js').compareSources(data.hypotheses,published,exampleFlow.items,{start:0,end:399,referenceFrames:data.reference_frames},{fps:15,margin:.1,minDuration:.2,maxInterval:.1,transitionWindow:30},require('../walkflows/hypothesis_analytics.js'),require('../walkflows/zone_transitions.js'));
assert.equal(demo.reference.transitions.events.length,1);assert.equal(demo.model.transitions.events.length,0);assert.equal(demo.reference.transitions.events[0].arrival_frame,114);
const quality=require('../walkflows/quality_report.js').summarize(data,{start:0,end:399},'pose');
assert.equal(quality.cameras.reduce((n,c)=>n+c.observation_rows,0),928);
assert.equal(quality.cameras.reduce((n,c)=>n+c.eligible_rows,0),549);
assert.equal(quality.reference_missing_frames,1);assert.equal(quality.hypotheses.spatial_conflicts,1);
assert.equal(quality.cameras.find(c=>c.camera==='C0001025_v1').frames_without_tracks,400);
const sceneBytes=fs.readFileSync(path.join(root,'data/upstream-research/site03_scene03.json'));const scene=JSON.parse(sceneBytes);
assert.equal(crypto.createHash('sha256').update(sceneBytes).digest('hex'),data.research_metadata.scene_sha256);
assert.deepEqual(data.camera_anchors,scene['bcam-keys'].map((camera,i)=>({camera,x:scene['bcam-transforms'][i].translation[0],y:scene['bcam-transforms'][i].translation[1],height:scene['bcam-transforms'][i].translation[2]})));
