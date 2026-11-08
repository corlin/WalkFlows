"""Audit decoded clip timestamps; never infer camera capture synchronization."""
from pathlib import Path
import cv2,csv,hashlib,json
r=Path(__file__).resolve().parents[1];out=r/"data/processed/site02-timestamp-audit";out.mkdir(parents=True,exist_ok=True)
expected={"C0001001_v10":"9926ccdd05358cab83c292d9a62f2196961de9439e97857c592a75d2993d5276","C0001011_v10":"1d9b0ff0cbf92d9d107cfb7b197fe393fea5937f1245e5bc99b852e7137c694d"}
report={"opencv_version":cv2.__version__,"scope":"Decoded file timestamps only, not proof of actual camera exposure synchronization.","cameras":[]};values={}
for cam,digest in expected.items():
 path=r/"data/raw/multiview/002_site02_gaze"/(cam+".mp4")
 if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError("Video checksum mismatch")
 cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS)
 if not cap.isOpened() or fps<=0:raise ValueError("Cannot open video or invalid fps")
 rows=[]
 while True:
  ok,frame=cap.read()
  if not ok:break
  rows.append({"frame":len(rows),"pos_msec":cap.get(cv2.CAP_PROP_POS_MSEC),"pts_fps_units":cap.get(cv2.CAP_PROP_PTS) if hasattr(cv2,"CAP_PROP_PTS") else None})
 cap.release()
 if len(rows)!=218:raise ValueError("Unexpected decoded frame count")
 if not all(rows[i]["pos_msec"]>rows[i-1]["pos_msec"] for i in range(1,len(rows))):raise ValueError("Non-monotonic timestamps")
 values[cam]=rows
 with (out/(cam+"_timestamps.csv")).open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 report["cameras"].append({"camera":cam,"sha256":digest,"fps":fps,"frames":len(rows),"first_ms":rows[0]["pos_msec"],"last_ms":rows[-1]["pos_msec"],"max_deviation_from_frame_fps_ms":max(abs(x["pos_msec"]-x["frame"]*1000/fps) for x in rows)})
a,b=values.values();report["max_difference_between_decoded_pos_msec"]=max(abs(x["pos_msec"]-y["pos_msec"]) for x,y in zip(a,b))
(out/"summary.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
