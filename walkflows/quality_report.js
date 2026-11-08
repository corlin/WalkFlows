/* Coverage of recorded research observations; never a detector recall estimate. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.WalkflowsQualityReport=factory()})(globalThis,function(){
 'use strict';
 function summarize(data,window,mode){
  if(!data||!Number.isSafeInteger(data.video_frames)||data.video_frames<1||!Number.isSafeInteger(data.reference_frames)||data.reference_frames<0||data.reference_frames>data.video_frames||!data.cameras||typeof data.cameras!=='object'||!Array.isArray(data.hypotheses)||!window||!Number.isSafeInteger(window.start)||!Number.isSafeInteger(window.end)||window.start<0||window.end<window.start||window.end>=data.video_frames||!['box','pose','hybrid'].includes(mode))throw Error('invalid quality request');
  const length=window.end-window.start+1,cameras=[];
  for(const [camera,rows] of Object.entries(data.cameras).sort(([a],[b])=>a.localeCompare(b))){
   if(!Array.isArray(rows))throw Error('invalid camera');const frames=new Set(),keys=new Set(),reasons={};let total=0,eligible=0,ambiguous=0;
   for(const row of rows){
    if(!Number.isSafeInteger(row.frame)||row.frame<0||row.frame>=data.video_frames||!Number.isSafeInteger(row.id)||row.id<0)throw Error('invalid observation');
    const key=row.frame+':'+row.id;if(keys.has(key))throw Error('duplicate observation');keys.add(key);
    if(row.frame<window.start||row.frame>window.end)continue;
    const flag=mode==='pose'?row.pose_candidate:mode==='hybrid'?row.hybrid_candidate:row.research_geometry_candidate;
    if(typeof flag!=='boolean')throw Error('invalid candidate flag');total++;frames.add(row.frame);if(flag)eligible++;if(mode==='pose'&&row.pose_status==='ambiguous')ambiguous++;
    if(!flag){const items=mode==='pose'?(row.pose_reason||'').split('|'):mode==='hybrid'?(row.hybrid_reasons||[]).filter(x=>!['floor_unvalidated','foot_visibility_unknown','sync_unvalidated'].includes(x)):['box_geometry_or_duplicate'];for(const reason of new Set(items.filter(Boolean)))reasons[reason]=(reasons[reason]||0)+1}
   }
   cameras.push({camera,observation_rows:total,frames_with_tracks:frames.size,frames_without_tracks:length-frames.size,eligible_rows:eligible,excluded_rows:total-eligible,ambiguous_pose_rows:mode==='pose'?ambiguous:null,exclusion_reasons:reasons});
  }
  let valid=0,conflicts=0;const ids=new Set();for(const h of data.hypotheses){if(!h||typeof h.id!=='string'||ids.has(h.id)||!Array.isArray(h.samples))throw Error('invalid hypothesis');ids.add(h.id);for(const sample of h.samples){if(!Number.isSafeInteger(sample.frame)||sample.frame<0||sample.frame>=data.video_frames||!['research_candidate','spatial_conflict'].includes(sample.status))throw Error('invalid sample');if(sample.frame>=window.start&&sample.frame<=window.end){if(sample.status==='spatial_conflict')conflicts++;else valid++}}}
  return {scope:'coverage_not_detection_recall_or_customer_counts',window:{start:window.start,end:window.end},projection:mode,reference_missing_frames:Math.max(0,window.end-Math.max(window.start,data.reference_frames)+1),cameras,hypotheses:{tracks:data.hypotheses.length,valid_samples:valid,spatial_conflicts:conflicts}};
 }
 return {summarize};
});
