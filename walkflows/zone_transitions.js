/* Conservative region-to-region candidates; not customer journeys. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.WalkflowsZoneTransitions=factory()})(globalThis,function(){
 'use strict';
 function extractTransitions(route,maxSeconds){
  if(!Array.isArray(route)||!Number.isFinite(maxSeconds)||maxSeconds<=0)throw Error('invalid transition input');
  let last=-1,active=new Set(),pending=null,tainted=false;const results=[];
  for(const group of route){
   if(!group||!Number.isSafeInteger(group.frame)||group.frame<last||!Number.isFinite(group.time)||!['gap','candidates'].includes(group.kind)||!Array.isArray(group.items))throw Error('invalid route');last=group.frame;
   if(group.kind==='gap'){active.clear();pending=null;tainted=false;continue}
   const entries=group.items.filter(x=>['initial_inside','resumed_inside','enter_candidate'].includes(x.kind)),exits=group.items.filter(x=>x.kind==='exit_candidate');
   if(entries.some(x=>typeof x.id!=='string'||!x.id)||exits.some(x=>typeof x.id!=='string'||!x.id))throw Error('invalid event');
   const before=new Set(active),ambiguous=entries.length>1||exits.length>1||(entries.length>0&&exits.length>0);
   if(ambiguous){pending=null;tainted=true}
   for(const e of exits)active.delete(e.id);
   if(!ambiguous&&exits.length===1){
    const e=exits[0];pending=before.size===1&&before.has(e.id)&&!tainted?{id:e.id,frame:group.frame,time:group.time}:null;
   }
   for(const e of entries){
    if(!ambiguous&&e.kind==='enter_candidate'&&active.size===0&&pending&&e.id!==pending.id&&group.frame>pending.frame&&group.time-pending.time<=maxSeconds+1e-9)results.push({from_id:pending.id,to_id:e.id,exit_frame:pending.frame,exit_time:pending.time,arrival_frame:group.frame,arrival_time:group.time});
    if(active.size>0&&!active.has(e.id))tainted=true;
    active.add(e.id);pending=null;
   }
   if(active.size>1){tainted=true;pending=null}
   if(active.size===0&&tainted){tainted=false;pending=null}
  }
  return results;
 }
 function extractInterrupted(route,maxSeconds){
  if(!Array.isArray(route)||!Number.isFinite(maxSeconds)||maxSeconds<=0)throw Error('invalid transition input');
  let last=-1,active=new Set(),pending=null,tainted=false;const results=[];
  for(const group of route){
   if(!group||!Number.isSafeInteger(group.frame)||group.frame<last||!Number.isFinite(group.time)||!['gap','candidates'].includes(group.kind)||!Array.isArray(group.items))throw Error('invalid route');last=group.frame;
   if(pending&&group.time-pending.time>maxSeconds+1e-9)pending=null;
   if(group.kind==='gap'){active.clear();tainted=false;if(pending)pending.gaps.push(group.frame);continue}
   const entries=group.items.filter(x=>['initial_inside','resumed_inside','enter_candidate'].includes(x.kind)),exits=group.items.filter(x=>x.kind==='exit_candidate');
   if(entries.some(x=>typeof x.id!=='string'||!x.id)||exits.some(x=>typeof x.id!=='string'||!x.id))throw Error('invalid event');
   const before=new Set(active),ambiguous=entries.length>1||exits.length>1||(entries.length>0&&exits.length>0);
   if(ambiguous){pending=null;tainted=true}
   for(const e of exits)active.delete(e.id);
   if(!ambiguous&&exits.length===1){const e=exits[0];pending=before.size===1&&before.has(e.id)&&!tainted?{id:e.id,frame:group.frame,time:group.time,gaps:[]}:null}
   for(const e of entries){
    if(!ambiguous&&pending&&pending.gaps.length&&active.size===0&&e.kind==='resumed_inside'&&e.id!==pending.id&&group.frame>pending.frame)results.push({from_id:pending.id,to_id:e.id,exit_frame:pending.frame,exit_time:pending.time,arrival_frame:group.frame,arrival_time:group.time,gap_resume_frames:pending.gaps.slice()});
    if(active.size>0&&!active.has(e.id))tainted=true;active.add(e.id);pending=null;
   }
   if(active.size>1){tainted=true;pending=null}if(active.size===0&&tainted){tainted=false;pending=null}
  }
  return results;
 }
 function summarize(hypotheses,items,options,analytics){
  if(!Array.isArray(hypotheses)||!Array.isArray(items)||!options||!analytics)throw Error('invalid request');
  const pairs=new Map(),events=[],interrupted=[];
  for(const h of hypotheses){
   const route=analytics.researchRoute(h,items,options);
   for(const e of extractInterrupted(route,options.transitionWindow))interrupted.push({hypothesis_id:h.id,...e});
   for(const e of extractTransitions(route,options.transitionWindow)){const event={hypothesis_id:h.id,...e};events.push(event);const key=JSON.stringify([e.from_id,e.to_id]);if(!pairs.has(key))pairs.set(key,{from_id:e.from_id,to_id:e.to_id,count:0,hypotheses:new Set()});const pair=pairs.get(key);pair.count++;pair.hypotheses.add(h.id)}
  }
  return {scope:'research_candidates_not_people_or_verified_transitions',window_s:options.transitionWindow,interrupted,pairs:[...pairs.values()].map(p=>({from_id:p.from_id,to_id:p.to_id,count:p.count,hypotheses:p.hypotheses.size})).sort((a,b)=>b.count-a.count||a.from_id.localeCompare(b.from_id)||a.to_id.localeCompare(b.to_id)),events};
 }
 return {extractTransitions,extractInterrupted,summarize};
});
