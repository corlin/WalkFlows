"""Retrieve source-pinned site03 calibration JSONs and verify Git object IDs."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,subprocess,os
root=Path(__file__).resolve().parents[1];out=root/'data/upstream-research';revision='7e334db96ca7ab685628365a2eaa2d5e8117eac3'
files={'scenes/site03_scene03.json':'ac45311a416ca267fd7c283442060ae1f1a355b8','binocular/C0001020_v1.json':'586ea65c74ee1e53bcb9a71cc379c847e3600e17','binocular/C0001025_v1.json':'d8dcdc84a3b2da9c4eb138570d52202c16456489','binocular/C0001029_v2.json':'939a506b0e3fcdb4b5286411dc33e7184161314b','binocular/C0001053_v5.json':'9245761bc393a406d4b4bf7879d26f580fd29a1f','binocular/C0001055_v4.json':'868671decae10509fcd8f9c0be662b6c38543501','binocular/C0001056_v2.json':'e25a96485a1a99f84a8e94ebb467375a64cb3956'}
def valid(path,expected):
 if not path.is_file():return False
 data=path.read_bytes();return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected
def download(item):
 relative,expected=item;dest=out/Path(relative).name;tmp=dest.with_suffix('.json.download')
 if valid(dest,expected):return dest.name+' verified existing'
 url=f'https://raw.githubusercontent.com/prcvlabs/multiview/{revision}/data/calibration/{relative}'
 subprocess.run(['curl','-fsSL','--retry','4','--retry-all-errors','--retry-delay','2','--connect-timeout','15','--max-time','60','-o',str(tmp),url],check=True)
 if not valid(tmp,expected):raise ValueError('unexpected blob: '+relative)
 os.replace(tmp,dest);return dest.name+' verified'
def main():
 out.mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=3) as pool:
  futures=[pool.submit(download,item) for item in files.items()]
  for f in as_completed(futures):print(f.result(),flush=True)
if __name__=='__main__':main()
