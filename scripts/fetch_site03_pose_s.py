"""Retrieve optional YOLO11s-pose weights for a research comparison."""
from pathlib import Path
import os,subprocess,sys,time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.artifact_cache import sha256,adopt_verified_part
EXPECTED='1060bda4a27012060eca246f9b2adeea22eabb045a1e58f8d229be29b7ebc2ba';SIZE=20373161

def valid(path):return path.is_file() and path.stat().st_size==SIZE and sha256(path)==EXPECTED

def main():
 out=root/'data/models';out.mkdir(parents=True,exist_ok=True);dest=out/'yolo11s-pose.pt';part=out/'yolo11s-pose.pt.download'
 if valid(dest):print('optional pose model verified');return
 if dest.exists():raise RuntimeError('existing model does not match pinned hash; preserve and inspect it')
 if part.exists() and part.stat().st_size>=SIZE and not valid(part):os.replace(part,out/('yolo11s-pose.invalid.'+str(time.time_ns())))
 if adopt_verified_part(part,dest,valid):print('optional pose model verified');return
 for host in ('huggingface.co','hf-mirror.com'):
  url=f'https://{host}/Ultralytics/YOLO11/resolve/main/yolo11s-pose.pt'
  subprocess.run(['curl','-fsSL','--continue-at','-','--retry','3','--retry-all-errors','--retry-delay','2','--connect-timeout','15','--max-time','600','--output',str(part),url])
  if adopt_verified_part(part,dest,valid):print('optional pose model downloaded and verified');return
  if part.exists() and part.stat().st_size>=SIZE:os.replace(part,out/('yolo11s-pose.invalid.'+str(time.time_ns())))
 raise RuntimeError('optional model retrieval incomplete; retry to resume')
if __name__=='__main__':main()
