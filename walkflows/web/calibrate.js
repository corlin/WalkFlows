"use strict";
const $ = id => document.getElementById(id);
let cameras = [], current = null, pending = null, rectangle = null;
const byCamera = new Map();
function data() { return byCamera.get(current.id); }
function paint() {
  if (!current) return;
  const canvas = $("click-image"), ctx = canvas.getContext("2d"), w=canvas.clientWidth, h=canvas.clientHeight;
  if (!w || !h) return;
  canvas.width=w*devicePixelRatio; canvas.height=h*devicePixelRatio; ctx.scale(devicePixelRatio,devicePixelRatio);
  const scale=Math.min(w/current.width,h/current.height), ox=(w-current.width*scale)/2, oy=(h-current.height*scale)/2;
  [...data().image_points,...(rectangle ? rectangle.points : []),...(pending ? [pending] : [])].forEach((point,i) => {
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
  rectangle=null;$("rectangle-cancel").disabled=true;$("rectangle-status").textContent="请先确认地面矩形和实际尺寸。";pending=null;$("image-point").textContent="在画面中选择一个地面点。";$("feedback").textContent="";
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
  if (rectangle) {
    rectangle.points.push([x,y]);
    if (rectangle.points.length === 4) {
      try {
        const result=rectanglePoints(rectangle.points, rectangle.width, rectangle.height);
        byCamera.set(current.id,result);rectangle=null;$("rectangle-cancel").disabled=true;
        $("rectangle-status").textContent="已生成四组对应点。请检查角点和尺寸，再下载；建议另选独立检查点。";
        render();return;
      } catch (error) {
        rectangle.points=[];
        $("rectangle-status").textContent=error.message+" 请重新按周边顺序选取。";
      }
    } else $("rectangle-status").textContent="已选 "+rectangle.points.length+" / 4 个角，请继续按周边顺序选择。";
    paint();return;
  }
  pending=[x,y];$("image-point").textContent="已选图像点："+x.toFixed(1)+", "+y.toFixed(1);
  $("feedback").textContent="";paint();
});
$("rectangle-start").onclick=()=>{
  if (!current) return;
  if (data().image_points.length) {
    $("rectangle-status").textContent="当前相机已有对应点，请先撤销已有点，避免覆盖。";return;
  }
  const w=Number($("rectangle-width").value),h=Number($("rectangle-height").value);
  if (!$("rectangle-width").value.trim() || !$("rectangle-height").value.trim() ||
      !Number.isFinite(w) || !Number.isFinite(h) || w<=0 || h<=0) {
    $("rectangle-status").textContent="请输入正的实际宽度和高度。";return;
  }
  pending=null;rectangle={width:w,height:h,points:[]};$("rectangle-cancel").disabled=false;
  $("rectangle-status").textContent="请选择原点，再沿矩形周边依次选择其他三个角。";
  paint();
};
$("rectangle-cancel").onclick=()=>{rectangle=null;$("rectangle-cancel").disabled=true;
  $("rectangle-status").textContent="已取消选点。";paint();};
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
  if(project.review_available){$("review-link").hidden=false;$("review-warning").hidden=false;}
  cameras=project.cameras;const select=$("camera");
  for(const c of cameras){const option=document.createElement("option");option.value=c.id;option.textContent=c.id;select.append(option);}
  if(!cameras.length)throw Error();
  select.disabled=false;$("rectangle-start").disabled=false;$("time").disabled=false;$("add").disabled=false;$("undo").disabled=false;
  select.onchange=choose;choose();
}).catch(()=>{$("video-error").textContent="无法读取项目视频信息。";});
