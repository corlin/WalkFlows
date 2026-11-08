"""Fetch the fixed six-view site03 testcase; validate published blob hashes."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import os
import subprocess
import time
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from walkflows.artifact_cache import adopt_verified_part
OUT=ROOT/'data/raw/multiview/006_site03_tracks'
REV='6cf0e1066653f7efe1d0aae5c49860b19ef9a6e5'
FILES={
'C0001020_v1.mp4':('sha256','3dd39a41b536df3f1e2eb46b1f32869ad57a05e594104bfc64b154c8bd7eca2c',9853376),
'C0001025_v1.mp4':('sha256','d772051ec5fa35aa9498f8c29156ad7d206e87911639b5a229875144eb105042',5739572),
'C0001029_v2.mp4':('sha256','1011dd58199550a726292289dfadecac6fb83863177fcad238d061b2fceb6ab4',9069032),
'C0001053_v5.mp4':('sha256','f8223fd6c25ec3cd02388917395e09d9c0c3acaa14940c57070ef35a5e264cb1',6199530),
'C0001055_v4.mp4':('sha256','25201b10b0d8eae6944187c0e6a8829155882f252402e4c0476276c6dd99ccfb',7022141),
'C0001056_v2.mp4':('sha256','2a9f1a109f8a8d37d624d4d8d650d8c15ae3b71b49901c6660e0b07f33a6c90e',10552517),
'annotation-data.json':('git','8b42b4663b75369235cb9881996ec3b3b0e79062',4854092),
'ground-truth.json':('git','bf10fdee4c01194928c9599678096046ecdb6358',118646),
'manifest.json':('git','0389ba73cbac9dc7d28c718d45d0fabc8621b2d3',1363),
'hash.md5':('git','36bb05b824935af16e5f93e095d8bccb0157e776',33),
'expected-output.text':('git','2279560c283ad74f0331b1b87ff1ec9c5724be24',20),
}
def valid(path,meta):
    if not path.is_file() or path.stat().st_size!=meta[2]:return False
    data=path.read_bytes()
    digest=hashlib.sha256(data).hexdigest() if meta[0]=='sha256' else hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    return digest==meta[1]
def fetch(item):
    name,meta=item;dest=OUT/name
    if valid(dest,meta):return name+' verified existing'
    part=OUT/(name+'.download')
    if adopt_verified_part(part,dest,lambda p:valid(p,meta)):return name+' resumed and verified'
    if part.exists() and part.stat().st_size>=meta[2] and not valid(part,meta):os.replace(part,OUT/(name+'.invalid.'+str(time.time_ns())))
    for host in ('huggingface.co','hf-mirror.com'):
        url=f'https://{host}/datasets/prcvlabs/multiview-retail-tracking/resolve/{REV}/testcases/006_site03_tracks/{name}'
        result=subprocess.run(['curl','-fsSL','--http1.1','--continue-at','-','--retry','6','--retry-all-errors','--retry-delay','2','--connect-timeout','15','--max-time','90','--output',str(part),url])
        if adopt_verified_part(part,dest,lambda p:valid(p,meta)):return name+' downloaded and verified'
        if part.exists() and part.stat().st_size>=meta[2]:os.replace(part,OUT/(name+'.invalid.'+str(time.time_ns())))
    raise RuntimeError('download or checksum failed: '+name)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(fetch,item) for item in FILES.items()]
        failures=[]
        for future in as_completed(futures):
            try:print(future.result(),flush=True)
            except Exception as exc:print(str(exc),flush=True);failures.append(str(exc))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
