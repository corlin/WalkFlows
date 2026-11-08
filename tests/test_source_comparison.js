const assert=require('node:assert/strict');
const {compareSources}=require('../walkflows/source_comparison.js');
const analytics=require('../walkflows/hypothesis_analytics.js'),trans=require('../walkflows/zone_transitions.js');
const h=(id,frames)=>({id,members:[],samples:frames.map(frame=>({frame,x:1,y:1,status:'research_candidate'}))});
const zones=[{id:'a',name:'A',type:'zone',x1:0,y1:0,x2:2,y2:2}];
const opts={fps:1,margin:0,minDuration:0,maxInterval:1,transitionWindow:30};
const r=compareSources([h('m',[0,1,2])],[h('r',[0,1])],zones,{start:1,end:2,referenceFrames:2},opts,analytics,trans);
assert.deepEqual(r.coverage,{requested_start:1,requested_end:2,compared_start:1,compared_end:1,excluded_reference_missing_frames:1});
assert.equal(r.model.areas[0].observed_hypotheses,1);assert.equal(r.reference.areas[0].observed_hypotheses,1);
assert.equal(compareSources([h('m',[2])],[h('r',[0])],zones,{start:2,end:2,referenceFrames:2},opts,analytics,trans).status,'no_reference_coverage');
assert.throws(()=>compareSources([],[],zones,{start:2,end:1,referenceFrames:2},opts,analytics,trans));
console.log('source comparison tests passed');

const select=require('../walkflows/source_comparison.js').selectComparisonSource;
const base=[h('base',[0])],direct=[h('direct',[0])];
assert.deepEqual(select('baseline',base,direct,{hypothesis_sha256:'a'.repeat(64),direct_hypothesis_sha256:'b'.repeat(64)}),{hypotheses:base,source:'baseline',sha256:'a'.repeat(64)});
assert.deepEqual(select('direct',base,direct,{hypothesis_sha256:'a'.repeat(64),direct_hypothesis_sha256:'b'.repeat(64)}),{hypotheses:direct,source:'experimental_direct_pose',sha256:'b'.repeat(64)});
assert.throws(()=>select('direct',base,null,{hypothesis_sha256:'a'.repeat(64)}));
assert.throws(()=>select('unknown',base,direct,{hypothesis_sha256:'a'.repeat(64)}));
