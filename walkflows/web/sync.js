"use strict";
const $=id=>document.getElementById(id);
let cards=[],start=0,end=0,playing=false,anchor=0,origin=0;
function stop(){playing=false;$("play").textContent="播放";cards.forEach(c=>c.video.pause());}
function updateTime(t,force=false){
  t=Math.max(start,Math.min(end,t));$("seek").value=t;$("clock").value=t.toFixed(2)+" 秒";
  for(const card of cards){
    const local=Math.max(0,t-Number(card.input.value));
    if(Number.isFinite(card.video.duration)&&(force||Math.abs(card.video.currentTime-local)>.2))
      card.video.currentTime=Math.min(local,Math.max(0,card.video.duration-.001));
    card.current.textContent="本视频 "+local.toFixed(2)+" 秒";
  }
}
function calculate(){
  stop();
  const offsets=cards.map(c=>c.input.value.trim()===""?NaN:Number(c.input.value));
  if(offsets.some(v=>!Number.isFinite(v))){
    $("status").textContent="请为每路输入有效的偏移秒数。";$("play").disabled=$("seek").disabled=$("export").disabled=true;return;
  }
  start=Math.max(...offsets);end=Math.min(...cards.map((c,i)=>offsets[i]+c.duration));
  if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start){
    $("status").textContent="当前视频没有共同时间范围，请调整偏移。";$("play").disabled=$("seek").disabled=$("export").disabled=true;return;
  }
  $("status").textContent="共同时间范围："+start.toFixed(2)+"–"+end.toFixed(2)+" 秒（基于视频元数据估算）。";
  $("seek").min=start;$("seek").max=end;$("play").disabled=$("seek").disabled=$("export").disabled=false;
  updateTime(start,true);
}
function tick(now){
  if(!playing)return;const t=origin+(now-anchor)/1000;updateTime(t);
  if(t>=end){stop();return;}requestAnimationFrame(tick);
}
$("play").onclick=async()=>{
  if(playing){stop();return;}
  let t=Number($("seek").value);if(t>=end-.01)t=start;updateTime(t,true);
  const result=await playAvailable(cards);
  const names=result.failed.map(c=>c.id).join("、");
  $("error").textContent=result.failed.length?"无法播放："+names+"；其他可播放视频继续，无法播放的画面不能用于对齐。":"";
  if(!result.playing.length){stop();return;}
  playing=true;origin=t;anchor=performance.now();$("play").textContent="暂停";requestAnimationFrame(tick);
};
$("seek").oninput=()=>{stop();updateTime(Number($("seek").value),true);};
$("export").onclick=()=>{
  const offsets=Object.fromEntries(cards.map(c=>[c.id,Number(c.input.value)]));
  const url=URL.createObjectURL(new Blob([JSON.stringify({offsets},null,2)],{type:"application/json"}));
  const link=document.createElement("a");link.href=url;link.download="walkflows-offsets.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
fetch("/manifest.json").then(r=>{if(!r.ok)throw Error();return r.json();}).then(project=>{
  $("title").textContent=project.name+" · 时间对齐";
  for(const camera of project.cameras){
    const card=document.createElement("article");card.className="card";
    const head=document.createElement("header"),name=document.createElement("h2");name.textContent=camera.id;head.append(name);
    const stage=document.createElement("div");stage.className="stage";
    const video=document.createElement("video");video.preload="metadata";video.muted=true;video.playsInline=true;video.src="/video/"+encodeURIComponent(camera.id)+"?v="+encodeURIComponent(camera.video_revision);stage.append(video);
    const panel=document.createElement("div");panel.className="sync-panel";
    const label=document.createElement("label");label.textContent="首帧偏移（秒）";
    const input=document.createElement("input");input.type="number";input.step="any";input.value=camera.offset_seconds;label.append(input);
    const current=document.createElement("span");current.textContent="本视频 0.00 秒";panel.append(label,current);
    const warning=document.createElement("p");warning.className="note";
    warning.textContent=camera.video_source==="transcoded_preview"?"使用转码预览副本；逐帧时间戳尚未校验，需结合原视频确认时间对齐。":"";
    if(camera.normalized_analysis_input) warning.textContent+=" 分析输入经过恒帧率重采样，需重新核对时间。";
    video.onerror=()=>{warning.textContent="视频无法播放：请检查格式或编码。";};
    input.oninput=calculate;card.append(head,stage,panel,warning);$("cameras").append(card);
    cards.push({id:camera.id,duration:camera.duration_seconds,input,video,current});
  }
  if(!cards.length)throw Error();calculate();
}).catch(()=>{$("error").textContent="无法读取项目视频信息。";});
