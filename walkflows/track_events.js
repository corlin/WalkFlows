/* Per-camera local track analysis only; no fused identity or customer counts. */
(function(root,factory){
  if(typeof module==='object'&&module.exports) module.exports=factory(require('./local_zones.js'));
  else root.WalkflowsTrackEvents=factory(root.WalkflowsZones);
})(globalThis,function(zones){
  'use strict';
  function qualityReasons(q){
    if(!q||![q.inside_hull,q.in_scene,q.forward_ray].every(v=>v===null||typeof v==='boolean')||![q.duplicate_candidate,q.floor_validated,q.sync_validated].every(v=>typeof v==='boolean')||!['visible','occluded','unknown'].includes(q.foot_visibility)) throw Error('invalid quality');
    const reasons=[];
    for(const [value,no,unknown] of [[q.inside_hull,'outside_calibration_hull','calibration_domain_unknown'],[q.in_scene,'outside_scene_bounds','scene_domain_unknown'],[q.forward_ray,'invalid_ray','ray_validity_unknown']]) if(value!==true) reasons.push(value===false?no:unknown);
    if(q.duplicate_candidate) reasons.push('local_duplicate_candidate');
    if(!q.floor_validated) reasons.push('floor_unvalidated');
    if(q.foot_visibility!=='visible') reasons.push(q.foot_visibility==='occluded'?'foot_occluded':'foot_visibility_unknown');
    if(!q.sync_validated) reasons.push('sync_unvalidated');
    return reasons;
  }
  function analyzeTrack(observations,zone,options,mode){
    if(!Array.isArray(observations)||!['strict','research'].includes(mode)) throw Error('invalid track request');
    let camera=null,id=null,last=-1;const points=[],reasons=new Set();
    for(const row of observations){
      if(!row||typeof row.camera!=='string'||!row.camera.trim()||!Number.isSafeInteger(row.local_id)||row.local_id<0||!Number.isSafeInteger(row.frame)||row.frame<0||!Number.isFinite(row.timestamp_s)||row.timestamp_s<0||!Array.isArray(row.xy)||row.xy.length!==2||!row.xy.every(Number.isFinite)) throw Error('invalid observation');
      if(camera===null){camera=row.camera;id=row.local_id;}
      if(row.camera!==camera||row.local_id!==id||row.frame<=last) throw Error('track must be ordered and camera-local');
      last=row.frame;
      const q=row.quality, why=qualityReasons(q);
      if(!Array.isArray(row.reasons)||row.reasons.length!==why.length||!row.reasons.every((reason,i)=>reason===why[i])) throw Error('quality reason mismatch');
      const blocked=q.inside_hull!==true||q.in_scene!==true||q.forward_ray!==true||q.duplicate_candidate;
      const status=blocked?'hard_excluded':why.length?'research_candidate_only':'strict_candidate';
      if(row.status!==status) throw Error('quality status mismatch');
      if(status==='strict_candidate'||(mode==='research'&&status==='research_candidate_only')){
        why.forEach(reason=>reasons.add(reason));
        points.push({clip_frame:row.frame,relative_s:row.timestamp_s,floor_x:row.xy[0],floor_y:row.xy[1]});
      }
    }
    return {camera,local_id:id,mode,total:observations.length,selected:points.length,reasons:[...reasons].sort(),points,events:zones.stableReferenceEvents(points,zone,options)};
  }
  function createReport(observations,zone,options,mode,layout){
    if(!layout||typeof layout.scene!=='string'||!layout.scene.trim()||!Number.isSafeInteger(layout.revision)||layout.revision<1) throw Error('invalid layout provenance');
    const analysis=analyzeTrack(observations,zone,options,mode);
    return structuredClone({schema_version:1,algorithm:'local-zone-hysteresis-v1',scope:mode==='research'?'camera_local_research':'camera_local_strict',layout:{scene:layout.scene,revision:layout.revision},zone,options,analysis,observations});
  }
  return {analyzeTrack,createReport};
});
