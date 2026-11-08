/* Camera-local experimental geometry only; no global identity or business events. */
(function(root,factory){
 if(typeof module==='object'&&module.exports) module.exports=factory(require('./local_zones.js'));
 else root.WalkflowsSite03Events=factory(root.WalkflowsZones);
})(globalThis,function(zones){
 'use strict';
 function trackZoneEvents(rows,id,mode,zone,options){
  if(!Array.isArray(rows)||!Number.isSafeInteger(id)||id<0||!['box','pose','hybrid'].includes(mode)||!options||!Number.isFinite(options.fps)||options.fps<=0)throw Error('invalid request');
  const own=rows.filter(r=>r.id===id).slice().sort((a,b)=>a.frame-b.frame),points=[];let last=-1;
  for(const r of own){
   if(!Number.isSafeInteger(r.frame)||r.frame<0||r.frame<=last||typeof r.research_geometry_candidate!=='boolean'||typeof r.pose_candidate!=='boolean'||(mode==='hybrid'&&typeof r.hybrid_candidate!=='boolean'))throw Error('invalid observation');
   last=r.frame;const selected=mode==='pose'?r.pose_candidate:mode==='hybrid'?r.hybrid_candidate:r.research_geometry_candidate;
   if(selected){const x=mode==='pose'?r.pose_x:mode==='hybrid'?r.hybrid_x:r.x,y=mode==='pose'?r.pose_y:mode==='hybrid'?r.hybrid_y:r.y;if(!Number.isFinite(x)||!Number.isFinite(y))throw Error('invalid position');points.push({clip_frame:r.frame,relative_s:r.frame/options.fps,floor_x:x,floor_y:y})}
  }
  return {total:own.length,selected:points.length,events:zones.stableReferenceEvents(points,zone,options)};
 }
 return {trackZoneEvents};
});
