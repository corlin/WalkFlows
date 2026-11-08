/* Portable, scene-specific research layouts. Versions are local revisions. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object' && module.exports) module.exports=api;
  else root.WalkflowsLayout=api;
})(globalThis,function(){
  'use strict';
  function rectangleFromCanvas(start,end,bounds,view){
    if(!Array.isArray(start)||start.length!==2||!Array.isArray(end)||end.length!==2||!Array.isArray(bounds)||bounds.length!==4||!view||![...start,...end,...bounds,view.left,view.top,view.scale].every(Number.isFinite)||view.scale<=0||bounds[0]>=bounds[2]||bounds[1]>=bounds[3])throw Error('invalid canvas rectangle');
    const [l,t,r,b]=bounds,maxX=view.left+(r-l)*view.scale,maxY=view.top+(b-t)*view.scale;
    if(start[0]<view.left||start[0]>maxX||start[1]<view.top||start[1]>maxY)throw Error('start outside scene');
    const x=Math.max(view.left,Math.min(maxX,end[0])),y=Math.max(view.top,Math.min(maxY,end[1]));
    if(Math.abs(x-start[0])<4||Math.abs(y-start[1])<4)throw Error('rectangle too small');
    const round=n=>Number(n.toFixed(3)),x1=Math.max(l,round(l+(Math.min(start[0],x)-view.left)/view.scale)),x2=Math.min(r,round(l+(Math.max(start[0],x)-view.left)/view.scale)),y1=Math.max(t,round(t+(Math.min(start[1],y)-view.top)/view.scale)),y2=Math.min(b,round(t+(Math.max(start[1],y)-view.top)/view.scale));
    if(x1>=x2||y1>=y2)throw Error('rectangle too small');return {x1,y1,x2,y2};
  }
  function emptyLayout(scene){
    if(typeof scene!=='string'||!scene.trim()) throw Error('invalid scene');
    return {schema_version:1,scene,revision:1,items:[]};
  }
  function validateLayout(layout,bounds,scene){
    if(!Array.isArray(bounds)||bounds.length!==4||!bounds.every(Number.isFinite)||bounds[0]>=bounds[2]||bounds[1]>=bounds[3]) throw Error('invalid scene bounds');
    if(!layout||layout.schema_version!==1||typeof scene!=='string'||!scene.trim()||layout.scene!==scene||!Number.isSafeInteger(layout.revision)||layout.revision<1||!Array.isArray(layout.items)||layout.items.length>200) throw Error('invalid layout');
    const ids=new Set();
    const items=layout.items.map(item=>{
      if(!item||typeof item.id!=='string'||!/^[-a-zA-Z0-9_]{1,80}$/.test(item.id)||ids.has(item.id)||typeof item.name!=='string'||!item.name.trim()||item.name.length>60||!['zone','point'].includes(item.type)||![item.x1,item.y1,item.x2,item.y2].every(Number.isFinite)||item.x1>=item.x2||item.y1>=item.y2||item.x1<bounds[0]||item.y1<bounds[1]||item.x2>bounds[2]||item.y2>bounds[3]) throw Error('invalid layout item');
      ids.add(item.id);
      return {id:item.id,name:item.name.trim(),type:item.type,x1:item.x1,y1:item.y1,x2:item.x2,y2:item.y2};
    });
    return {schema_version:1,scene,revision:layout.revision,items};
  }
  function saveItem(layout,item,bounds,scene){
    const source=validateLayout(layout,bounds,scene);
    if(source.revision===Number.MAX_SAFE_INTEGER) throw Error('revision exhausted');
    const at=source.items.findIndex(x=>x.id===item.id);
    if(at<0) source.items.push(item); else source.items[at]=item;
    source.revision++;
    return validateLayout(source,bounds,scene);
  }
  function removeItem(layout,id,bounds,scene){
    const source=validateLayout(layout,bounds,scene);
    if(source.revision===Number.MAX_SAFE_INTEGER) throw Error('revision exhausted');
    const at=source.items.findIndex(x=>x.id===id);
    if(at<0) throw Error('item not found');
    source.items.splice(at,1);source.revision++;
    return source;
  }
  function migrateLegacy(zone,bounds,scene){
    return validateLayout({...emptyLayout(scene),items:[{id:'legacy',name:zone.name,type:'zone',x1:zone.x1,y1:zone.y1,x2:zone.x2,y2:zone.y2}]},bounds,scene);
  }
  function exampleFlow(scene,bounds){
    validateLayout(emptyLayout(scene),bounds,scene);
    const [left,top,right,bottom]=bounds,height=bottom-top,split=top+height*6/13,gap=height*.4/13;
    const items=[{id:'example_flow_south',name:'\u793a\u4f8b\u5357\u533a',type:'zone',x1:left,y1:top,x2:right,y2:split},{id:'example_flow_north',name:'\u793a\u4f8b\u5317\u533a',type:'zone',x1:left,y1:split+gap,x2:right,y2:bottom}];
    return validateLayout({...emptyLayout(scene),items},bounds,scene);
  }
  function exampleGrid(scene,bounds){
    validateLayout(emptyLayout(scene),bounds,scene);
    const [left,top,right,bottom]=bounds,mx=left/2+right/2,my=top/2+bottom/2;
    const rectangles=[[left,top,mx,my],[mx,top,right,my],[left,my,mx,bottom],[mx,my,right,bottom]];
    const items=rectangles.map(([x1,y1,x2,y2],index)=>({id:'example_'+(index+1),name:'\u793a\u4f8b\u533a '+(index+1),type:'zone',x1,y1,x2,y2}));
    return validateLayout({...emptyLayout(scene),items},bounds,scene);
  }
  return {rectangleFromCanvas,emptyLayout,validateLayout,saveItem,removeItem,migrateLegacy,exampleFlow,exampleGrid};
});
