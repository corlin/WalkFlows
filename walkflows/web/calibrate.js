"use strict";
const $ = id => document.getElementById(id);
let cameras = [], current = null, pending = null;
const byCamera = new Map();
function data() { return byCamera.get(current.id); }
function paint() {
  if (!current) return;
  const canvas = $("click-image"), ctx = canvas.getContext("2d"), w=canvas.clientWidth, h=canvas.clientHeight;
  if (!w || !h) return;
  canvas.width=w*devicePixelRatio; canvas.height=h*devicePixelRatio; ctx.scale(devicePixelRatio,devicePixelRatio);
  const scale=Math.min(w/current.width,h/current.height), ox=(w-current.width*scale)/2, oy=(h-current.height*scale)/2;
  [...data().image_points,...(pending ? [pending] : [])].forEach((point,i) => {
    const x=ox+point[0]*scale,y=oy+point[1]*scale;
    ctx.beginPath();ctx.arc(x,y,6,0,Math.PI*2);ctx.fillStyle=i<data().image_points.length?"#55e2a7":"#ffbf40";ctx.fill();
    ctx.fillStyle="#fff";ctx.font="bold 14px system-ui";ctx.fillText(String(i+1),x+8,y-5);
  });
}
function render() {
  const list=$("points");list.replaceChildren();
  data().image_points.forEach((p,i)=>{
    const li=document.createElement("li"), world=data().plane_points[i];
    li.textContent="图像 ("+p.map(v=>v.toFixed(1)).join(", ")+") → 平面 ("+world.join(", ")+")";
    list.append(li);
  });
  $("download").disabled=data().image_points.length<4;paint();
}
function choose() {
  current=cameras.find(c=>c.id===$("camera").value);
  if (!current) return;
  if (!byCamera.has(current.id)) byCamera.set(current.id,{image_points:[],plane_points:[]});
  $("source-warning").textContent=current.video_source==="transcoded_preview"?"当前使用转码预览副本；逐帧时间戳尚未校验。":"当前使用原视频。";
  if(current.normalized_analysis_input) $("source-warning").textContent+=" 分析输入经过恒帧率重采样，需重新核对时间。";
  pending=null;$("image-point").textContent="在画面中选择一个地面点。";$("feedback").textContent="";
  $("video-error").textContent="";$("time").value=0;$("time-label").value="0.00 秒";
  $("video").src="/video/"+encodeURIComponent(current.id)+"?v="+encodeURIComponent(current.video_revision);render();
}
$("click-image").addEventListener("click", event => {
  if (!current || !$("video").videoWidth) return;
  const rect=event.currentTarget.getBoundingClientRect();
  const scale=Math.min(rect.width/current.width,rect.height/current.height);
  const x=(event.clientX-rect.left-(rect.width-current.width*scale)/2)/scale;
  const y=(event.clientY-rect.top-(rect.height-current.height*scale)/2)/scale;
  if (x<0 || y<0 || x>=current.width || y>=current.height) { $("feedback").textContent="请选择视频画面内的点。";return; }
  pending=[x,y];$("image-point").textContent="已选图像点："+x.toFixed(1)+", "+y.toFixed(1);
  $("feedback").textContent="";paint();
});
$("add").onclick=()=>{
  const x=$("world-x").value,y=$("world-y").value;
  if (!pending || x.trim()==="" || y.trim()==="" || !Number.isFinite(Number(x)) || !Number.isFinite(Number(y))) {
    $("feedback").textContent="请先选择图像点并填写有效的 X、Y 坐标。";return;
  }
  data().image_points.push(pending);data().plane_points.push([Number(x),Number(y)]);
  pending=null;$("world-x").value="";$("world-y").value="";
  $("image-point").textContent="在画面中选择下一个地面点。";$("feedback").textContent="已添加。";render();
};
$("undo").onclick=()=>{data().image_points.pop();data().plane_points.pop();render();};
$("download").onclick=()=>{
  const blob=new Blob([JSON.stringify(data(),null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob), link=document.createElement("a");link.href=url;link.download=current.id+"-points.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$("time").oninput=()=>{const t=Number($("time").value);$("video").currentTime=t;$("time-label").value=t.toFixed(2)+" 秒";};
$("video").onloadedmetadata=()=>{$("time").max=Number.isFinite($("video").duration)?$("video").duration:0;paint();};
$("video").onerror=()=>{$("video-error").textContent="视频无法播放：请检查浏览器支持的格式和编码。";};
window.addEventListener("resize",paint);
fetch("/manifest.json").then(r=>{if(!r.ok)throw Error();return r.json();}).then(project=>{
  cameras=project.cameras;const select=$("camera");
  for(const c of cameras){const option=document.createElement("option");option.value=c.id;option.textContent=c.id;select.append(option);}
  if(!cameras.length)throw Error();
  select.disabled=false;$("time").disabled=false;$("add").disabled=false;$("undo").disabled=false;
  select.onchange=choose;choose();
}).catch(()=>{$("video-error").textContent="无法读取项目视频信息。";});
