"""Single-environment loopback entry point for the site03 research pipeline."""
from pathlib import Path
import argparse,getpass,importlib.metadata,importlib.util,json,os,platform,shutil,sys,time
from walkflows.artifact_cache import sha256
from walkflows.pipeline_runtime import Asset,_write_json,bundle_fingerprint,check_assets,fingerprint,manifest_current,pipeline_lock,run_steps,fail_journal,preparation_busy,wait_for_readers_lock
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'data/processed/local-pipeline'

def asset_specs():
    from scripts.fetch_site03_sample import FILES
    from scripts.fetch_site03_calibration import files as calibration
    from scripts.fetch_site03_models import MODELS,SIZES
    from scripts.fetch_site03_native_header import expected as native_header
    entries=[Asset('data/raw/multiview/006_site03_tracks/'+name,meta[0],meta[1],meta[2]) for name,meta in FILES.items()]
    entries.extend(Asset('data/upstream-research/'+Path(name).name,'git',digest) for name,digest in calibration.items())
    entries.append(Asset('data/upstream-research/calibration-utils.hpp','git',native_header))
    entries.extend(Asset('data/models/'+name,'sha256',digest,SIZES[name]) for name,digest in MODELS.items())
    return entries

def bundle_paths():
    from scripts.fetch_site03_sample import FILES
    prefix='data/processed/site03-review/'
    static=['index.html','data.json','layout.js','local_zones.js','site03_events.js','hypothesis_analytics.js','research_funnel.js','zone_transitions.js','source_comparison.js','quality_report.js']
    return [prefix+x for x in static]+[prefix+x for x in FILES if x.endswith('.mp4')]

def package_versions():
    versions={}
    for name in ('torch','torchvision','numpy','opencv-python','scipy','ultralytics','lap'):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    for module in ('torch','torchvision'):
        spec=importlib.util.find_spec(module)
        version_file=Path(spec.origin).parent/'version.py' if spec and spec.origin else None
        versions[module+'_build_hash']=sha256(version_file) if version_file and version_file.is_file() else None
    return versions

def read_json(path):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError,TypeError):return None

def local_environment():
    return {'user':getpass.getuser(),'uid':os.geteuid(),'python':platform.python_version(),'python_executable':sys.executable,'project_venv':str(ROOT/'.venv'),'using_project_venv':Path(sys.prefix).resolve()==(ROOT/'.venv').resolve(),'packages':package_versions(),'node':shutil.which('node'),'g++':shutil.which('g++'),'curl':shutil.which('curl')}

def status():
    assets=check_assets(ROOT,asset_specs());environment=local_environment();manifest=read_json(STATE/'manifest.json');journal=read_json(STATE/'state.json');verification=read_json(ROOT/'data/processed/site03-verification/report.json')
    busy=preparation_busy(STATE/'prepare.lock')
    last=journal.get('status') if isinstance(journal,dict) else None
    if last=='running' and not busy:last='interrupted_or_abandoned'
    report_path=ROOT/'data/processed/site03-verification/report.json'
    verification_matches=isinstance(manifest,dict) and report_path.is_file() and manifest.get('verification_sha256')==sha256(report_path) and isinstance(verification,dict) and verification.get('status')=='pass'
    current=not busy and environment['using_project_venv'] and environment['python'].startswith('3.12.') and all(a['state']=='ready' for a in assets) and verification_matches and manifest_current(ROOT,manifest,bundle_paths(),environment['packages'])
    return {'scope':'site03 research output only; not validated identities or customer counts','environment':environment,'assets':{'total':len(assets),'ready':sum(x['state']=='ready' for x in assets),'issues':[x for x in assets if x['state']!='ready']},'prepare_lock_busy':busy,'last_prepare':last,'bundle_current':current,'last_successful_scope':manifest.get('verification_scope') if isinstance(manifest,dict) else None,'gpu_health':'not checked by status; prepare runs GPU stages','review_url':'http://127.0.0.1:8767/'}

def check_inputs():
    issues=[x for x in check_assets(ROOT,asset_specs()) if x['state']!='ready']
    if issues:
        for x in issues:print(x['state']+': '+x['path'],flush=True)
        print('Missing or changed fixed inputs; run prepare --fetch to retrieve and verify them.',flush=True);return 1
    print('All fixed site03 inputs and model hashes verified.',flush=True);return 0

def serve(port):
    import subprocess
    directory=ROOT/'data/processed/site03-review'
    if not (directory/'index.html').is_file() or not (directory/'data.json').is_file():print('Review bundle missing; run prepare first.',file=sys.stderr);return 1
    if not status()['bundle_current']:print('Warning: bundle provenance is stale or has not been verified against current source.',file=sys.stderr)
    return subprocess.call([sys.executable,'-m','walkflows.review_server','--port',str(port),'--directory',str(directory),'--prepare-lock',str(STATE/'prepare.lock')],cwd=ROOT)

def prepare(fetch,cross_scene,then_serve,port):
    env=local_environment()
    if not env['using_project_venv']:print('Use the existing project virtual environment: .venv/bin/python -m walkflows prepare',file=sys.stderr);return 1
    missing=[name for name,value in env['packages'].items() if value is None]
    if missing or not env['node'] or not env['g++'] or (fetch and not env['curl']):
        print('Missing prerequisites: '+', '.join(missing+(['node'] if not env['node'] else [])+(['g++'] if not env['g++'] else [])+(['curl'] if fetch and not env['curl'] else [])),file=sys.stderr);return 1
    if sys.version_info[:2]!=(3,12):print('Project requires Python 3.12 in the existing .venv.',file=sys.stderr);return 1
    try:
        with wait_for_readers_lock(STATE/'prepare.lock'):
            before=fingerprint(ROOT);packages=env['packages'];steps=[]
            if fetch:
                for script in ('fetch_site03_sample.py','fetch_site03_calibration.py','fetch_site03_native_header.py','fetch_site03_models.py'):steps.append((script,[sys.executable,str(ROOT/'scripts'/script)]))
            steps.append(('check-inputs',[sys.executable,str(ROOT/'scripts/check_site03_inputs.py')]))
            for script in ('probe_site03.py','probe_site03_pose.py'):steps.append((script,[sys.executable,str(ROOT/'scripts'/script)]))
            verify=[sys.executable,str(ROOT/'scripts/verify_site03_research.py')]
            if not cross_scene:verify.append('--site03-only')
            steps.append(('verify-site03',verify));code=run_steps(ROOT,steps,STATE/'state.json')
            if code:return code
            if fingerprint(ROOT)!=before or package_versions()!=packages:
                fail_journal(STATE/'state.json','source or environment changed during preparation');print('Source or environment changed during preparation; no current manifest written.',file=sys.stderr);return 1
            verification_path=ROOT/'data/processed/site03-verification/report.json';verification=read_json(verification_path);bundle=bundle_fingerprint(ROOT,bundle_paths())
            if not verification or verification.get('status')!='pass' or verification.get('site03_only')==cross_scene or bundle is None:
                fail_journal(STATE/'state.json','verification or bundle incomplete');print('Verification or bundle incomplete; no current manifest written.',file=sys.stderr);return 1
            manifest={'status':'passed','verification_scope':'site03_and_cross_scene' if cross_scene else 'site03_only','source_fingerprint':before,'bundle_fingerprint':bundle,'verification_sha256':sha256(verification_path),'packages':packages,'completed_unix_s':time.time(),'scope':'Research only; identity, localization and customer statistics not validated.'}
            try:_write_json(STATE/'manifest.json',manifest)
            except OSError as error:
                fail_journal(STATE/'state.json','manifest write failed: '+str(error));print('Manifest write failed: '+str(error),file=sys.stderr);return 1
            print('Research bundle prepared and verified; no identity or customer-count acceptance implied.',flush=True)
    except BlockingIOError:
        print('A preparation or active review request holds the project lock; inspect status and retry after it finishes.',file=sys.stderr);return 2
    return serve(port) if then_serve else 0

def main(argv=None):
    parser=argparse.ArgumentParser(description='WalkFlows local research pipeline; use the WSL non-root user and existing .venv.')
    sub=parser.add_subparsers(dest='command',required=True)
    s=sub.add_parser('status',help='inspect input and bundle status');s.add_argument('--json',action='store_true')
    p=sub.add_parser('prepare',help='prepare and verify the site03 research bundle');p.add_argument('--fetch',action='store_true',help='retrieve missing fixed inputs and models');p.add_argument('--cross-scene',action='store_true',help='also verify existing site02 comparison assets');p.add_argument('--serve',action='store_true',help='serve the resulting bundle in the foreground');p.add_argument('--port',type=int,default=8767)
    q=sub.add_parser('serve',help='serve the existing bundle on loopback');q.add_argument('--port',type=int,default=8767)
    project=sub.add_parser('project-validate',help='validate generic local video inputs without running inference');project.add_argument('--config',required=True,help='JSON camera configuration')
    run=sub.add_parser('project-run',help='run sequential per-camera detection and tracking');run.add_argument('--config',required=True);run.add_argument('--output',required=True);run.add_argument('--weights',default=str(ROOT/'data/models/yolo11n.pt'));run.add_argument('--device',default='cpu',help='CPU or CUDA device, for example cpu or 0');run.add_argument('--resume',action='store_true',help='reuse verified completed cameras in an interrupted or failed run');run.add_argument('--image-size',type=int,default=640,help='model input size, a multiple of 32');run.add_argument('--confidence',type=float,default=0.25,help='person detection confidence threshold')
    review=sub.add_parser('project-review',help='review a completed generic run on loopback');review.add_argument('--output',required=True);review.add_argument('--port',type=int,default=8768)
    calibration=sub.add_parser('project-calibrate',help='fit a plane mapping from matching points');calibration.add_argument('--points',required=True,help='JSON with image_points and plane_points')
    calui=sub.add_parser('project-calibration-ui',help='select calibration points from project videos');calui.add_argument('--config',required=True);calui.add_argument('--port',type=int,default=8769)
    applycal=sub.add_parser('project-apply-calibration',help='create a new project config with a fitted mapping');applycal.add_argument('--config',required=True);applycal.add_argument('--camera',required=True);applycal.add_argument('--points',required=True);applycal.add_argument('--output',required=True)
    create=sub.add_parser('project-create',help='create a validated video project');create.add_argument('--name',required=True);create.add_argument('--camera',action='append',required=True,metavar='ID=PATH');create.add_argument('--offset',action='append',default=[],metavar='ID=SECONDS');create.add_argument('--output',required=True)
    runstatus=sub.add_parser('project-status',help='inspect a generic processing run');runstatus.add_argument('--output',required=True)
    evaluate=sub.add_parser('project-evaluate-reference',help='conditional frame-indexed position comparison');evaluate.add_argument('--output',required=True,help='completed run directory');evaluate.add_argument('--reference',required=True);evaluate.add_argument('--distance',required=True,type=float,help='proximity gate in scene units');evaluate.add_argument('--assume-aligned',action='store_true',required=True,help='assert reference uses the same frame zero and coordinates');evaluate.add_argument('--report',help='write a new JSON report')
    offsets=sub.add_parser('project-apply-offsets',help='create a validated project using timing offsets');offsets.add_argument('--config',required=True);offsets.add_argument('--offsets',required=True);offsets.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    if os.geteuid()==0:print('Direct root execution is prohibited; use the WSL non-root user.',file=sys.stderr);return 1
    if args.command=='project-evaluate-reference':
        from walkflows.generic_reference import evaluate_run
        try:
            result=evaluate_run(args.output,args.reference,args.distance)
            content=json.dumps(result,ensure_ascii=False,indent=2)
            if args.report:
                with Path(args.report).open('x',encoding='utf-8') as file:file.write(content+'\n')
            print(content)
        except (ValueError,OSError,KeyError,TypeError,ZeroDivisionError) as error:print('Reference evaluation failed: '+str(error),file=sys.stderr);return 1
        return 0
    if args.command=='project-apply-offsets':
        from walkflows.multicamera_project import apply_offsets
        try:result=apply_offsets(args.config,args.offsets,args.output)
        except (ValueError,OSError,KeyError,TypeError) as error:print('Cannot apply offsets: '+str(error),file=sys.stderr);return 1
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if args.command=='project-status':
        from walkflows.multicamera_processing import inspect_run
        try:result=inspect_run(args.output)
        except (ValueError,OSError,TypeError) as error:print('Cannot inspect run: '+str(error),file=sys.stderr);return 1
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if args.command=='project-create':
        from walkflows.multicamera_project import create_config
        try:
            cameras=[]
            for spec in args.camera:
                if '=' not in spec:raise ValueError('camera must use ID=PATH')
                cid,path=spec.split('=',1);cameras.append({'id':cid,'path':path})
            offsets={}
            for spec in args.offset:
                if '=' not in spec:raise ValueError('offset must use ID=SECONDS')
                cid,value=spec.split('=',1)
                if cid in offsets:raise ValueError('duplicate camera offset')
                offsets[cid]=float(value)
            if set(offsets)-{c['id'] for c in cameras}:raise ValueError('offset references unknown camera')
            for camera in cameras:camera['offset_seconds']=offsets.get(camera['id'],0)
            result=create_config(args.name,cameras,args.output)
        except (ValueError,OSError) as error:print('Cannot create project: '+str(error),file=sys.stderr);return 1
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if args.command=='project-apply-calibration':
        from walkflows.plane_calibration import apply_calibration
        try:result=apply_calibration(args.config,args.camera,args.points,args.output)
        except (ValueError,OSError,KeyError,TypeError) as error:print('Cannot apply calibration: '+str(error),file=sys.stderr);return 1
        print(json.dumps({'output':str(Path(args.output).resolve()),'points':result['points'],'rmse':result['rmse'],'scope':result['scope']},indent=2));return 0
    if args.command=='project-calibration-ui':
        from walkflows.multicamera_project import build_project
        from walkflows.multicamera_review import serve_calibration
        try:serve_calibration(build_project(args.config,allow_no_overlap=True),args.port)
        except (ValueError,OSError,KeyError) as error:print('Cannot open calibration: '+str(error),file=sys.stderr);return 1
        return 0
    if args.command=='project-calibrate':
        from walkflows.plane_calibration import fit_homography
        try:
            points=json.loads(Path(args.points).read_text(encoding='utf-8'));result=fit_homography(points['image_points'],points['plane_points'])
        except (ValueError,OSError,KeyError,TypeError) as error:print('Invalid calibration: '+str(error),file=sys.stderr);return 1
        print(json.dumps(result,indent=2));return 0
    if args.command=='project-review':
        from walkflows.multicamera_review import serve as serve_project
        try:serve_project(args.output,args.port)
        except (ValueError,OSError,KeyError) as error:print('Cannot review project: '+str(error),file=sys.stderr);return 1
        return 0
    if args.command=='project-run':
        from walkflows.multicamera_project import build_project
        from walkflows.multicamera_processing import run_project
        try:result=run_project(build_project(args.config),args.output,args.weights,args.device,resume=args.resume,image_size=args.image_size,confidence=args.confidence)
        except (ValueError,OSError,RuntimeError) as error:print('Project failed: '+str(error),file=sys.stderr);return 1
        print(json.dumps({'status':result['status'],'output':str(Path(args.output).resolve()),'cameras':result['cameras']},indent=2));return 0
    if args.command=='project-validate':
        from walkflows.multicamera_project import build_project
        try:result=build_project(args.config)
        except (ValueError,OSError) as error:print('Invalid project: '+str(error),file=sys.stderr);return 1
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if args.command=='status':
        result=status()
        if args.json:print(json.dumps(result,ensure_ascii=False,indent=2))
        else:
            print('User:',result['environment']['user'],'| project .venv:',result['environment']['using_project_venv'])
            print('Fixed inputs:',result['assets']['ready'],'/',result['assets']['total'],'| current verified bundle:',result['bundle_current'])
            print('Prepare lock busy:',result['prepare_lock_busy'],'| last prepare:',result['last_prepare'])
            for item in result['assets']['issues']:print(item['state']+': '+item['path'])
            print('Scope: research only; identity and customer counts remain unvalidated.')
        return 0
    if args.command=='serve':return serve(args.port)
    return prepare(args.fetch,args.cross_scene,args.serve,args.port)
