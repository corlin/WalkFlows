"use strict";
// Four corners must trace the measured ground rectangle around its perimeter.
function rectanglePoints(points, width, height) {
  if (!Array.isArray(points) || points.length !== 4 ||
      !points.every(p => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite)) ||
      !Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error("请输入正的矩形宽度、高度并选取四个角。");
  }
  const cross = (a,b,c) => (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]);
  const turns = points.map((p,i) => cross(p,points[(i+1)%4],points[(i+2)%4]));
  if (!turns.every(v => v > 1e-6) && !turns.every(v => v < -1e-6)) {
    throw new Error("四个角须按周边顺序选择，不能重合、共线或交叉。");
  }
  return {image_points: points.map(p=>p.slice()),
          plane_points: [[0,0],[width,0],[width,height],[0,height]]};
}
function viewRect(width,height,side) {
  const split=Math.floor(width/2);
  if(side==="left")return {x:0,y:0,width:split,height};
  if(side==="right")return {x:split,y:0,width:width-split,height};
  return {x:0,y:0,width,height};
}
function imageToCanvas(point,view,width,height) {
  const scale=Math.min(width/view.width,height/view.height);
  return [(width-view.width*scale)/2+(point[0]-view.x)*scale,
          (height-view.height*scale)/2+(point[1]-view.y)*scale];
}
function canvasToImage(point,view,width,height) {
  const scale=Math.min(width/view.width,height/view.height);
  const x=(point[0]-(width-view.width*scale)/2)/scale+view.x;
  const y=(point[1]-(height-view.height*scale)/2)/scale+view.y;
  return x>=view.x && x<view.x+view.width && y>=view.y && y<view.y+view.height?[x,y]:null;
}
if (typeof module !== "undefined") module.exports = {rectanglePoints,viewRect,imageToCanvas,canvasToImage};
