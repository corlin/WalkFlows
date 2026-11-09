"""Train a fixed pilot residual model from spatial-proxy pairs; not production."""
from pathlib import Path
import argparse,collections,hashlib,json,math,os,statistics,sys
import numpy as np,torch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.artifact_cache import sha256,cache_valid
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--expanded',action='store_true',help='use all successfully exported labeled training scenarios');args=parser.parse_args()
TRAIN=('002_site02_gaze','006_site03_tracks','007_site03_sparse_tracks');VALIDATION=('011_site06_standing',);omitted=[];batch_sha=None
raw=root/'data/raw/multiview/full-dataset';processed=root/'data/processed';state=processed/'multiview-inventory';inventory=json.loads((state/'manifest.json').read_text());splits=json.loads((state/'site-splits.json').read_text());export_script=root/'scripts/export_weak_position_labels.py'
if splits['manifest_sha256']!=sha256(state/'manifest.json') or splits['revision']!=inventory['revision']:raise ValueError('split manifest mismatch')
if args.expanded:
 batch_path=processed/'weak-position-labels/training-batch.json';batch=json.loads(batch_path.read_text());batch_sha=sha256(batch_path)
 if batch['status'] not in ('complete','incomplete') or batch['splits_sha256']!=sha256(state/'site-splits.json') or batch['exporter_sha256']!=sha256(export_script):raise ValueError('stale or running batch')
 expected={e['path'].split('/')[1] for e in splits['splits']['train'] if e['path'].startswith('testcases/') and e['path'].endswith('/ground-truth.json')};actual=[x['scenario'] for x in batch['scenarios']]
 if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError('incomplete batch ledger')
 TRAIN=tuple(x['scenario'] for x in batch['scenarios'] if x['exit_code']==0);omitted=[x['scenario'] for x in batch['scenarios'] if x['exit_code']!=0];VALIDATION=('011_site06_standing','044_site06_sitting_1')

inputs={}
def load(scenarios,role):
 rows=[];allowed={e['path'] for e in splits['splits'][role]}
 for scenario in scenarios:
  manifest_rel='testcases/'+scenario+'/manifest.json'
  if manifest_rel not in allowed:raise ValueError('scenario not in expected split')
  manifest=json.loads((raw/manifest_rel).read_text());folder=processed/'weak-position-labels'/scenario
  for camera in sorted(x['camera'] for x in manifest['videos']):
   path=folder/(camera+'.jsonl');cache=folder/(camera+'.cache.json');meta=json.loads(cache.read_text());contract=meta['contract']
   if contract['split']!=role or contract['scenario']!=scenario or contract['camera']!=camera or contract['script_sha256']!=sha256(export_script) or contract.get('scenario_validator_sha256')!=sha256(root/'walkflows/scenario_names.py') or contract.get('extent_validator_sha256')!=sha256(root/'walkflows/reference_extent.py') or contract.get('scene_transforms_sha256')!=sha256(root/'walkflows/scene_transforms.py') or contract['inventory_sha256']!=sha256(state/'manifest.json') or contract['splits_sha256']!=sha256(state/'site-splits.json') or contract['manifest_sha256']!=sha256(raw/manifest_rel) or not cache_valid(cache,contract,folder,(path.name,)):raise ValueError('weak-label provenance mismatch')
   inputs[scenario+'/'+camera]={'role':role,'weak_labels_sha256':sha256(path),'cache_sha256':sha256(cache)}
   with path.open() as f:
    frames=[json.loads(line) for line in f]
   if len(frames)!=contract['frames'] or [x['frame'] for x in frames]!=list(range(contract['frames'])):raise ValueError('frame ledger mismatch')
   for frame in frames:
    for pair in frame['weak_pairs']:
     if pair['label_kind']!='spatial_unique_proxy' or pair['distance']>.5:raise ValueError('invalid weak label')
     x,y=pair['input_x'],pair['input_y'];tx,ty=pair['target_x'],pair['target_y'];l,t,r,b=pair['box'];px,py=pair['foot_pixel'];confidence=pair['confidence']
     features=[x/10,y/10,px/896,py/672,(r-l)/896,(b-t)/672,confidence];target=[tx-x,ty-y]
     if not all(math.isfinite(v) for v in features+target):raise ValueError('invalid numeric feature')
     rows.append({'scenario':scenario,'camera':camera,'frame':frame['frame'],'reference_id':pair['reference_id'],'features':features,'target':target})
 return rows
train=load(TRAIN,'train');validation=load(VALIDATION,'validation')
if len(train)<100 or len(validation)<30:raise ValueError('insufficient weak support')
if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
device=torch.device('cuda:0');torch.manual_seed(42);torch.cuda.manual_seed_all(42)
model=torch.nn.Sequential(torch.nn.Linear(7,32),torch.nn.ReLU(),torch.nn.Linear(32,2)).to(device)
torch.nn.init.zeros_(model[-1].weight);torch.nn.init.zeros_(model[-1].bias)
x=torch.tensor([r['features'] for r in train],dtype=torch.float32,device=device);y=torch.tensor([r['target'] for r in train],dtype=torch.float32,device=device);vx=torch.tensor([r['features'] for r in validation],dtype=torch.float32,device=device);vy=torch.tensor([r['target'] for r in validation],dtype=torch.float32,device=device)
optim=torch.optim.Adam(model.parameters(),lr=.001,weight_decay=.001);losses=[]
for epoch in range(100):
 optim.zero_grad();pred=model(x);loss=torch.nn.functional.mse_loss(pred,y);loss.backward();optim.step();losses.append(float(loss.detach().cpu()))
with torch.no_grad():
 delta=model(vx);before=torch.linalg.vector_norm(vy,dim=1).cpu().numpy();after=torch.linalg.vector_norm(vy-delta,dim=1).cpu().numpy();predicted=delta.cpu().numpy()

out=processed/('weak-localizer-expanded' if args.expanded else 'weak-localizer-pilot');out.mkdir(parents=True,exist_ok=True);checkpoint=out/'model.pt';temp=out/'model.pt.tmp';torch.save({'state_dict':{k:v.detach().cpu() for k,v in model.state_dict().items()},'features':7,'hidden':32},temp);os.replace(temp,checkpoint)
predpath=out/'validation-predictions.jsonl';tmp=out/'validation-predictions.jsonl.tmp'
with tmp.open('w') as f:
 for r,b,a,p in zip(validation,before,after,predicted):f.write(json.dumps({'scenario':r['scenario'],'camera':r['camera'],'frame':r['frame'],'reference_id':r['reference_id'],'baseline_distance':float(b),'corrected_distance':float(a),'predicted_delta':[float(x) for x in p]},allow_nan=False)+'\n')
os.replace(tmp,predpath)
camera_metrics={}
for camera in sorted({r['camera'] for r in validation}):
 indices=[i for i,r in enumerate(validation) if r['camera']==camera];b=before[indices];a=after[indices]
 camera_metrics[camera]={'pairs':len(indices),'baseline_median':float(np.median(b)),'corrected_median':float(np.median(a)),'improved':int(np.sum(a<b)),'worsened':int(np.sum(a>b))}
scenario_metrics={}
for scenario in VALIDATION:
 indices=[i for i,r in enumerate(validation) if r['scenario']==scenario];b=before[indices];a=after[indices]
 scenario_metrics[scenario]={'pairs':len(indices),'baseline_median':float(np.median(b)) if indices else None,'corrected_median':float(np.median(a)) if indices else None,'improved':int(np.sum(a<b)),'worsened':int(np.sum(a>b))}
report={'batch_sha256':batch_sha,'omitted_training_scenarios':omitted,'training_pairs_by_scenario':dict(collections.Counter(r['scenario'] for r in train)),'validation_by_scenario':scenario_metrics,'validation_by_camera':camera_metrics,'scope':'weak proximity-proxy pilot; no verified identity, production model or test-set evaluation','training_scenarios':TRAIN,'validation_scenarios':VALIDATION,'site_test_policy':'site07 not read','inputs':inputs,'inventory_sha256':sha256(state/'manifest.json'),'splits_sha256':sha256(state/'site-splits.json'),'trainer_sha256':sha256(Path(__file__)),'model_sha256':sha256(checkpoint),'validation_predictions_sha256':sha256(predpath),'parameters':{'seed':42,'epochs':100,'optimizer':'Adam','learning_rate':.001,'weight_decay':.001,'device':str(device),'hidden':32},'versions':{'torch':str(torch.__version__),'cuda':str(torch.version.cuda)},'train_pairs':len(train),'validation_pairs':len(validation),'train_loss_first':losses[0],'train_loss_last':losses[-1],'validation':{'baseline_median':float(np.median(before)),'corrected_median':float(np.median(after)),'baseline_mean':float(np.mean(before)),'corrected_mean':float(np.mean(after)),'improved':int(np.sum(after<before)),'worsened':int(np.sum(after>before))}}
(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='inputs'},indent=2))
