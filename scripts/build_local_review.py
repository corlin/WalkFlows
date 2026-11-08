"""Build a local reference/quality review bundle; no identity fusion."""
from pathlib import Path
import collections
import csv
import hashlib
import json
import shutil
import sys
import math
import cv2
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from walkflows.image_heatmap import heatmap

r=Path(__file__).resolve().parents[1]
out=r/"data/processed/local-review"
cameras={"C0001001_v10":"9926ccdd05358cab83c292d9a62f2196961de9439e97857c592a75d2993d5276","C0001011_v10":"1d9b0ff0cbf92d9d107cfb7b197fe393fea5937f1245e5bc99b852e7137c694d"}
with (r/"data/processed/site02-reference-floor/reference_floor.csv").open() as f:reference=list(csv.DictReader(f))
with (r/"data/processed/site02-coverage/frame_coverage.csv").open() as f:quality=list(csv.DictReader(f))
tracks={}
for cam in cameras:
 with (r/"data/processed/site02-gpu-conf010"/(cam+"_observations.csv")).open() as f:tracks[cam]=list(csv.DictReader(f))
quality_observations=[json.loads(line) for line in (r/"data/processed/site02-quality/observations.jsonl").read_text().splitlines()]
scene=json.loads((r/"data/upstream-research/site02_scene01_v1.json").read_text())
if [int(x["clip_frame"]) for x in reference]!=list(range(218)):raise ValueError("Invalid reference frame coverage")
frame_quality={(x["camera"],int(x["frame"])):x for x in quality}
if len(quality)!=436 or len(frame_quality)!=436 or set(frame_quality)!={(cam,frame) for cam in cameras for frame in range(218)}:raise ValueError("Invalid quality frame coverage")
quality_keys={(x["camera"],x["frame"],x["local_id"]) for x in quality_observations}
track_keys={(cam,int(x["frame"]),int(x["local_id"])) for cam,rows in tracks.items() for x in rows}
if len(quality_observations)!=len(quality_keys) or sum(map(len,tracks.values()))!=len(track_keys) or quality_keys!=track_keys:raise ValueError("Track and observation quality keys do not match")
counts=collections.Counter((cam,int(x["frame"])) for cam,rows in tracks.items() for x in rows)
if any(int(row["all_observations"])!=counts[key] for key,row in frame_quality.items()):raise ValueError("Frame observation count mismatch")
for cam,digest in cameras.items():
 src=r/"data/raw/multiview/002_site02_gaze"/(cam+".mp4")
 if hashlib.sha256(src.read_bytes()).hexdigest()!=digest:raise ValueError("Video checksum mismatch: "+cam)
html=r/"walkflows/local_review.html";zones=r/"walkflows/local_zones.js";layout_js=r/"walkflows/layout.js";track_js=r/"walkflows/track_events.js"
if not html.is_file() or not zones.is_file() or not layout_js.is_file() or not track_js.is_file():raise FileNotFoundError("Missing review source")
out.mkdir(parents=True,exist_ok=True)
for cam in cameras:
 src=r/"data/raw/multiview/002_site02_gaze"/(cam+".mp4");dest=out/(cam+".mp4")
 if not dest.is_file() or hashlib.sha256(dest.read_bytes()).hexdigest()!=cameras[cam]:
  temp=out/(cam+".mp4.tmp");shutil.copyfile(src,temp);temp.replace(dest)
status_by_key={(x['camera'],x['frame'],x['local_id']):x['status'] for x in quality_observations}
heatmaps={}
for cam, observations in tracks.items():
 image_points=[]
 for row in observations:
  frame, ident=int(row['frame']),int(row['local_id'])
  x=(float(row['left'])+float(row['right']))/2
  bottom=float(row['bottom'])
  if not 0 <= bottom <= 672: raise ValueError('box bottom outside image')
  y=min(bottom,math.nextafter(672.0,0.0))
  image_points.append({'frame':frame,'local_id':ident,'x':x,'y':y,'status':status_by_key[(cam,frame,ident)]})
 heatmaps[cam]={'qualified':heatmap(image_points,width=896,height=672,columns=16,rows=12,fps=15), 'all':heatmap(image_points,width=896,height=672,columns=16,rows=12,fps=15,include_excluded=True)}
 if heatmaps[cam]['all']['selected_observations'] != len(observations):raise ValueError('heatmap observation count mismatch')
for cam in cameras:
 capture=cv2.VideoCapture(str(out/(cam+'.mp4')))
 try:
  ok,frame=capture.read()
  if not ok or frame.shape[:2] != (672,1792):raise ValueError('unexpected video frame shape: '+cam)
  if not cv2.imwrite(str(out/(cam+'_background.jpg')),frame[:,:896]):raise ValueError('unable to write camera background')
 finally:
  capture.release()
data={"heatmaps":heatmaps,"reference":reference,"quality":quality,"quality_observations":quality_observations,"tracks":tracks,"bounds":scene["hist-aabb"],"entrance":scene["entrance-zone"],"scope":"Reference path and per-camera output only; cross-camera identity and ground accuracy unvalidated."}
temp=out/"data.json.tmp";temp.write_text(json.dumps(data));temp.replace(out/"data.json")
shutil.copyfile(html,out/"index.html");shutil.copyfile(zones,out/"local_zones.js");shutil.copyfile(layout_js,out/"layout.js");shutil.copyfile(track_js,out/"track_events.js")
print("built",out)
