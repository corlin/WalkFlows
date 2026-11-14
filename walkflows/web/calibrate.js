"use strict";
const $ = id => document.getElementById(id);
let cameras = [], current = null, pending = null, rectangle = null, coverage = null, sourceHashes = new Map();
const byCamera = new Map(), drafts = new Map(), coverageDrafts = new Map();
let storageKey = null, groundSuggestions = null;
const cornerNames=["原点","沿宽度方向的角","对角","剩余的角"];
function saveDraft() {
  if (!storageKey) return;
  if (current) {drafts.set(current.id,rectangle);coverageDrafts.set(current.id,coverage);}
  try {
    sessionStorage.setItem(storageKey,JSON.stringify({
      cameras:Array.from(byCamera.entries()),drafts:Array.from(drafts.entries()),coverageDrafts:Array.from(coverageDrafts.entries())
    }));
  } catch (_) { $("storage-status").textContent="浏览器无法保存草稿，请及时下载对应点。"; }
}
function validPoint(p) {
  return Array.isArray(p) && p.length===2 && p.every(Number.isFinite);
}
function restoreDraft(project) {
  storageKey="walkflows-calibration-v1:"+JSON.stringify([project.name,project.cameras.map(c=>[c.id,c.video_revision,c.width,c.height])]);
  try {
    const saved=JSON.parse(sessionStorage.getItem(storageKey)||"null");
    const ids=new Set(project.cameras.map(c=>c.id));
    if (!saved) return;
    for(const [id,points] of saved.cameras||[]) {
      if(ids.has(id)&&Array.isArray(points.image_points)&&Array.isArray(points.plane_points)&&
         points.image_points.length===points.plane_points.length&&points.image_points.every(validPoint)&&points.plane_points.every(validPoint))
        byCamera.set(id,points);
    }
    for(const [id,draft] of saved.drafts||[]) {
      if(ids.has(id)&&draft&&Array.isArray(draft.points)&&draft.points.length<4&&draft.points.every(validPoint)&&
         Number.isFinite(draft.width)&&draft.width>0&&Number.isFinite(draft.height)&&draft.height>0) drafts.set(id,draft);
    }
    for(const [id,points] of saved.coverageDrafts||[]) {
      if(ids.has(id)&&Array.isArray(points)&&points.every(validPoint)) coverageDrafts.set(id,points);
    }
    if(byCamera.size||drafts.size||coverageDrafts.size) $("storage-status").textContent="已恢复本标签页的草稿；请检查后下载文件。";
  } catch (_) { $("storage-status").textContent="草稿无法恢复，请重新选点。"; }
}
function updateRectangleStatus() {
  $("rectangle-undo").disabled=!rectangle || !rectangle.points.length;
  $("rectangle-cancel").disabled=!rectangle;
  if(rectangle) $("rectangle-status").textContent="已选 "+rectangle.points.length+" / 4：请选择"+cornerNames[rectangle.points.length]+"。";
}
function data() { return byCamera.get(current.id); }
function paint() {
  if (!current) return;
  const canvas = $("click-image"), ctx = canvas.getContext("2d"), w=canvas.clientWidth, h=canvas.clientHeight;
  if (!w || !h) return;
  canvas.width=w*devicePixelRatio; canvas.height=h*devicePixelRatio; ctx.scale(devicePixelRatio,devicePixelRatio);
  const view=viewRect(current.width,current.height,$("view-side").value);
  const scale=Math.min(w/view.width,h/view.height), ox=(w-view.width*scale)/2-view.x*scale, oy=(h-view.height*scale)/2-view.y*scale;
  const outline=coverage || data().coverage_polygon || [];
  if(outline.length>1){ctx.beginPath();outline.forEach((p,i)=>{const x=ox+p[0]*scale,y=oy+p[1]*scale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});
    if(!coverage)ctx.closePath();ctx.strokeStyle="#49aaff";ctx.lineWidth=2;ctx.stroke();
    outline.forEach(p=>{ctx.beginPath();ctx.arc(ox+p[0]*scale,oy+p[1]*scale,4,0,Math.PI*2);ctx.fillStyle="#49aaff";ctx.fill();});}
  const corners=rectangle ? rectangle.points : [];
  if(corners.length>1){
    ctx.beginPath();corners.forEach((p,i)=>{const x=ox+p[0]*scale,y=oy+p[1]*scale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});
    ctx.strokeStyle="#ffbf40";ctx.lineWidth=2;ctx.stroke();
  }
  if(groundSuggestions && groundSuggestions.target===current.id && $("match-details").open){
    groundSuggestions.matches.forEach((pair,i)=>{
      const x=ox+pair.target[0]*scale,y=oy+pair.target[1]*scale;
      ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.fillStyle="#c34276";ctx.fill();
      ctx.fillStyle="#fff";ctx.font="bold 12px system-ui";ctx.fillText(String(i+1),x+10,y-7);
    });
  }
  [...data().image_points,...corners,...(pending ? [pending] : [])].forEach((point,i) => {
    const x=ox+point[0]*scale,y=oy+point[1]*scale;
    ctx.beginPath();ctx.arc(x,y,6,0,Math.PI*2);ctx.fillStyle=i<data().image_points.length?"#55e2a7":"#ffbf40";ctx.fill();
    ctx.fillStyle="#fff";ctx.font="bold 14px system-ui";ctx.fillText(String(i+1),x+8,y-5);
  });
}
function render() {
  const list=$("points");list.replaceChildren();
  data().image_points.forEach((p,i)=>{
    const li=document.createElement("li"), world=data().plane_points[i];
    const text=document.createElement("span");
    text.textContent="图像 ("+p.map(v=>v.toFixed(1)).join(", ")+") → 平面 ("+world.join(", ")+")";
    const remove=document.createElement("button");remove.type="button";remove.textContent="删除";
    remove.setAttribute("aria-label","删除第 "+(i+1)+" 个对应点");
    remove.onclick=()=>{data().image_points.splice(i,1);data().plane_points.splice(i,1);saveDraft();render();};
    li.append(text,remove);list.append(li);
  });
  $("download").disabled=data().image_points.length<4 || Boolean(coverage) || Boolean(rectangle);
  const counts=cameras.map(c=>({camera:c,points:byCamera.get(c.id)}));
  const complete=counts.filter(x=>x.points && x.points.image_points.length>=4);
  $("all-status").textContent="已完成 "+complete.length+" / "+cameras.length+" 路对应点；共同坐标系和实际有效地面仍需核验。";
  const listAll=$("all-cameras");listAll.replaceChildren();
  counts.forEach(({camera,points})=>{const li=document.createElement("li");
    const roi=camera.analysis_roi;
    const outside=roi && points ? points.image_points.filter(p=>p[0]<roi[0]||p[0]>=roi[0]+roi[2]||p[1]<roi[1]||p[1]>=roi[1]+roi[3]).length : 0;
    li.textContent=camera.id+"："+(points ? points.image_points.length:0)+" 个对应点 · "+(points&&points.coverage_polygon?"已画区域":"未画区域")+(outside?" · "+outside+" 点在分析范围外，请核对":"");listAll.append(li);});
  const unfinished=Boolean(coverage)||Boolean(rectangle)||Array.from(drafts.values()).some(Boolean)||Array.from(coverageDrafts.values()).some(Boolean);
  const sourceMissing=counts.some(x=>!sourceHashes.get(x.camera.id));
  $("download-all").disabled=complete.length!==cameras.length || sourceMissing || unfinished;
  if(sourceMissing) $("all-status").textContent+=" 缺少原视频来源信息，不能整组导出。";
  else if(unfinished) $("all-status").textContent+=" 请先完成或取消正在绘制的区域。";
  $("coverage-start").disabled=Boolean(rectangle) || Boolean(coverage);
  $("coverage-undo").disabled=!coverage || !coverage.length;
  $("coverage-finish").disabled=!coverage || coverage.length<3;
  $("coverage-cancel").disabled=!coverage;
  if(coverage) $("coverage-status").textContent="正在绘制：已选 "+coverage.length+" 个顶点，按地面边界顺序继续。";
  else $("coverage-status").textContent=data().coverage_polygon?"已绘制 "+data().coverage_polygon.length+" 个顶点；请核验地面范围。":"尚未绘制地面区域。";
  updateView();
}
function updateView() {
  if(!current)return;
  const side=$("view-side").value, view=viewRect(current.width,current.height,side);
  const stage=$("click-image").parentElement, video=$("video");
  stage.style.aspectRatio=view.width+" / "+view.height;
  video.style.width=(100*current.width/view.width)+"%";
  video.style.height="100%";
  video.style.left=(-100*view.x/view.width)+"%";
  video.style.objectFit="fill";
  const roi=current.analysis_roi;
  $("view-warning").textContent=roi ? "原视频分析范围："+roi.join(", ")+"（左上 X、Y、宽、高）；切换显示不改变处理范围。" :
    "仅调整显示范围，选点仍记录原视频坐标；请确认所选画面与分析区域一致。";
  const chosen=[...data().image_points,...(data().coverage_polygon||[])];
  const hidden=chosen.filter(p=>p[0]<view.x||p[0]>=view.x+view.width||p[1]<view.y||p[1]>=view.y+view.height).length;
  if(roi && (view.x>=roi[0]+roi[2] || view.x+view.width<=roi[0]))
    $("view-warning").textContent+=" 当前画面不在分析范围内，请确认标定与实际处理使用同一视角。";
  if(hidden) $("view-warning").textContent+=" 当前有 "+hidden+" 个已保存顶点在显示范围外，请切回完整画面检查。";
  paint();
}
$("view-side").onchange=updateView;
function choose() {
  if(current) saveDraft();
  if(typeof clearGroundSuggestions==="function")clearGroundSuggestions();
  current=cameras.find(c=>c.id===$("camera").value);
  if (!current) return;
  if (!byCamera.has(current.id)) byCamera.set(current.id,{image_points:[],plane_points:[]});
  $("source-warning").textContent=current.video_source==="transcoded_preview"?"当前使用转码预览副本；逐帧时间戳尚未校验。":"当前使用原视频。";
  if(current.normalized_analysis_input) $("source-warning").textContent+=" 分析输入经过恒帧率重采样，需重新核对时间。";
  rectangle=drafts.get(current.id)||null;coverage=coverageDrafts.get(current.id)||null;
  $("rectangle-status").textContent="请先确认地面矩形和实际尺寸。";
  if(rectangle){$("rectangle-width").value=rectangle.width;$("rectangle-height").value=rectangle.height;}
  updateRectangleStatus();pending=null;$("image-point").textContent="在画面中选择一个地面点。";$("feedback").textContent="";
  $("video-error").textContent="";$("time").value=0;$("time-label").value="0.00 秒";
  $("video").src="/video/"+encodeURIComponent(current.id)+"?v="+encodeURIComponent(current.video_revision);
  const roi=current.analysis_roi;
  $("view-side").value=roi && roi[0]===0 && roi[1]===0 && roi[2]===Math.floor(current.width/2) && roi[3]===current.height?"left":"full";
  updateView();render();
}
$("click-image").addEventListener("click", event => {
  if (!current || !$("video").videoWidth) return;
  const rect=event.currentTarget.getBoundingClientRect();
  const view=viewRect(current.width,current.height,$("view-side").value);
  const selected=canvasToImage([event.clientX-rect.left,event.clientY-rect.top],view,rect.width,rect.height);
  if(!selected){$("feedback").textContent="请选择视频画面内的点。";return;}
  const [x,y]=selected;
  if(coverage){coverage.push([x,y]);saveDraft();render();return;}
  if (rectangle) {
    rectangle.points.push([x,y]);
    if (rectangle.points.length === 4) {
      try {
        const result=rectanglePoints(rectangle.points, rectangle.width, rectangle.height);
        if(data().coverage_polygon) result.coverage_polygon=data().coverage_polygon;
        byCamera.set(current.id,result);rectangle=null;updateRectangleStatus();saveDraft();
        $("rectangle-status").textContent="已生成四组对应点。请检查角点和尺寸，再下载；建议另选独立检查点。";
        render();return;
      } catch (error) {
        rectangle.points.pop();updateRectangleStatus();saveDraft();
        $("rectangle-status").textContent=error.message+" 已撤销最后一个角，请重新选择。";
      }
    } else {updateRectangleStatus();saveDraft();}
    paint();return;
  }
  pending=[x,y];$("image-point").textContent="已选图像点："+x.toFixed(1)+", "+y.toFixed(1);
  $("feedback").textContent="";paint();
});
$("coverage-start").onclick=()=>{if(!current || rectangle)return;
  if(typeof clearGroundSuggestions==="function")clearGroundSuggestions();
  coverage=[];pending=null;saveDraft();render();};
$("coverage-undo").onclick=()=>{if(!coverage)return;coverage.pop();saveDraft();render();};
$("coverage-cancel").onclick=()=>{coverage=null;saveDraft();render();};
$("coverage-finish").onclick=()=>{if(!coverage || coverage.length<3)return;
  data().coverage_polygon=coverage.map(p=>p.slice());coverage=null;saveDraft();render();
  $("coverage-status").textContent="区域草稿已保存；要映射到共同平面还需设置对应点。";};
$("download-all").onclick=()=>{
  const entries=cameras.map(c=>({id:c.id,source_sha256:sourceHashes.get(c.id),width:c.width,height:c.height,...byCamera.get(c.id)}));
  const payload={schema_version:1,cameras:entries};
  const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}));
  const link=document.createElement("a");link.href=url;link.download="walkflows-all-camera-calibration.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$("rectangle-start").onclick=()=>{
  if (!current) return;
  if (coverage) {$("rectangle-status").textContent="请先完成或取消区域绘制。";return;}
  if (rectangle && rectangle.points.length) {
    $("rectangle-status").textContent="当前正在选点，可撤销上一个角或取消后重新开始。";return;
  }
  if (data().image_points.length) {
    $("rectangle-status").textContent="当前相机已有对应点，请先撤销已有点，避免覆盖。";return;
  }
  const w=Number($("rectangle-width").value),h=Number($("rectangle-height").value);
  if (!$("rectangle-width").value.trim() || !$("rectangle-height").value.trim() ||
      !Number.isFinite(w) || !Number.isFinite(h) || w<=0 || h<=0) {
    $("rectangle-status").textContent="请输入正的实际宽度和高度。";return;
  }
  pending=null;rectangle={width:w,height:h,points:[]};updateRectangleStatus();saveDraft();
  render();
};
$("rectangle-undo").onclick=()=>{if(!rectangle)return;rectangle.points.pop();updateRectangleStatus();saveDraft();paint();};
$("rectangle-cancel").onclick=()=>{rectangle=null;updateRectangleStatus();saveDraft();
  $("rectangle-status").textContent="已取消选点。";render();};
$("add").onclick=()=>{
  const x=$("world-x").value,y=$("world-y").value;
  if (!pending || x.trim()==="" || y.trim()==="" || !Number.isFinite(Number(x)) || !Number.isFinite(Number(y))) {
    $("feedback").textContent="请先选择图像点并填写有效的 X、Y 坐标。";return;
  }
  data().image_points.push(pending);data().plane_points.push([Number(x),Number(y)]);saveDraft();
  pending=null;$("world-x").value="";$("world-y").value="";
  $("image-point").textContent="在画面中选择下一个地面点。";$("feedback").textContent="已添加。";render();
};
$("undo").onclick=()=>{data().image_points.pop();data().plane_points.pop();saveDraft();render();};
$("download").onclick=()=>{
  const blob=new Blob([JSON.stringify(data(),null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob), link=document.createElement("a");link.href=url;link.download=current.id+"-points.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$("time").oninput=()=>{if(typeof clearGroundSuggestions==="function")clearGroundSuggestions();const t=Number($("time").value);$("video").currentTime=t;$("time-label").value=t.toFixed(2)+" 秒";};
$("video").onloadedmetadata=()=>{$("time").max=Number.isFinite($("video").duration)?$("video").duration:0;paint();};
$("video").onerror=()=>{$("video-error").textContent="视频无法播放：请检查浏览器支持的格式和编码。";};
window.addEventListener("resize",paint);
fetch("/manifest.json").then(r=>{if(!r.ok)throw Error();return r.json();}).then(project=>{
  if(project.review_available){$("review-link").hidden=false;$("review-warning").hidden=false;}
  cameras=project.cameras;
  const sourceInfo=new Map((project.provenance?.source_videos||[]).map(c=>[c.id,c]));
  cameras.forEach(c=>{c.analysis_roi=c.analysis_roi||sourceInfo.get(c.id)?.analysis_roi||null;});
  const sources=new Map((project.provenance?.source_videos||[]).map(c=>[c.id,c.sha256]));
  sourceHashes=new Map(cameras.map(c=>[c.id,sources.get(c.id)||(c.video_source==="original"?c.video_revision:null)]));
  restoreDraft(project);const select=$("camera");
  for(const c of cameras){const option=document.createElement("option");option.value=c.id;option.textContent=c.id;select.append(option);}
  if(!cameras.length)throw Error();
  select.disabled=false;$("rectangle-start").disabled=false;$("time").disabled=false;$("add").disabled=false;$("undo").disabled=false;
  select.onchange=choose;choose();
  if(typeof setupGroundMatching==="function")setupGroundMatching();
}).catch(()=>{$("video-error").textContent="无法读取项目视频信息。";});
