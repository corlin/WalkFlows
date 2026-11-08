"""Fetch a pinned, separately recorded site03 reference clip for evaluation."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from fetch_site03_sample import valid
from walkflows.artifact_cache import adopt_verified_part
REV='6cf0e1066653f7efe1d0aae5c49860b19ef9a6e5';OUT=ROOT/'data/raw/multiview/007_site03_sparse_tracks'
FILES={
 'C0001020_v1.mp4':('sha256','3ce02f470a7e4cf8d4d73ed75cbdd7b66775bd775bf866ea9c23ce2e100dc3fa',12601809),
 'C0001025_v1.mp4':('sha256','ce5d35e27598e0fa8ea3750d3dc675316c3a5c0d4322cf41de5d982639f2f7df',9332140),
 'C0001029_v2.mp4':('sha256','8a09eb5260e537a5d3a1bebdb7b47b3fbb7cbfa105578e901ea7b51227b78f68',12517749),
 'C0001053_v5.mp4':('sha256','5df5daa8b3991752396d0c26ff2f44df9fd97ed212c1a48fd1ab0b3cb850b4b6',11897615),
 'C0001055_v4.mp4':('sha256','8647aa78461c1abcaf28dfe8b046fc7fd94730d5cec1f273e304665fb8691d28',10095159),
 'C0001056_v2.mp4':('sha256','f761eba90c9a470618a85032d0245a9b883609b882a35e3c1f2b4c42d667e048',11617175),
 'ground-truth.json':('git','f70b1030080404be1f7872dd0d1c3a841e118981',99710),
 'manifest.json':('git','0c1350a42c4f5a568eac563b6956ceae77afd03e',1394),
}
def fetch(item):
 name,meta=item;dest=OUT/name;part=OUT/(name+'.download')
 if valid(dest,meta):return name+' verified existing'
 if adopt_verified_part(part,dest,lambda p:valid(p,meta)):return name+' resumed and verified'
 if part.exists() and part.stat().st_size>=meta[2]:os.replace(part,OUT/(name+'.invalid.'+str(time.time_ns())))
 for host in ('huggingface.co','hf-mirror.com'):
  url=f'https://{host}/datasets/prcvlabs/multiview-retail-tracking/resolve/{REV}/testcases/007_site03_sparse_tracks/{name}'
  subprocess.run(['curl','-fsSL','--http1.1','--continue-at','-','--retry','4','--retry-all-errors','--retry-delay','2','--connect-timeout','15','--max-time','90','--output',str(part),url])
  if adopt_verified_part(part,dest,lambda p:valid(p,meta)):return name+' downloaded and verified'
  if part.exists() and part.stat().st_size>=meta[2]:os.replace(part,OUT/(name+'.invalid.'+str(time.time_ns())))
 raise RuntimeError('download or checksum failed: '+name)
def main():
 OUT.mkdir(parents=True,exist_ok=True);failures=[]
 with ThreadPoolExecutor(max_workers=3) as pool:
  for future in as_completed([pool.submit(fetch,item) for item in FILES.items()]):
   try:print(future.result(),flush=True)
   except Exception as exc:failures.append(str(exc));print(str(exc),flush=True)
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
