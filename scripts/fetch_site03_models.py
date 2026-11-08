"""Fetch only the two pinned pretrained model files; never train or create an environment."""
from pathlib import Path
import os,subprocess,time
root=Path(__file__).resolve().parents[1]
import sys;sys.path.insert(0,str(root))
from walkflows.artifact_cache import sha256,adopt_verified_part
MODELS={'yolo11n.pt':'0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1','yolo11n-pose.pt':'869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0'}
SIZES={'yolo11n.pt':5613764,'yolo11n-pose.pt':6255593}
def valid(path,name):
 return path.is_file() and path.stat().st_size==SIZES[name] and sha256(path)==MODELS[name]
def main():
 out=root/'data/models';out.mkdir(parents=True,exist_ok=True)
 for name in MODELS:
  dest=out/name
  if valid(dest,name):print(name+' verified existing',flush=True);continue
  part=out/(name+'.download')
  if adopt_verified_part(part,dest,lambda p:valid(p,name)):
   print(name+' resumed and verified',flush=True);continue
  if part.exists() and part.stat().st_size>=SIZES[name] and not valid(part,name):
   quarantine=out/(name+'.invalid.'+str(time.time_ns()));os.replace(part,quarantine)
  success=False
  for host in ('huggingface.co','hf-mirror.com'):
   url=f'https://{host}/Ultralytics/YOLO11/resolve/main/{name}'
   result=subprocess.run(['curl','-fsSL','--http1.1','--continue-at','-','--retry','6','--retry-all-errors','--retry-delay','2','--connect-timeout','15','--max-time','90','--output',str(part),url])
   if adopt_verified_part(part,dest,lambda p:valid(p,name)):success=True;break
   if part.exists() and part.stat().st_size>=SIZES[name]:os.replace(part,out/(name+'.invalid.'+str(time.time_ns())))
  if not success:raise RuntimeError('model download/checksum failed: '+name)
  print(name+' downloaded and verified',flush=True)
if __name__=='__main__':main()
