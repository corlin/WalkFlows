"""Fetch the exact native calibration lift header from a pinned upstream commit."""
from pathlib import Path
import hashlib,os,subprocess
root=Path(__file__).resolve().parents[1];path=root/'data/upstream-research/calibration-utils.hpp';expected='99b4deadde025e4e0794705f85156cc464300730'
def valid(path):
 if not path.is_file():return False
 data=path.read_bytes();return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected
def main():
 if valid(path):print('native header verified');return
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.hpp.download');url='https://raw.githubusercontent.com/prcvlabs/multiview/7e334db96ca7ab685628365a2eaa2d5e8117eac3/multiview/multiview_cpp/src/perceive/calibration/calibration-utils.hpp'
 subprocess.run(['curl','-fsSL','--retry','4','--retry-all-errors','--retry-delay','2','--connect-timeout','15','--max-time','60','-o',str(tmp),url],check=True)
 if not valid(tmp):raise ValueError('native header checksum mismatch')
 os.replace(tmp,path);print('native header downloaded and verified')
if __name__=='__main__':main()
