"""Run an isolated mixed nano/small pose downstream research comparison."""
from pathlib import Path
import json,hashlib,os,shutil,subprocess,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));p=root/'data/processed';base=p/'site03-pose-evidence';small=p/'site03-pose-s-evidence';mixed=p/'site03-pose-s-mixed-evidence';mixed.mkdir(parents=True,exist_ok=True);sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
a=json.loads((base/'summary.json').read_text());b=json.loads((small/'summary.json').read_text());smap={x['camera']:x for x in b['cameras']};targets={'C0001055_v4','C0001056_v2'}
if set(smap)!=targets:raise ValueError('incomplete small-pose cameras')
entries=[]
for old in a['cameras']:
 cam=old['camera'];entry=smap[cam] if cam in targets else old;source=(small if cam in targets else base)/(cam+'_track_pose.csv');dest=mixed/source.name
 if sha(source)!=entry['pose_csv_sha256'] or entry['track_sha256']!=old['track_sha256']:raise ValueError('pose or track mismatch')
 temp=dest.with_suffix('.tmp');shutil.copyfile(source,temp);os.replace(temp,dest);entries.append(entry)
meta={**a,'scope':'Experimental mixed pose models; nano on four cameras and small on two; not identity truth.','weight_sha256':'mixed; see model_weight_sha256_by_camera','script_sha256':'mixed; see inference_script_sha256_by_camera','inference_script_sha256_by_camera':{e['camera']:(b['script_sha256'] if e['camera'] in targets else a['script_sha256']) for e in entries},'model_weight_sha256_by_camera':{e['camera']:(b['weight_sha256'] if e['camera'] in targets else a['weight_sha256']) for e in entries},'cameras':entries,'input_summaries':{'nano_sha256':sha(base/'summary.json'),'small_sha256':sha(small/'summary.json')}};(mixed/'summary.json').write_text(json.dumps(meta,indent=2))
work=p/'site03-pose-s-experiment-scripts';work.mkdir(parents=True,exist_ok=True);replacements={'site03-pose-evidence':'site03-pose-s-mixed-evidence','site03-pose-floor':'site03-pose-s-mixed-floor','site03-pose-proposals':'site03-pose-s-mixed-proposals','site03-hypotheses':'site03-pose-s-mixed-hypotheses'}
for name in ('export_site03_pose_floor.py','probe_site03_pose_crossview.py','build_site03_hypotheses.py'):
 src=root/'scripts'/name;text=src.read_text();old='root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))'
 if old not in text:raise ValueError('unexpected upstream script shape '+name)
 text=text.replace(old,'root=Path('+repr(str(root))+');sys.path.insert(0,str(root))',1)
 for a0,b0 in replacements.items():text=text.replace(a0,b0)
 tmp=work/name;tmp.write_text(text);print('running',name,flush=True);subprocess.run([sys.executable,str(tmp)],cwd=root,check=True,stdout=subprocess.DEVNULL)
from walkflows.stitched_journeys import stitch
linked_input=p/'site03-tracklet-experiment/summary.json';tracklet=json.loads(linked_input.read_text());mixed_hyp=p/'site03-pose-s-mixed-hypotheses/hypotheses.json';h=json.loads(mixed_hyp.read_text());linked=stitch(h['hypotheses'],tracklet['links'],.5);linked_path=work/'linked.json';linked_path.write_text(json.dumps({'scope':'Experimental mixed-model and local-link candidates; not identity truth.','hypotheses':linked},indent=2,allow_nan=False))
result={'scope':'Experimental nano/small mixed pose comparison; not calibrated identity, localization or customer counts.','input_summaries':meta['input_summaries'],'tracklet_summary_sha256':sha(linked_input),'linked_sha256':sha(linked_path),'derived_scripts':{name:sha(work/name) for name in ('export_site03_pose_floor.py','probe_site03_pose_crossview.py','build_site03_hypotheses.py')},'hypotheses_summary':json.loads((p/'site03-pose-s-mixed-hypotheses/summary.json').read_text()),'floor_summary_sha256':sha(p/'site03-pose-s-mixed-floor/summary.json'),'proposals_summary_sha256':sha(p/'site03-pose-s-mixed-proposals/summary.json')};(work/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
