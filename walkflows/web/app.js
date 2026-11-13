"use strict";
const $ = id => document.getElementById(id);
let manifest, cards = [], playing = false, anchorClock = 0, anchorTime = 0;
const colors = ["#137b62","#d35428","#596bd7","#b14183","#a37100","#007d9a"];
let floorBounds = null, fullFloorBounds = null;
function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/), names = lines.shift().split(",");
  const frames = new Map();
  for (const line of lines) {
    if (!line) continue;
    const values = line.split(","), row = Object.fromEntries(names.map((n, i) => [n, values[i] || ""]));
    const f = Number(row.frame); if (!Number.isInteger(f)) continue;
    if (!frames.has(f)) frames.set(f, []); frames.get(f).push(row);
  }
  return frames;
}
function draw(card) {
  const {video, canvas, camera, frames} = card, ctx = canvas.getContext("2d");
  const width = canvas.clientWidth, height = canvas.clientHeight;
  if (!width || !height) return;
  canvas.width = width * devicePixelRatio; canvas.height = height * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  const scale = Math.min(width / camera.width, height / camera.height);
  const ox = (width - camera.width * scale) / 2, oy = (height - camera.height * scale) / 2;
  const frame = Math.floor(video.currentTime * camera.fps + 0.00001);
  for (const row of frames.get(frame) || []) {
    const x = ox + Number(row.left) * scale, y = oy + Number(row.top) * scale;
    const w = (Number(row.right) - Number(row.left)) * scale, h = (Number(row.bottom) - Number(row.top)) * scale;
    if (![x,y,w,h].every(Number.isFinite)) continue;
    ctx.strokeStyle = "#55e2a7"; ctx.lineWidth = 2; ctx.strokeRect(x,y,w,h);
    ctx.font = "13px system-ui"; ctx.fillStyle = "#55e2a7"; ctx.fillText(row.local_id ? "本镜 #" + row.local_id : "未分配编号", x + 2, Math.max(14,y - 4));
  }
}
function prepareFloor() {
  let bounds = [Infinity, Infinity, -Infinity, -Infinity], count = 0;
  for (const card of cards) for (const rows of card.frames.values()) for (const row of rows) {
    if (row.world_x === "" || row.world_y === "") continue;
    const x = Number(row.world_x), y = Number(row.world_y);
    if (Number.isFinite(x) && Number.isFinite(y)) {
      bounds = [Math.min(bounds[0],x), Math.min(bounds[1],y), Math.max(bounds[2],x), Math.max(bounds[3],y)];
      count++;
    }
  }
  if (!count) {
    $("floor-note").textContent = "没有可显示的平面坐标：请检查映射、有效区域和检测结果。";
    return;
  }
  floorBounds = bounds; fullFloorBounds = bounds.slice();
  $("floor-note").textContent = "散点为当前时间各镜的脚点投影估计；坐标范围根据本次结果自动缩放，不是实际平面图或去重人数。";
  cards.forEach((card,i) => {
    const item = document.createElement("span"); item.className = "legend-item";
    item.style.setProperty("--color", colors[i % colors.length]); item.textContent = card.camera.id;
    $("legend").append(item);
  });
}
let zones=[], draft=null, floorGeometry=null;
let zoneEvents=[], heatCells=null;
let flowSamples=new Map(), flowCandidates=[];
function recomputeFlows() {
  const raw=$("flow-duration").value, seconds=Number(raw);
  flowCandidates=(raw!=="" && Number.isFinite(seconds) && seconds>0) ? regionFlows(zoneEvents,flowSamples,seconds) : [];
  updateFlows(Number($("seek").value));
}
function updateFlows(time) {
  const raw=$("flow-duration").value, seconds=Number(raw), list=$("flow-list");list.replaceChildren();
  if(raw==="" || !Number.isFinite(seconds) || seconds<=0){
    $("flow-status").textContent="输入最长间隔后计算单镜流转候选；未确认身份，也未跨镜去重。";
    $("flow-export").disabled=true;return;
  }
  const visible=flowCandidates.filter(x=>x.arrival_time<=time);
  $("flow-status").textContent="截至当前时间："+visible.length+" 条单镜流转候选；轨迹连续不代表真实身份。";
  for(const item of visible.slice(-20).reverse()){
    const li=document.createElement("li");
    li.textContent=item.exit_time.toFixed(2)+"–"+item.arrival_time.toFixed(2)+" 秒 · "+item.camera+" #"+item.id+" · "+item.from+" → "+item.to;
    list.append(li);
  }
  $("flow-export").disabled=flowCandidates.length===0;
}

function recomputeEvents() {
  const output=[];flowSamples=new Map();
  for(const card of cards) {
    const points=[];
    for(const [frame, rows] of card.frames) for(const point of uniqueFramePoints(rows)) {
      points.push({...point,frame,time:card.camera.offset_seconds+frame/card.camera.fps});
      const key=JSON.stringify([card.camera.id,point.id]);
      if(!flowSamples.has(key))flowSamples.set(key,new Map());
      flowSamples.get(key).set(frame,1);
    }
    zones.forEach((zone,index)=>{
      for(const event of zoneTransitions(points,zone.points))
        output.push({...event,camera:card.camera.id,zone:zone.name,zone_index:index});
    });
  }
  zoneEvents=output.sort((a,b)=>a.time-b.time);
  recomputeFlows();
}
function updateEvents(time) {
  const visible=zoneEvents.filter(e=>e.time<=time), list=$("event-list");list.replaceChildren();
  const entered=visible.filter(e=>e.type==="enter").length,exited=visible.length-entered;
  $("event-status").textContent="截至当前时间：进入候选 "+entered+"，离开候选 "+exited+"。仅连续帧边界变化，按相机独立计算，未去重。";
  for(const e of visible.slice(-20).reverse()){
    const li=document.createElement("li");
    li.textContent=e.time.toFixed(2)+" 秒 · "+e.camera+" #"+e.id+" · "+(e.type==="enter"?"进入":"离开")+" "+e.zone;
    list.append(li);
  }
  $("event-export").disabled=zoneEvents.length===0;
}
function computeHeat() {
  if(heatCells || !floorBounds)return;
  const points=[];
  for(const card of cards) for(const rows of card.frames.values()) for(const row of rows) {
    if(row.world_x===""||row.world_y==="")continue;
    const x=Number(row.world_x),y=Number(row.world_y);
    if(Number.isFinite(x)&&Number.isFinite(y))points.push({x,y});
  }
  heatCells=heatGrid(points,floorBounds,30);
}

function polygonArea(points) {
  return Math.abs(points.reduce((sum,p,i)=>{const q=points[(i+1)%points.length];return sum+p[0]*q[1]-q[0]*p[1];},0))/2;
}
function updateZones(time) {
  const list=$("zone-list");list.replaceChildren();
  for(const [index,zone] of zones.entries()) {
    let count=0;
    for(const card of cards) {
      const frame=Math.floor((time-card.camera.offset_seconds)*card.camera.fps+0.00001);
      for(const row of card.frames.get(frame)||[]) {
        if(row.world_x===""||row.world_y==="")continue;
        if(pointInPolygon([Number(row.world_x),Number(row.world_y)],zone.points))count++;
      }
    }
    const li=document.createElement("li"), del=document.createElement("button");
    li.append(document.createTextNode(zone.name+"：当前 "+count+" 条投影观察（未去重）"));
    del.textContent="删除";del.onclick=()=>{zones.splice(index,1);recomputeEvents();updateEvents(Number($("seek").value));updateZones(Number($("seek").value));drawFloor(Number($("seek").value));};
    li.append(del);list.append(li);
  }
  $("zone-export").disabled=zones.length===0;
}
function setupZones() {
  const canvas=$("floor-canvas");
  $("zone-start").onclick=()=>{
    if(!floorBounds){$("zone-status").textContent="当前没有可用平面坐标，无法绘制区域。";return;}
    if(!$("zone-name").value.trim()){$("zone-status").textContent="请先输入区域名称。";return;}
    draft=[];$("zone-start").disabled=true;$("zone-finish").disabled=false;$("zone-cancel").disabled=false;
    $("zone-status").textContent="正在绘制：在平面上依次点击顶点，至少三个点。";canvas.style.cursor="crosshair";
  };
  $("zone-cancel").onclick=()=>{draft=null;$("zone-start").disabled=false;$("zone-finish").disabled=true;$("zone-cancel").disabled=true;canvas.style.cursor="";drawFloor(Number($("seek").value));};
  $("zone-finish").onclick=()=>{
    if(!draft || draft.length<3 || polygonArea(draft)<1e-9){$("zone-status").textContent="至少需要三个不共线的顶点。";return;}
    zones.push({name:$("zone-name").value.trim(),points:draft});recomputeEvents();updateEvents(Number($("seek").value));$("zone-name").value="";
    $("zone-cancel").click();$("zone-status").textContent="区域已添加；观察数未按人员去重。";updateZones(Number($("seek").value));drawFloor(Number($("seek").value));
  };
  canvas.onclick=event=>{
    if(!draft || !floorGeometry)return;
    const rect=canvas.getBoundingClientRect(),g=floorGeometry;
    const x=g.xmin+(event.clientX-rect.left-g.ox)/g.scale;
    const y=g.ymin+(g.h-g.oy-(event.clientY-rect.top))/g.scale;
    if(Number.isFinite(x)&&Number.isFinite(y)){draft.push([x,y]);drawFloor(Number($("seek").value));}
  };
  const refreshFloorBounds=bounds=>{
    floorBounds=bounds;heatCells=null;
    if($("show-heat").checked)computeHeat();
    drawFloor(Number($("seek").value));
  };
  $("floor-focus").onclick=()=>{
    const time=Number($("seek").value),points=[];
    for(const card of cards){
      const frame=Math.floor((time-card.camera.offset_seconds)*card.camera.fps+0.00001);
      for(const row of card.frames.get(frame)||[]){
        if(row.world_x===""||row.world_y==="")continue;
        points.push({x:Number(row.world_x),y:Number(row.world_y)});
      }
    }
    const bounds=pointBounds(points);
    if(!bounds){$("floor-view-status").textContent="当前时间没有有效投影，无法聚焦。";return;}
    refreshFloorBounds(bounds);
    $("floor-view-status").textContent="已聚焦所选时刻的投影；范围以外的点可能不可见，画面不会自动跟随。";
  };
  $("floor-all").onclick=()=>{
    if(!fullFloorBounds){$("floor-view-status").textContent="当前没有可用平面坐标。";return;}
    refreshFloorBounds(fullFloorBounds.slice());
    $("floor-view-status").textContent="显示全时段投影范围。";
  };
  $("flow-duration").oninput=recomputeFlows;
  $("flow-export").onclick=()=>{
    const payload={schema_version:1,project:manifest.name,scope:"single-camera continuous track region transitions; not identities or deduplicated",
      max_seconds:Number($("flow-duration").value),provenance:manifest.provenance,zones,flows:flowCandidates};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download="walkflows-region-flows.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  $("show-heat").onchange=()=>{if($("show-heat").checked)computeHeat();drawFloor(Number($("seek").value));};
  $("event-export").onclick=()=>{
    const payload={schema_version:1,project:manifest.name,scope:"camera-local consecutive-frame region boundary candidates; not deduplicated; full recording",provenance:manifest.provenance,zones,events:zoneEvents};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download="walkflows-zone-events.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  $("zone-export").onclick=()=>{
    const payload={schema_version:1,project:manifest.name,scope:"user-defined plane regions; coordinate system not independently validated",zones};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download="walkflows-zones.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  $("zone-import").onchange=async event=>{
    try{
      const file=event.target.files[0];if(!file)return;if(file.size>1000000)throw Error();
      const payload=JSON.parse(await file.text());
      if(payload.schema_version!==1 || !Array.isArray(payload.zones) || payload.zones.length>100)throw Error();
      for(const z of payload.zones) if(typeof z.name!=="string" || !z.name.trim() || z.name.length>60 ||
        !Array.isArray(z.points) || z.points.length<3 || z.points.length>500 ||
        z.points.some(p=>!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite)) || polygonArea(z.points)<1e-9)throw Error();
      zones=payload.zones.map(z=>({name:z.name,points:z.points}));recomputeEvents();updateEvents(Number($("seek").value));updateZones(Number($("seek").value));drawFloor(Number($("seek").value));
      $("zone-status").textContent="区域已导入；请确认坐标系与当前场地一致。";
    }catch(e){$("zone-status").textContent="区域文件无效或格式不受支持。";}
    event.target.value="";
  };
}

function currentPoints(card, time) {
  const frame=Math.floor((time-card.camera.offset_seconds)*card.camera.fps + 0.00001);
  return (card.frames.get(frame)||[]).filter(r=>r.local_id!=="" && r.world_x!=="" && r.world_y!=="")
    .map(r=>({id:r.local_id,x:Number(r.world_x),y:Number(r.world_y)}))
    .filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
}
function updateCandidates(time) {
  const raw=$("candidate-distance").value, threshold=Number(raw), list=$("candidate-list");
  list.replaceChildren();
  if (raw==="" || !Number.isFinite(threshold) || threshold<=0) {
    $("candidate-status").textContent="输入正的距离阈值后显示候选；未设置阈值时不推断关联。";return;
  }
  const unique=[], ambiguous=[];
  for(let i=0;i<cards.length;i++) for(let j=i+1;j<cards.length;j++) {
    const pairs=candidatePairs(currentPoints(cards[i],time),currentPoints(cards[j],time),threshold);
    for(const pair of pairs.unique) unique.push({a:cards[i].camera.id,b:cards[j].camera.id,...pair});
    ambiguous.push(...pairs.ambiguous);
  }
  $("candidate-status").textContent="当前时间，逐相机对的唯一邻近候选 "+unique.length+" 对；存在竞争的候选边 "+ambiguous.length+" 条。均非确认身份。";
  for(const pair of unique.slice(0,20)) {
    const item=document.createElement("li");
    item.textContent=pair.a+" #"+pair.left.id+" ↔ "+pair.b+" #"+pair.right.id+"，距离 "+pair.distance.toFixed(3);
    list.append(item);
  }
  if(unique.length>20){const item=document.createElement("li");item.textContent="仅列出前 20 对。";list.append(item);}
}

function drawFloor(time) {
  const canvas = $("floor-canvas"), ctx = canvas.getContext("2d"), w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w || !h) return;
  canvas.width = w * devicePixelRatio; canvas.height = h * devicePixelRatio; ctx.scale(devicePixelRatio,devicePixelRatio);
  if (!floorBounds) return;
  const [xmin,ymin,xmax,ymax] = floorBounds, dx = Math.max(xmax-xmin,0.1), dy = Math.max(ymax-ymin,0.1);
  const scale = Math.min((w-48)/dx,(h-48)/dy), ox=(w-dx*scale)/2, oy=(h-dy*scale)/2;
  ctx.fillStyle="#64748b"; ctx.font="12px system-ui"; ctx.fillText("场景坐标（未验证）",12,17);
  if($("show-heat").checked && heatCells) {
    const peak=Math.max(...heatCells);
    if(peak) for(let gy=0;gy<30;gy++)for(let gx=0;gx<30;gx++){
      const count=heatCells[gy*30+gx];if(!count)continue;
      ctx.fillStyle="rgba(222,90,25,"+(0.08+0.55*Math.sqrt(count/peak))+")";
      const cellW=dx*scale/30,cellH=dy*scale/30;
      ctx.fillRect(ox+gx*cellW,h-oy-(gy+1)*cellH,cellW+0.5,cellH+0.5);
    }
  }
  floorGeometry={xmin,ymin,scale,ox,oy,h};
  const drawPolygon=(points,closed)=>{
    if(!points.length)return;ctx.beginPath();
    points.forEach((p,i)=>{const x=ox+(p[0]-xmin)*scale,y=h-oy-(p[1]-ymin)*scale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});
    if(closed)ctx.closePath();ctx.strokeStyle="#c57b00";ctx.lineWidth=2;ctx.stroke();
    if(closed){ctx.fillStyle="rgba(255,190,50,.16)";ctx.fill();}
  };
  zones.forEach(z=>drawPolygon(z.points,true));if(draft)drawPolygon(draft,false);
  // Only unique, consecutive local observations ending at the current frame.
  cards.forEach((card,i) => {
    const end=Math.floor((time-card.camera.offset_seconds)*card.camera.fps+0.00001);
    const begin=Math.max(0,end-Math.min(120,Math.ceil(card.camera.fps*3)));
    if(end<0)return;
    const toCanvas=p=>[ox+(p.x-xmin)*scale,h-oy-(p.y-ymin)*scale];
    ctx.strokeStyle=colors[i%colors.length];ctx.fillStyle=colors[i%colors.length];
    ctx.lineWidth=1.5;ctx.globalAlpha=.8;
    for(const path of continuousTrails(card.frames,begin,end).values()) {
      if(path.length<2)continue;
      const points=path.map(toCanvas);
      ctx.beginPath();ctx.moveTo(...points[0]);for(const p of points.slice(1))ctx.lineTo(...p);ctx.stroke();
      // A half-second minimum and screen-space displacement suppress obvious jitter.
      if(path.length-1<Math.ceil(card.camera.fps*.5))continue;
      const first=points[0],last=points[points.length-1],dx=last[0]-first[0],dy=last[1]-first[1];
      if(Math.hypot(dx,dy)<8)continue;
      const angle=Math.atan2(dy,dx),size=9;
      ctx.beginPath();ctx.moveTo(...last);
      ctx.lineTo(last[0]-size*Math.cos(angle-.45),last[1]-size*Math.sin(angle-.45));
      ctx.lineTo(last[0]-size*Math.cos(angle+.45),last[1]-size*Math.sin(angle+.45));
      ctx.closePath();ctx.fill();
    }
    ctx.globalAlpha=1;
  });
  cards.forEach((card,i) => {
    const f = Math.floor((time-card.camera.offset_seconds)*card.camera.fps + 0.00001);
    for (const row of card.frames.get(f) || []) {
      if (row.world_x === "" || row.world_y === "") continue;
      const x=Number(row.world_x), y=Number(row.world_y);
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      ctx.beginPath(); ctx.fillStyle=colors[i % colors.length]; ctx.arc(ox+(x-xmin)*scale,h-oy-(y-ymin)*scale,5,0,Math.PI*2); ctx.fill();
    }
  });
}
function setTime(time, force = false) {
  const start = manifest.timeline.start_seconds, end = manifest.timeline.end_seconds;
  time = Math.max(start, Math.min(end, time));
  $("seek").value = time; $("time").value = time.toFixed(2) + " 秒";
  for (const card of cards) {
    const target = Math.max(0, time - card.camera.offset_seconds);
    if (Number.isFinite(card.video.duration) && (force || Math.abs(card.video.currentTime - target) > 0.20))
      card.video.currentTime = Math.min(target, Math.max(0,card.video.duration - 0.001));
    draw(card);
  }
  drawFloor(time);
  updateCandidates(time);
  updateZones(time);
  updateEvents(time);
  updateFlows(time);
}
function stop() {
  playing = false; $("play").textContent = "播放";
  for (const card of cards) card.video.pause();
}
function tick(now) {
  if (!playing) return;
  const t = anchorTime + (now - anchorClock) / 1000;
  setTime(t);
  if (t >= manifest.timeline.end_seconds) { stop(); return; }
  requestAnimationFrame(tick);
}
async function start() {
  if (playing) { stop(); return; }
  let t = Number($("seek").value);
  if (t >= manifest.timeline.end_seconds - 0.01) t = manifest.timeline.start_seconds;
  setTime(t,true);
  try { await Promise.all(cards.map(c => c.video.play())); }
  catch (e) { stop(); $("error").textContent = "部分视频无法播放，请检查浏览器支持的编码或文件状态。"; return; }
  playing = true; anchorClock = performance.now(); anchorTime = t; $("play").textContent = "暂停";
  requestAnimationFrame(tick);
}
async function init() {
  const response = await fetch("/manifest.json"); if (!response.ok) throw Error("无法读取项目");
  manifest = await response.json(); $("title").textContent = manifest.name;
  $("scope").textContent = "本地处理结果 · 仅显示逐镜观察";
  $("seek").min = manifest.timeline.start_seconds; $("seek").max = manifest.timeline.end_seconds;
  for (const camera of manifest.cameras) {
    const result = await fetch("/observations/" + encodeURIComponent(camera.id) + "?v=" + encodeURIComponent(camera.observations_revision));
    if (!result.ok) throw Error("无法读取观察数据：" + camera.id);
    const frames = parseCsv(await result.text());
    sanitizeCalibration(frames, camera.calibrated);
    const card = document.createElement("article"); card.className = "card";
    const head = document.createElement("header"), name = document.createElement("h2"), meta = document.createElement("span");
    name.textContent = camera.id; meta.className = "meta"; meta.textContent = camera.observations + " 条观察 · 原始编码 " + (camera.codec_fourcc || "未知");
    head.append(name,meta); const stage = document.createElement("div"); stage.className = "stage";
    const video = document.createElement("video"); video.preload = "metadata"; video.muted = true; video.playsInline = true; video.src = "/video/" + encodeURIComponent(camera.id) + "?v=" + encodeURIComponent(camera.video_revision);
    const canvas = document.createElement("canvas"); stage.append(video,canvas);
    const note = document.createElement("p"); note.className = "note";
    note.textContent = camera.calibrated ? "已提供平面映射；精度未验证。" : "未提供平面映射；仅显示单镜结果。";
    note.textContent += camera.video_source === "transcoded_preview" ? " · 使用转码预览副本；叠框基于原视频，逐帧时间戳尚未校验。" : " · 使用分析输入视频。";
    if(camera.normalized_analysis_input) note.textContent += " · 分析输入经过恒帧率重采样，可能复制或丢弃帧。";
    if(camera.frame_count_matches_metadata===false) note.textContent += " · 解码帧数与元数据不一致；共同时间范围按已解码帧数估算，请检查原视频。";
    video.addEventListener("error", () => { note.textContent += " · 视频无法播放：请检查浏览器是否支持该格式和编码。"; });
    video.addEventListener("seeked", () => draw(item)); video.addEventListener("loadedmetadata", () => draw(item));
    card.append(head,stage,note); $("cameras").append(card);
    const item = {camera,video,canvas,frames}; cards.push(item);
  }
  $("play").disabled = $("seek").disabled = $("reset").disabled = false;
  $("play").onclick = start; $("seek").oninput = () => { stop(); setTime(Number($("seek").value),true); };
  $("reset").onclick = () => { stop(); setTime(manifest.timeline.start_seconds,true); };
  prepareFloor();
  setupZones();
  $("candidate-distance").oninput = () => updateCandidates(Number($("seek").value));
  window.addEventListener("resize", () => {cards.forEach(draw); drawFloor(Number($("seek").value));});
  setTime(manifest.timeline.start_seconds,true);
}
init().catch(e => { $("error").textContent = e.message; $("title").textContent = "无法打开项目"; });
