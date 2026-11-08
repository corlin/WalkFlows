/* Ordered research candidate funnel; no unique people or confirmed business acts. */
(function(root,factory){
 if(typeof module==='object'&&module.exports)module.exports=factory(require('./hypothesis_analytics.js'));
 else root.WalkflowsResearchFunnel=factory(root.WalkflowsHypothesisAnalytics);
})(globalThis,function(analytics){
 'use strict';
 function buildFunnel(hypotheses,items,zoneIds,options){
  if(!Array.isArray(hypotheses)||!Array.isArray(items)||!Array.isArray(zoneIds)||zoneIds.length<2||zoneIds.length>10||new Set(zoneIds).size!==zoneIds.length||!options||![options.window_s,options.fps,options.margin,options.minDuration,options.maxInterval].every(Number.isFinite)||options.window_s<=0||options.fps<=0||options.margin<0||options.minDuration<0||options.maxInterval<=0)throw Error('invalid funnel settings');
  const zoneMap=new Map();for(const item of items){if(!item||typeof item.id!=='string'||!item.id||typeof item.name!=='string'||!item.name.trim()||!['zone','point'].includes(item.type)||![item.x1,item.y1,item.x2,item.y2].every(Number.isFinite)||item.x1>=item.x2||item.y1>=item.y2||zoneMap.has(item.id))throw Error('invalid zone');zoneMap.set(item.id,item)}
  if(zoneIds.some(id=>typeof id!=='string'||!zoneMap.has(id)))throw Error('unknown funnel zone');
  const ids=new Set(),tracks=[];
  for(const h of hypotheses){
   if(!h||typeof h.id!=='string'||!h.id||ids.has(h.id))throw Error('invalid hypothesis');ids.add(h.id);
   const route=analytics.researchRoute(h,zoneIds.map(id=>zoneMap.get(id)),options),states=Array(zoneIds.length+1).fill(null);states[0]=[];let best=[],interruptions=0,gaps=0;
   for(const group of route){
    for(let i=1;i<states.length;i++)if(states[i]&&group.time-states[i][0].time>options.window_s+1e-9)states[i]=null;
    if(group.kind==='gap'){gaps++;if(states.some((v,i)=>i>0&&i<zoneIds.length&&v))interruptions++;for(let i=1;i<states.length;i++)states[i]=null;continue}
    const old=states.map(v=>v&&v.slice());
    for(let step=0;step<zoneIds.length;step++){
     const item=group.items.find(x=>x.id===zoneIds[step]&&['initial_inside','resumed_inside','enter_candidate'].includes(x.kind));
     const previous=old[step];if(!item||!previous||(previous.length&&group.frame<=previous[previous.length-1].frame)||(previous.length&&group.time-previous[0].time>options.window_s+1e-9))continue;
     const next=[...previous,{zone_id:item.id,frame:group.frame,time:group.time,kind:item.kind}];
     if(!states[step+1]||next[0].time>=states[step+1][0].time)states[step+1]=next;
     if(next.length>best.length)best=next;
    }
   }
   tracks.push({id:h.id,reached:best.length,evidence:best,gaps,interruptions});
  }
  return {scope:'research_hypotheses_not_customers',window_s:options.window_s,steps:zoneIds.map((id,index)=>({zone_id:id,name:zoneMap.get(id).name,hypotheses:tracks.filter(t=>t.reached>index).length})),tracks};
 }
 return {buildFunnel};
});
