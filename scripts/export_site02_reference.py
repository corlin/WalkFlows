"""Export upstream reference floor coordinates, not estimated customer journeys."""
from pathlib import Path
import csv,json,hashlib
import cv2
import numpy as np
r=Path(__file__).resolve().parents[1]
src=r/"data/raw/multiview/002_site02_gaze/ground-truth.json"
g=json.loads(src.read_text())["track_results"]
scene=json.loads((r/"data/upstream-research/site02_scene01_v1.json").read_text())
out=r/"data/processed/site02-reference-floor";out.mkdir(parents=True,exist_ok=True)
left,top,right,bottom=scene["hist-aabb"];origin=g["top-left"];size=g["hist-sz"]
rows=[]
for track in g["tracks"]:
    for point in track["path"]:
        gx,gy,frame=point[:3];x=gx*size+origin[0];y=gy*size+origin[1]
        rows.append([track["id"],frame,frame*g["frame-duration"],gx,gy,x,y,int(0<=gx<g["width"] and 0<=gy<g["height"]),int(left<=x<=right and top<=y<=bottom)])
assert len(rows)==218 and [row[1] for row in rows]==list(range(218))
with (out/"reference_floor.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["reference_id","clip_frame","relative_s","grid_x","grid_y","floor_x","floor_y","in_half_open_grid","in_closed_scene_bounds"]);w.writerows(rows)
canvas=np.full((700,700,3),255,np.uint8)
def pixel(x,y):return (int(60+(x-left)/(right-left)*560),int(60+(y-top)/(bottom-top)*560))
cv2.rectangle(canvas,pixel(left,top),pixel(right,bottom),(0,0,0),2)
entrance=np.array([pixel(x,y) for x,y in scene["entrance-zone"]],dtype=np.int32)
cv2.polylines(canvas,[entrance],True,(180,180,180),1)
pts=np.array([pixel(row[5],row[6]) for row in rows],dtype=np.int32)
cv2.polylines(canvas,[pts],False,(200,80,0),2)
for index in [0,50,100,150,217]:
    pt=tuple(pts[index]);cv2.circle(canvas,pt,4,(0,0,200),-1);cv2.putText(canvas,str(index),pt,cv2.FONT_HERSHEY_SIMPLEX,.45,(0,0,200),1)
cv2.putText(canvas,"UPSTREAM REFERENCE ONLY",(70,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,0,0),2)
cv2.putText(canvas,"x right, y down; no camera projection validated",(50,665),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,0,0),1)
cv2.imwrite(str(out/"reference-floor.png"),canvas)
summary={"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),"rows":len(rows),"outside_half_open_grid":sum(not row[7] for row in rows),"outside_closed_scene_bounds":sum(not row[8] for row in rows),"formula":"world = grid * hist_sz + top_left (no half-cell offset)","provenance":"Reference only; start-frame 4702 retained in original JSON; timestamps here remain clip-relative; no calibrated video alignment proven."}
(out/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
