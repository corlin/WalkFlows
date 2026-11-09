"""Inventory and optionally fetch a complete pinned non-commercial dataset."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time,urllib.parse,urllib.request
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.dataset_manifest import parse_manifest
from walkflows.artifact_cache import adopt_verified_part
REV='6cf0e1066653f7efe1d0aae5c49860b19ef9a6e5';REPO='prcvlabs/multiview-retail-tracking'
DEST=root/'data/raw/multiview/full-dataset';STATE=root/'data/processed/multiview-inventory'
def digest(path,entry):
 if not path.is_file() or path.stat().st_size!=entry['size']:return False
 h=hashlib.sha256() if entry['kind']=='sha256' else hashlib.sha1()
 if entry['kind']=='git':h.update(b'blob '+str(entry['size']).encode()+b'\0')
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()==entry['digest']
def target(entry):
 base=DEST.resolve();path=(DEST/entry['path']).resolve()
 if not path.is_relative_to(base) or path==base:raise ValueError('path escapes dataset root')
 return path
def fetch(entry):
 path=target(entry);path.parent.mkdir(parents=True,exist_ok=True);part=path.with_name(path.name+'.download')
 if digest(path,entry):return 'verified'
 if adopt_verified_part(part,path,lambda p:digest(p,entry)):return 'resumed'
 if part.exists() and part.stat().st_size>=entry['size']:os.replace(part,part.with_name(part.name+'.invalid.'+str(time.time_ns())))
 for attempt in range(3):
  for host in ('huggingface.co','hf-mirror.com'):
   url='https://'+host+'/datasets/'+REPO+'/resolve/'+REV+'/'+urllib.parse.quote(entry['path'],safe='/')
   # A new curl invocation re-reads the current partial length after a timeout.
   subprocess.run(['curl','-fsSL','--http1.1','--continue-at','-','--connect-timeout','15','--max-time','120','--output',str(part),url],stdout=subprocess.DEVNULL)
   if adopt_verified_part(part,path,lambda p:digest(p,entry)):return 'downloaded'
   if part.exists() and part.stat().st_size>=entry['size']:os.replace(part,part.with_name(part.name+'.invalid.'+str(time.time_ns())))
 raise RuntimeError('download or checksum failed: '+entry['path'])
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true',help='download and verify all files');args=parser.parse_args()
 url='https://huggingface.co/api/datasets/'+REPO+'/revision/'+REV+'?blobs=true'
 with urllib.request.urlopen(url,timeout=60) as response:payload=json.load(response)
 entries=parse_manifest(payload,REV);STATE.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
 info={'repository':REPO,'revision':REV,'license':payload.get('cardData',{}).get('license'),'files':len(entries),'bytes':sum(e['size'] for e in entries),'entries':entries}
 tmp=STATE/'manifest.json.tmp';tmp.write_text(json.dumps(info,indent=2));os.replace(tmp,STATE/'manifest.json')
 print('Pinned inventory:',len(entries),'files,',info['bytes'],'bytes; license:',info['license'],flush=True)
 if not args.download:return
 counts={'verified':0,'resumed':0,'downloaded':0,'failed':0};failures=[]
 with ThreadPoolExecutor(max_workers=3) as pool:
  def priority(e):
   path=e['path']
   return (0 if path.startswith('testcases/') and 'site04' in path else 1 if path.startswith('testcases/') and 'site06' in path else 2,path)
  pending=[pool.submit(fetch,e) for e in sorted(entries,key=priority)]
  for done,future in enumerate(as_completed(pending),1):
   try:counts[future.result()]+=1
   except Exception as exc:counts['failed']+=1;failures.append(str(exc));print(str(exc),flush=True)
   if done%25==0 or done==len(entries):print('Progress',done,'/',len(entries),counts,flush=True)
 result={'repository':REPO,'revision':REV,'manifest_sha256':hashlib.sha256((STATE/'manifest.json').read_bytes()).hexdigest(),'counts':counts,'failures':failures,'status':'complete' if not failures else 'incomplete'}
 tmp=STATE/'download-report.json.tmp';tmp.write_text(json.dumps(result,indent=2));os.replace(tmp,STATE/'download-report.json')
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
