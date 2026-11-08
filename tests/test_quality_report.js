const assert=require('node:assert/strict');const q=require('../walkflows/quality_report.js');
const data={video_frames:4,reference_frames:3,cameras:{a:[{frame:0,id:1,pose_candidate:true,pose_status:'unique',pose_reason:''},{frame:0,id:2,pose_candidate:false,pose_status:'ambiguous',pose_reason:'pose_foot_unavailable|local_duplicate_candidate'},{frame:2,id:1,pose_candidate:false,pose_status:'no_candidate',pose_reason:'pose_foot_unavailable'}]},hypotheses:[{id:'h',samples:[{frame:0,status:'research_candidate'},{frame:1,status:'spatial_conflict'}]}]};
const r=q.summarize(data,{start:0,end:3},'pose');assert.equal(r.cameras[0].observation_rows,3);assert.equal(r.cameras[0].frames_with_tracks,2);assert.equal(r.cameras[0].frames_without_tracks,2);assert.equal(r.cameras[0].eligible_rows,1);assert.deepEqual(r.cameras[0].exclusion_reasons,{pose_foot_unavailable:2,local_duplicate_candidate:1});assert.equal(r.reference_missing_frames,1);assert.equal(r.hypotheses.spatial_conflicts,1);
assert.throws(()=>q.summarize(data,{start:4,end:4},'pose'));assert.throws(()=>q.summarize(data,{start:0,end:3},'unknown'));
console.log('quality report tests passed');
const duplicate=structuredClone(data);duplicate.cameras.a.push({...duplicate.cameras.a[0]});assert.throws(()=>q.summarize(duplicate,{start:0,end:3},'pose'));
const last=q.summarize(data,{start:3,end:3},'pose');assert.equal(last.reference_missing_frames,1);assert.equal(last.cameras[0].frames_without_tracks,1);
const hybrid={video_frames:1,reference_frames:1,cameras:{a:[{frame:0,id:1,hybrid_candidate:false,hybrid_reasons:['position_unavailable','floor_unvalidated','sync_unvalidated']}]},hypotheses:[]};
assert.deepEqual(q.summarize(hybrid,{start:0,end:0},'hybrid').cameras[0].exclusion_reasons,{position_unavailable:1});
