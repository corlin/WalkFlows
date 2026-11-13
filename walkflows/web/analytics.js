"use strict";
function candidatePairs(left, right, maxDistance) {
  if (!Number.isFinite(maxDistance) || maxDistance <= 0) throw Error("invalid distance");
  const edges=[], leftCount=new Map(), rightCount=new Map();
  for (const a of left) for (const b of right) {
    if (a.id === "" || b.id === "" || ![a.x,a.y,b.x,b.y].every(Number.isFinite)) continue;
    const distance=Math.hypot(a.x-b.x,a.y-b.y);
    if (distance<=maxDistance) {
      edges.push({left:a,right:b,distance});
      leftCount.set(a.id,(leftCount.get(a.id)||0)+1);
      rightCount.set(b.id,(rightCount.get(b.id)||0)+1);
    }
  }
  const unique=[],ambiguous=[];
  for(const edge of edges) {
    (leftCount.get(edge.left.id)===1 && rightCount.get(edge.right.id)===1 ? unique : ambiguous).push(edge);
  }
  return {unique,ambiguous};
}
function pointInPolygon(point, polygon) {
  if (!Array.isArray(point) || point.length!==2 || !point.every(Number.isFinite) ||
      !Array.isArray(polygon) || polygon.length<3) return false;
  const [x,y]=point;let inside=false;
  for(let i=0,j=polygon.length-1;i<polygon.length;j=i++) {
    const [xi,yi]=polygon[i],[xj,yj]=polygon[j];
    const cross=(x-xi)*(yj-yi)-(y-yi)*(xj-xi);
    if(Math.abs(cross)<1e-9 && x>=Math.min(xi,xj)-1e-9 && x<=Math.max(xi,xj)+1e-9 &&
       y>=Math.min(yi,yj)-1e-9 && y<=Math.max(yi,yj)+1e-9) return true;
    if((yi>y)!==(yj>y) && x<(xj-xi)*(y-yi)/(yj-yi)+xi)inside=!inside;
  }
  return inside;
}
function zoneTransitions(observations, polygon) {
  const groups=new Map();
  for (const p of observations) {
    if (p.id==="" || p.id===null || p.id===undefined || !Number.isInteger(p.frame) ||
        p.frame<0 || ![p.x,p.y,p.time].every(Number.isFinite)) continue;
    const key=String(p.id);
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(p);
  }
  const result=[];
  for (const [id,points] of groups) {
    points.sort((a,b)=>a.frame-b.frame);
    const counts=new Map();for(const p of points)counts.set(p.frame,(counts.get(p.frame)||0)+1);
    let previous=null;
    for (const p of points) {
      if(counts.get(p.frame)!==1){previous=null;continue;}
      const inside=pointInPolygon([p.x,p.y],polygon);
      if(previous && p.frame===previous.frame+1 && inside!==previous.inside)
        result.push({id,frame:p.frame,time:p.time,type:inside?"enter":"exit",x:p.x,y:p.y});
      previous={frame:p.frame,inside};
    }
  }
  return result.sort((a,b)=>a.time-b.time || a.id.localeCompare(b.id));
}
function heatGrid(points, bounds, size) {
  if(!Array.isArray(bounds) || bounds.length!==4 || !bounds.every(Number.isFinite) ||
     !Number.isInteger(size) || size<1 || size>200) throw Error("invalid heat grid");
  const [xmin,ymin,xmax,ymax]=bounds, dx=Math.max(xmax-xmin,1e-9),dy=Math.max(ymax-ymin,1e-9);
  const cells=Array(size*size).fill(0);
  for(const p of points) {
    if(![p.x,p.y].every(Number.isFinite) || p.x<xmin || p.x>xmax || p.y<ymin || p.y>ymax)continue;
    const x=Math.min(size-1,Math.floor((p.x-xmin)/dx*size));
    const y=Math.min(size-1,Math.floor((p.y-ymin)/dy*size));
    cells[y*size+x]++;
  }
  return cells;
}
if (typeof module !== "undefined") module.exports={candidatePairs,pointInPolygon,zoneTransitions,heatGrid};
