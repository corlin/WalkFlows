/* Experimental hypothesis analytics: unverified associations and coordinates. */
(function(root,factory){
 if(typeof module==='object'&&module.exports) module.exports=factory(require('./local_zones.js'),require('./layout.js'));
 else root.WalkflowsHypothesisAnalytics=factory(root.WalkflowsZones,root.WalkflowsLayout);
})(globalThis,function(zones,layoutApi){
 'use strict';
 function validSamples(h){
  if(!h||typeof h.id!=='string'||!h.id||!Array.isArray(h.samples))throw Error('invalid hypothesis');
  let last=-1;
  for(const s of h.samples){
   if(!s||!Number.isSafeInteger(s.frame)||s.frame<0||s.frame<=last||!['research_candidate','spatial_conflict'].includes(s.status))throw Error('invalid hypothesis sample');
   if(s.status==='research_candidate'&&(!Number.isFinite(s.x)||!Number.isFinite(s.y)))throw Error('invalid position');
   if(s.status==='spatial_conflict'&&(s.x!==null||s.y!==null))throw Error('conflict must not carry position');
   last=s.frame;
  }
 }
 function referenceTracks(reference,frameCount){
  if(!reference||typeof reference!=='object'||Array.isArray(reference)||!Number.isSafeInteger(frameCount)||frameCount<1)throw Error('invalid reference');
  const tracks=new Map();
  for(const [key,points] of Object.entries(reference)){
   const frame=Number(key);if(!Number.isSafeInteger(frame)||frame<0||frame>=frameCount||String(frame)!==key||!Array.isArray(points))throw Error('invalid reference frame');
   const ids=new Set();for(const p of points){
    if(!p||!Number.isSafeInteger(p.id)||p.id<0||ids.has(p.id)||!Number.isFinite(p.x)||!Number.isFinite(p.y))throw Error('invalid reference point');ids.add(p.id);
    if(!tracks.has(p.id))tracks.set(p.id,[]);tracks.get(p.id).push({frame,x:p.x,y:p.y,status:'research_candidate',sources:[{kind:'published_reference',id:p.id}]});
   }
  }
  return [...tracks.entries()].sort((a,b)=>a[0]-b[0]).map(([id,samples])=>({id:'reference-'+id,members:[],reference_id:id,samples:samples.sort((a,b)=>a.frame-b.frame)}));
 }
 function sliceHypotheses(hypotheses,startFrame,endFrame){
  if(!Array.isArray(hypotheses)||!Number.isSafeInteger(startFrame)||!Number.isSafeInteger(endFrame)||startFrame<0||endFrame<startFrame)throw Error('invalid analysis window');
  const ids=new Set();return hypotheses.map(h=>{validSamples(h);if(ids.has(h.id))throw Error('duplicate hypothesis');ids.add(h.id);return {...h,samples:h.samples.filter(s=>s.frame>=startFrame&&s.frame<=endFrame)};});
 }
 function zoneEvents(h,zone,options){
  validSamples(h);if(!options||!Number.isFinite(options.fps)||options.fps<=0)throw Error('invalid fps');
  const points=h.samples.filter(s=>s.status==='research_candidate').map(s=>({clip_frame:s.frame,relative_s:s.frame/options.fps,floor_x:s.x,floor_y:s.y}));
  const events=zones.stableReferenceEvents(points,zone,options),eventFrames=new Map();
  for(const event of events){if(!eventFrames.has(event.frame))eventFrames.set(event.frame,[]);eventFrames.get(event.frame).push(event)}
  let inside=false,previous=null,intervals=0;
  const interior=p=>p.floor_x>=zone.x1+options.margin&&p.floor_x<=zone.x2-options.margin&&p.floor_y>=zone.y1+options.margin&&p.floor_y<=zone.y2-options.margin;
  for(const p of points){
   const wasInside=inside;
   for(const event of eventFrames.get(p.clip_frame)||[]){if(event.kind==='gap'||event.kind==='exit_candidate')inside=false;else if(['initial_inside','resumed_inside','enter_candidate'].includes(event.kind))inside=true}
   if(previous&&wasInside&&inside&&p.clip_frame===previous.clip_frame+1&&p.relative_s-previous.relative_s<=options.maxInterval+1e-9&&interior(previous)&&interior(p))intervals++;
   previous=p;
  }
  return {total:h.samples.length,selected:points.length,events,observed_inside_seconds:intervals/options.fps,inside_intervals:intervals};
 }
 function summarizeArea(hypotheses,zone,options){
  if(!Array.isArray(hypotheses))throw Error('invalid hypotheses');const seen=new Set(),items=[];
  for(const h of hypotheses){if(seen.has(h.id))throw Error('duplicate hypothesis');seen.add(h.id);items.push({id:h.id,...zoneEvents(h,zone,options)})}
  const events=items.flatMap(x=>x.events);
  return {hypotheses:items,observed_hypotheses:items.filter(x=>x.events.some(e=>['initial_inside','resumed_inside','enter_candidate'].includes(e.kind))).length,candidate_enter_events:events.filter(e=>e.kind==='enter_candidate').length,initial_or_resumed_inside:events.filter(e=>['initial_inside','resumed_inside'].includes(e.kind)).length,observed_inside_seconds:items.reduce((total,x)=>total+x.observed_inside_seconds,0)};
 }
 function heatmap(hypotheses,bounds,options){
  if(!Array.isArray(hypotheses)||!Array.isArray(bounds)||bounds.length!==4||!bounds.every(Number.isFinite)||bounds[0]>=bounds[2]||bounds[1]>=bounds[3]||!options||!Number.isSafeInteger(options.columns)||options.columns<1||!Number.isSafeInteger(options.rows)||options.rows<1||!Number.isFinite(options.fps)||options.fps<=0)throw Error('invalid heatmap settings');
  const {columns,rows,fps}=options,grid=()=>Array.from({length:rows},()=>Array(columns).fill(0)),result={samples:grid(),crossings:grid(),seconds:grid(),starts:grid(),visitors:grid()},ids=new Set();
  for(const h of hypotheses){
   validSamples(h);if(ids.has(h.id))throw Error('duplicate hypothesis');ids.add(h.id);let prev=null;const visited=new Set();
   for(const s of h.samples){
    if(s.status!=='research_candidate'){prev=null;continue}
    if(s.x<bounds[0]||s.x>bounds[2]||s.y<bounds[1]||s.y>bounds[3])throw Error('outside scene');
    const col=Math.min(columns-1,Math.floor((s.x-bounds[0])*columns/(bounds[2]-bounds[0]))),row=Math.min(rows-1,Math.floor((s.y-bounds[1])*rows/(bounds[3]-bounds[1])));
    result.samples[row][col]++;const cell=row+':'+col;if(!visited.has(cell)){visited.add(cell);result.visitors[row][col]++}
    if(!prev||s.frame!==prev.frame+1)result.starts[row][col]++;
    else if(prev.col!==col||prev.row!==row)result.crossings[row][col]++;
    else result.seconds[row][col]+=1/fps;
    prev={frame:s.frame,col,row};
   }
  }
  return result;
 }
 function researchRoute(h,items,options){
  validSamples(h);if(!options||!Number.isFinite(options.fps)||options.fps<=0)throw Error('invalid fps');
  const points=h.samples.filter(s=>s.status==='research_candidate').map(s=>({clip_frame:s.frame,relative_s:s.frame/options.fps,floor_x:s.x,floor_y:s.y}));
  return zones.referenceRoute(points,items,options);
 }
 function createResearchReport(data,layout,options){
  if(!data||typeof data.scene!=='string'||!data.research_metadata||typeof data.research_metadata.hypothesis_sha256!=='string'||!/^[0-9a-f]{64}$/.test(data.research_metadata.hypothesis_sha256)||!options)throw Error('invalid source metadata');
  if(data.research_metadata.analysis_source==='published_reference'&&(typeof data.research_metadata.reference_sha256!=='string'||!/^[0-9a-f]{64}$/.test(data.research_metadata.reference_sha256)))throw Error('invalid reference metadata');
  if(data.research_metadata.analysis_source==='experimental_linked'&&(typeof data.research_metadata.linked_hypothesis_sha256!=='string'||!/^[0-9a-f]{64}$/.test(data.research_metadata.linked_hypothesis_sha256)))throw Error('invalid linked metadata');
  const safeLayout=layoutApi.validateLayout(layout,data.bounds,data.scene),settings={margin:options.margin,minDuration:options.minDuration,maxInterval:options.maxInterval,fps:data.fps,columns:options.columns,rows:options.rows};
  const maps=heatmap(data.hypotheses,data.bounds,settings),areas=safeLayout.items.map(zone=>({zone_id:zone.id,...summarizeArea(data.hypotheses,zone,settings)}));
  return structuredClone({schema_version:1,scope:data.research_metadata.analysis_source==='published_reference'?'published_reference_not_validated_customer_counts':data.research_metadata.analysis_source==='experimental_linked'?'experimental_linked_not_validated_customer_counts':'unverified_research_hypotheses_not_customer_counts',source:data.research_metadata,scene:data.scene,bounds:data.bounds,layout:safeLayout,settings,hypotheses:data.hypotheses,areas,routes:data.hypotheses.map(h=>({id:h.id,events:researchRoute(h,safeLayout.items,settings)})),heatmaps:maps});
 }
 return {referenceTracks,sliceHypotheses,zoneEvents,summarizeArea,heatmap,researchRoute,createResearchReport};
});
