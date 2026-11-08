"""Fixed site03 six-view local tracking baseline; does not create global IDs."""
from pathlib import Path
import argparse,csv,hashlib,json,os,time
import cv2,torch
from ultralytics import YOLO, __version__ as ultralytics_version
from ultralytics.utils import ROOT as ULTRALYTICS_ROOT
from fetch_site03_sample import FILES, valid
ROOT=Path(__file__).resolve().parents[1]
EXPERIMENT=ROOT/'data/processed/site03-byte095-experiment'
CONFIG=EXPERIMENT/'byte095.yaml'
CAMERAS=[name[:-4] for name in FILES if name.endswith('.mp4')]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 EXPERIMENT.mkdir(parents=True,exist_ok=True)
 default_config=ULTRALYTICS_ROOT/'cfg/trackers/bytetrack.yaml'
 original=default_config.read_text()
 if 'match_thresh: 0.8 ' not in original: raise ValueError('unexpected baseline tracker config')
 expected=original.replace('match_thresh: 0.8 ','match_thresh: 0.95 ')
 if CONFIG.exists() and CONFIG.read_text()!=expected: raise ValueError('experiment config changed')
 if not CONFIG.exists(): CONFIG.write_text(expected)
 parser=argparse.ArgumentParser();parser.add_argument('--camera',action='append',choices=CAMERAS);parser.add_argument('--conf',type=float,default=.1);parser.add_argument('--imgsz',type=int,default=640);parser.add_argument('--output',type=Path);args=parser.parse_args()
 if not 0<args.conf<1 or args.imgsz<=0:parser.error('invalid inference settings')
 if (args.conf!=.1 or args.imgsz!=640) and args.output is None:parser.error('non-default inference settings require --output')
 weights=ROOT/'data/models/yolo11n.pt';out=args.output or EXPERIMENT;out.mkdir(parents=True,exist_ok=True)
 if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
 selected=args.camera or CAMERAS
 for camera in selected:
  name=camera+'.mp4';video=ROOT/'data/raw/multiview/006_site03_tracks'/name
  if not valid(video,FILES[name]):print(camera+' missing or checksum mismatch',flush=True);continue
  runpath=out/(camera+'_run.json');observations=out/(camera+'_observations.csv');framespath=out/(camera+'_frames.csv')
  contract={'video_sha256':FILES[name][1],'weights_sha256':sha(weights),'conf':args.conf,'imgsz':args.imgsz,'tracker':str(CONFIG),'torch':str(torch.__version__),'ultralytics':ultralytics_version,'opencv':cv2.__version__,'tracker_config_sha256':sha(CONFIG)}
  if runpath.exists() and observations.exists() and framespath.exists():
   old=json.loads(runpath.read_text())
   if old.get('contract')==contract and old.get('observations_sha256')==sha(observations) and old.get('frames_sha256')==sha(framespath):print(camera+' verified existing output',flush=True);continue
  cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS)
  if not cap.isOpened() or abs(fps-15)>1e-3:raise ValueError('invalid video/fps '+camera)
  model=YOLO(str(weights));rows=[];frames=[];n=0;start=time.perf_counter()
  try:
   while True:
    ok,image=cap.read()
    if not ok:break
    if image.shape[:2]!=(672,1792):raise ValueError('invalid dimensions')
    result=model.track(image[:,:896].copy(),persist=True,tracker=str(CONFIG),classes=[0],conf=args.conf,imgsz=args.imgsz,device=0,verbose=False)[0]
    boxes=result.boxes;count=0
    if boxes is not None and boxes.id is not None:
     for box,tid,confidence in zip(boxes.xyxy.cpu().tolist(),boxes.id.cpu().tolist(),boxes.conf.cpu().tolist()):rows.append([n,n/fps,int(tid),confidence,*box]);count+=1
    frames.append([n,n/fps,0 if boxes is None else len(boxes),count]);n+=1
  finally:cap.release()
  torch.cuda.synchronize()
  if n!=400:raise ValueError(f'{camera}: expected 400 decoded frames, got {n}')
  for path,header,data in [(observations,['frame','relative_s','local_id','confidence','left','top','right','bottom'],rows),(framespath,['frame','relative_s','returned_boxes','tracked_boxes'],frames)]:
   tmp=path.with_suffix('.csv.tmp')
   with tmp.open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(header);writer.writerows(data)
   os.replace(tmp,path)
  result={'camera':camera,'contract':contract,'frames':n,'fps':fps,'observations':len(rows),'local_ids':len({x[2] for x in rows}),'elapsed_s':time.perf_counter()-start,'observations_sha256':sha(observations),'frames_sha256':sha(framespath),'scope':'left-eye camera-local detector tracks only; IDs are not people'}
  temp=runpath.with_suffix('.json.tmp');temp.write_text(json.dumps(result,indent=2));os.replace(temp,runpath);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
