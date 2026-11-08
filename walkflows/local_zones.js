/* Geometry-only reference events. No customer or identity inference. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WalkflowsZones = api;
})(globalThis, function () {
  "use strict";
  function validateZone(zone, bounds) {
    if (!zone || !Array.isArray(bounds) || bounds.length !== 4) return false;
    const values = [zone.x1, zone.y1, zone.x2, zone.y2, ...bounds];
    return values.every(Number.isFinite) && zone.x1 < zone.x2 && zone.y1 < zone.y2 &&
      zone.x1 >= bounds[0] && zone.y1 >= bounds[1] && zone.x2 <= bounds[2] && zone.y2 <= bounds[3];
  }
  function number(value) {
    if (value === null || value === undefined || (typeof value === "string" && !value.trim())) throw Error("missing reference value");
    const result = Number(value);
    if (!Number.isFinite(result)) throw Error("invalid reference value");
    return result;
  }
  function referenceEvents(points, zone) {
    // Scene bounds are validated separately by the caller.
    if (!zone || ![zone.x1,zone.y1,zone.x2,zone.y2].every(Number.isFinite) || zone.x1>=zone.x2 || zone.y1>=zone.y2) throw Error("invalid zone");
    let previous = null; const events = [];
    for (const p of points) {
      const frame=number(p.clip_frame), time=number(p.relative_s), x=number(p.floor_x), y=number(p.floor_y);
      if (!Number.isInteger(frame) || frame<0 || time<0 || (previous && (frame<=previous.frame || time<=previous.time))) throw Error("invalid reference order");
      const inside=x>=zone.x1 && x<=zone.x2 && y>=zone.y1 && y<=zone.y2;
      if (!previous && inside) events.push({kind:"initial_inside",frame,time});
      else if (previous && frame>previous.frame+1) {
        events.push({kind:"gap",from_frame:previous.frame+1,to_frame:frame-1,frame,time});
        if (inside) events.push({kind:"resumed_inside",frame,time});
      } else if (previous && inside!==previous.inside) events.push({kind:inside?"enter_candidate":"exit_candidate",frame,time});
      previous={frame,time,inside};
    }
    return events;
  }
  function stableReferenceEvents(points, zone, options) {
    if (!zone || ![zone.x1,zone.y1,zone.x2,zone.y2].every(Number.isFinite) || zone.x1>=zone.x2 || zone.y1>=zone.y2) throw Error("invalid zone");
    const {margin,minDuration,maxInterval}=options || {};
    if (![margin,minDuration,maxInterval].every(Number.isFinite) || margin<0 || minDuration<0 || maxInterval<=0) throw Error("invalid hysteresis options");
    const events=[]; let previous=null, stable=null, candidate=null, lastStable=null, afterGap=false;
    for (const p of points) {
      const frame=number(p.clip_frame),time=number(p.relative_s),x=number(p.floor_x),y=number(p.floor_y);
      if (!Number.isInteger(frame)||frame<0||time<0||(previous&&(frame<=previous.frame||time<=previous.time))) throw Error("invalid reference order");
      if (previous&&(frame!==previous.frame+1||time-previous.time>maxInterval+1e-9)) {
        events.push({kind:"gap",from_frame:previous.frame,to_frame:frame,frame,time});
        stable=null;candidate=null;lastStable=null;afterGap=true;
      }
      const inside=x>=zone.x1&&x<=zone.x2&&y>=zone.y1&&y<=zone.y2;
      const distance=inside?Math.min(x-zone.x1,zone.x2-x,y-zone.y1,zone.y2-y):-Math.hypot(Math.max(zone.x1-x,0,x-zone.x2),Math.max(zone.y1-y,0,y-zone.y2));
      const state=distance>=margin&&inside?"inside":distance<=-margin&&!inside?"outside":null;
      if (state===null) candidate=null;
      else if (state===stable) {candidate=null;lastStable={frame,time};}
      else {
        if (!candidate||candidate.state!==state) candidate={state,frame,time};
        if (time-candidate.time+1e-9>=minDuration) {
          if (stable===null) {
            if (state==="inside") events.push({kind:afterGap?"resumed_inside":"initial_inside",first_frame:candidate.frame,frame,time});
          } else events.push({kind:state==="inside"?"enter_candidate":"exit_candidate",first_frame:candidate.frame,previous_frame:lastStable.frame,previous_time:lastStable.time,frame,time});
          stable=state;lastStable={frame,time};candidate=null;
        }
      }
      previous={frame,time};
    }
    return events;
  }
  function referenceRoute(points, items, options) {
    if (!Array.isArray(items)) throw Error("invalid items");
    const ids=new Set(), groups=new Map();
    for (const item of items) {
      if (!item||typeof item.id!=="string"||!item.id||ids.has(item.id)||typeof item.name!=="string"||!item.name||!["zone","point"].includes(item.type)) throw Error("invalid item");
      ids.add(item.id);
      for (const event of stableReferenceEvents(points,item,options)) {
        const key=event.kind==="gap"?"gap:"+event.frame:"candidates:"+event.frame;
        if (!groups.has(key)) groups.set(key,{kind:event.kind==="gap"?"gap":"candidates",frame:event.frame,time:event.time,items:[]});
        if(event.kind!=="gap") groups.get(key).items.push({id:item.id,name:item.name,type:item.type,kind:event.kind,first_frame:event.first_frame});
      }
    }
    return [...groups.values()].sort((a,b)=>a.frame-b.frame||(a.kind==="gap"?-1:1));
  }
  return {validateZone,referenceEvents,stableReferenceEvents,referenceRoute};
});
