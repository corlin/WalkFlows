"""Local pipeline primitives: verified inputs, source fingerprint, journal and lock."""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import fcntl,hashlib,json,os,re,signal,subprocess,sys,time

@dataclass(frozen=True)
class Asset:
    path: str
    algorithm: str
    digest: str
    size: int | None = None

def check_assets(root,specs):
    root=Path(root).resolve();results=[]
    for spec in specs:
        relative=Path(spec.path)
        if relative.is_absolute() or '..' in relative.parts or spec.algorithm not in ('sha256','git'):raise ValueError('invalid asset specification')
        path=root/relative
        if not path.is_file():state='missing'
        elif not path.resolve().is_relative_to(root):state='mismatch'
        elif spec.size is not None and path.stat().st_size!=spec.size:state='mismatch'
        else:
            size=path.stat().st_size;digest=hashlib.sha256() if spec.algorithm=='sha256' else hashlib.sha1()
            if spec.algorithm=='git':digest.update(b'blob '+str(size).encode()+b'\0')
            with path.open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
            state='ready' if digest.hexdigest()==spec.digest else 'mismatch'
        results.append({'path':spec.path,'state':state})
    return results

def fingerprint(root):
    root=Path(root);files=[]
    for name in ('walkflows','scripts','tests'):
        directory=root/name
        if directory.is_dir():files.extend(p for p in directory.rglob('*') if p.is_file() and p.suffix in ('.py','.js','.html') and '__pycache__' not in p.parts)
    for name in ('pyproject.toml','uv.lock'):
        p=root/name
        if p.is_file():files.append(p)
    digest=hashlib.sha256()
    for path in sorted(files,key=lambda p:p.relative_to(root).as_posix()):
        name=path.relative_to(root).as_posix().encode();data=path.read_bytes();digest.update(len(name).to_bytes(8,'big'));digest.update(name);digest.update(len(data).to_bytes(8,'big'));digest.update(data)
    return digest.hexdigest()

def _write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False));os.replace(tmp,path)

@contextmanager
def pipeline_lock(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)

def run_steps(root,steps,journal):
    root=Path(root);journal=Path(journal);run_id=str(time.time_ns())+'-'+str(os.getpid());logdir=journal.parent/'runs'/run_id;logdir.mkdir(parents=True,exist_ok=False)
    report={'status':'running','run_id':run_id,'log_directory':str(logdir),'steps':[]};_write_json(journal,report)
    try:
        for name,command in steps:
            if not re.fullmatch(r'[A-Za-z0-9_.-]+',name):raise ValueError('invalid step name')
            entry={'name':name,'status':'running'};report['steps'].append(entry);_write_json(journal,report);print('\n>>> '+name,flush=True);start=time.monotonic()
            try:
                with (logdir/(name+'.log')).open('w') as log:
                    process=subprocess.Popen(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1,start_new_session=True)
                    try:
                        for line in process.stdout:
                            log.write(line);log.flush();sys.stdout.write(line);sys.stdout.flush()
                        code=process.wait()
                    except BaseException:
                        try:os.killpg(process.pid,signal.SIGTERM)
                        except ProcessLookupError:pass
                        try:process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            try:os.killpg(process.pid,signal.SIGKILL)
                            except ProcessLookupError:pass
                            process.wait()
                        raise
                    finally:process.stdout.close()
            except OSError as error:
                entry['error']=str(error);code=127
            entry.update(status='passed' if code==0 else 'failed',exit_code=code,elapsed_s=time.monotonic()-start);_write_json(journal,report)
            if code:
                report['status']='failed';_write_json(journal,report);return code
        report['status']='passed';_write_json(journal,report);return 0
    except BaseException as error:
        report['status']='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed';report['error']=type(error).__name__;_write_json(journal,report);raise

def bundle_fingerprint(root,relative_paths):
    root=Path(root).resolve();digest=hashlib.sha256()
    for name in sorted(relative_paths):
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:return None
        path=root/rel
        if not path.is_file() or not path.resolve().is_relative_to(root):return None
        encoded=rel.as_posix().encode();digest.update(len(encoded).to_bytes(8,'big'));digest.update(encoded);digest.update(path.stat().st_size.to_bytes(8,'big'))
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def manifest_current(root,manifest,bundle_paths,packages):
    if not isinstance(manifest,dict) or manifest.get('status')!='passed':return False
    current=bundle_fingerprint(root,bundle_paths)
    return current is not None and manifest.get('source_fingerprint')==fingerprint(root) and manifest.get('bundle_fingerprint')==current and manifest.get('packages')==packages

def fail_journal(path,message):
    path=Path(path)
    try:report=json.loads(path.read_text())
    except (OSError,ValueError,TypeError):report={'steps':[]}
    if not isinstance(report,dict):report={'steps':[]}
    report['status']='failed';report['error']=str(message);_write_json(path,report)

def preparation_busy(path):
    """Report an exclusive preparation, ignoring concurrent shared readers."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+') as f:
        try:fcntl.flock(f,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:return True
        fcntl.flock(f,fcntl.LOCK_UN);return False

@contextmanager
def wait_for_readers_lock(path,timeout=3):
    """Wait briefly for review reads; never start a second active preparation."""
    if not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not 0<=timeout<=60:raise ValueError('invalid lock timeout')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);deadline=time.monotonic()+timeout
    with path.open('a+') as f:
        while True:
            try:
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if preparation_busy(path) or time.monotonic()>=deadline:raise
                time.sleep(min(.05,max(0,deadline-time.monotonic())))
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)
