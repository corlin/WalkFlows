"use strict";
let matchSnapshot=null;
function clearGroundSuggestions(){
  groundSuggestions=null;matchSnapshot=null;
  const list=$("match-list");if(list)list.replaceChildren();
  if($("match-apply"))$("match-apply").disabled=true;
  if($("match-status"))$("match-status").textContent="选择参考相机及两路地面区域后寻找候选。";
  if($("match-reference-canvas"))paintMatchReference();
}
function matchReferenceCamera(){return cameras.find(c=>c.id===$("match-reference").value);}
function paintMatchReference(){
  const camera=matchReferenceCamera(),canvas=$("match-reference-canvas");
  if(!camera || !canvas)return;
  const width=canvas.clientWidth,height=canvas.clientHeight;if(!width||!height)return;
  canvas.width=width*devicePixelRatio;canvas.height=height*devicePixelRatio;
  const ctx=canvas.getContext("2d");ctx.scale(devicePixelRatio,devicePixelRatio);
  const roi=camera.analysis_roi;
  const side=roi && roi[0]===0 && roi[1]===0 && roi[2]===Math.floor(camera.width/2) && roi[3]===camera.height?"left":"full";
  const view=viewRect(camera.width,camera.height,side),video=$("match-video"),stage=canvas.parentElement;
  stage.style.aspectRatio=view.width+" / "+view.height;
  video.style.width=(100*camera.width/view.width)+"%";video.style.height="100%";
  video.style.left=(-100*view.x/view.width)+"%";video.style.objectFit="fill";
  const points=byCamera.get(camera.id)?.coverage_polygon||[];
  if(points.length>1){ctx.beginPath();points.forEach((p,i)=>{const [x,y]=imageToCanvas(p,view,width,height);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});
    ctx.closePath();ctx.strokeStyle="#49aaff";ctx.lineWidth=2;ctx.stroke();}
  if(groundSuggestions && groundSuggestions.reference===camera.id)
    groundSuggestions.matches.forEach((pair,i)=>{const [x,y]=imageToCanvas(pair.reference,view,width,height);
      ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.fillStyle="#c34276";ctx.fill();
      ctx.fillStyle="#fff";ctx.font="bold 12px system-ui";ctx.fillText(String(i+1),x+10,y-7);});
}
function changeMatchReference(){
  clearGroundSuggestions();
  const camera=matchReferenceCamera();if(!camera)return;
  $("match-video").src="/video/"+encodeURIComponent(camera.id)+"?v="+encodeURIComponent(camera.video_revision);
  paintMatchReference();paint();
}
function setupGroundMatching(){
  const select=$("match-reference");select.replaceChildren();
  cameras.forEach(c=>{const option=document.createElement("option");option.value=c.id;option.textContent=c.id;select.append(option);});
  if(current && cameras.length>1)select.value=cameras.find(c=>c.id!==current.id)?.id||current.id;
  select.onchange=changeMatchReference;
  $("match-video").onloadedmetadata=()=>{const t=Number($("match-reference-time").value);if(Number.isFinite(t))$("match-video").currentTime=Math.max(0,Math.min(t,$("match-video").duration||0));paintMatchReference();};
  $("match-reference-time").oninput=()=>{clearGroundSuggestions();const t=Number($("match-reference-time").value);
    if(Number.isFinite(t)&&t>=0&&Number.isFinite($("match-video").duration))$("match-video").currentTime=Math.min(t,Math.max(0,$("match-video").duration-.001));paint();};
  window.addEventListener("resize",paintMatchReference);
  changeMatchReference();
}
function matchingInputs(){
  const ref=matchReferenceCamera(),target=current;
  if(!ref||!target||ref.id===target.id)throw Error("请选择与当前相机不同的参考相机。");
  const referenceData=byCamera.get(ref.id),targetData=byCamera.get(target.id);
  if(!referenceData?.coverage_polygon || !targetData?.coverage_polygon)throw Error("请先分别为参考相机和当前相机完成地面区域圈选。");
  if(coverage||rectangle||coverageDrafts.get(ref.id)||drafts.get(ref.id))throw Error("请先完成或取消两路正在绘制的区域。");
  if(referenceData.image_points.length>0 && referenceData.image_points.length<4)
    throw Error("参考相机已有对应点不足四个，请补全或移除后再寻找。");
  const seconds=Number($("match-reference-time").value);
  if(!Number.isFinite(seconds)||seconds<0||!Number.isFinite(ref.fps)||!Number.isFinite(target.fps))throw Error("参考时间或视频帧率无效。");
  if(!$("video").videoWidth)throw Error("当前视频尚未加载完成。");
  return {reference:ref.id,target:target.id,
    reference_frame:Math.floor(seconds*ref.fps+1e-6),
    target_frame:Math.floor(Number($("video").currentTime)*target.fps+1e-6),
    reference_polygon:referenceData.coverage_polygon,target_polygon:targetData.coverage_polygon,
    reference_points:referenceData.image_points,plane_points:referenceData.plane_points,
    coordinate_system:referenceData.coordinate_system||null};
}
$("match-find").onclick=async()=>{
  let payload;
  try{payload=matchingInputs();}catch(error){$("match-status").textContent=error.message;return;}
  clearGroundSuggestions();$("match-find").disabled=true;$("match-status").textContent="正在比较两路地面画面…";
  const snapshot=JSON.stringify(payload);
  try{
    const response=await fetch("/ground-match",{method:"POST",headers:{"Content-Type":"application/json"},body:snapshot});
    if(!response.ok)throw Error("匹配服务返回 "+response.status+"；请检查视频和地面范围。");
    const result=await response.json();
    if(JSON.stringify(matchingInputs())!==snapshot)throw Error("相机、时间或标注已变化，请重新寻找。");
    if(result.status!=="candidates" || result.matches.length<4){
      $("match-status").textContent="未找到足够的候选（"+result.status+"），请检查地面重叠、纹理或画面时间。";return;
    }
    groundSuggestions=result;matchSnapshot=snapshot;
    const mode=result.plane_mode==="reference_image"?"参考画面像素相对坐标，非米制":"参考相机已有坐标";
    $("match-status").textContent="找到 "+result.matches.length+" 对候选（"+mode+"）。请核对同编号点；只选择同一个固定地面点。";
    const list=$("match-list");list.replaceChildren();
    result.matches.forEach((pair,i)=>{const label=document.createElement("label"),input=document.createElement("input");
      input.type="checkbox";input.value=String(i);input.onchange=()=>{$("match-apply").disabled=list.querySelectorAll("input:checked").length<4;};
      label.append(input,document.createTextNode(" "+(i+1)+" · 参考 ("+pair.reference.map(x=>x.toFixed(0)).join(", ")+") → 当前 ("+pair.target.map(x=>x.toFixed(0)).join(", ")+")"));list.append(label);});
    paint();paintMatchReference();
  }catch(error){$("match-status").textContent=error.message||"匹配失败。";}
  finally{$("match-find").disabled=false;}
};
$("match-apply").onclick=()=>{
  try{
    if(!groundSuggestions||JSON.stringify(matchingInputs())!==matchSnapshot)throw Error("相机、时间或标注已变化，请重新寻找。");
    const indexes=Array.from($("match-list").querySelectorAll("input:checked"),x=>Number(x.value));
    if(indexes.length<4)throw Error("请至少选择四对可信地面候选。");
    if(data().image_points.length && !confirm("当前相机已有对应点。应用候选会替换这些对应点，保留地面区域。继续吗？"))return;
    const chosen=indexes.map(i=>groundSuggestions.matches[i]);
    function hasSpread(points){
      let area=0;
      for(let i=0;i<points.length;i++)for(let j=i+1;j<points.length;j++)for(let k=j+1;k<points.length;k++){
        const [a,b,c]=[points[i],points[j],points[k]];
        area=Math.max(area,Math.abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])));
      }
      return area>1e-6;
    }
    if(!hasSpread(chosen.map(p=>p.target))||!hasSpread(chosen.map(p=>p.plane)))
      throw Error("所选点过于重合或共线，请选择分散的地面点。");
    const targetData=data(),refData=byCamera.get(groundSuggestions.reference);
    if(groundSuggestions.reference_seed && !refData.image_points.length){
      refData.image_points=groundSuggestions.reference_seed.image_points;
      refData.plane_points=groundSuggestions.reference_seed.plane_points;
      refData.coordinate_system={kind:"reference_image_pixels",reference_camera:groundSuggestions.reference};
    }
    targetData.coordinate_system=refData.coordinate_system||{kind:"user_supplied"};
    targetData.image_points=chosen.map(p=>p.target);
    targetData.plane_points=chosen.map(p=>p.plane);
    saveDraft();clearGroundSuggestions();render();
    $("match-status").textContent="已应用 "+chosen.length+" 对候选，请用独立地面点检查，确认后导出整组。";
  }catch(error){$("match-status").textContent=error.message;}
};
