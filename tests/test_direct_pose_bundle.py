import json,tempfile,unittest
from pathlib import Path
from walkflows.artifact_cache import sha256
from walkflows.direct_pose_bundle import load_direct_pose

class DirectPoseBundleTest(unittest.TestCase):
 def test_missing_and_stale_data_are_not_loaded(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   def put(path,contents):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(contents);return p
   def js(path,obj):return put(path,json.dumps(obj))
   self.assertIsNone(load_direct_pose(root,'base','ref','scene'))
   evaluate=put('scripts/evaluate_site03_direct_pose_journeys.py','evaluate');probe=put('scripts/probe_site03_pose_direct.py','probe')
   model=put('data/models/yolo11s-pose.pt','weights');video=put('data/raw/multiview/006_site03_tracks/cam.mp4','video');sensor=put('data/upstream-research/cam.json','sensor')
   d='data/processed/site03-direct-pose-probe/cam/';obs=put(d+'observations.csv','tracks')
   info=js(d+'report.json',{'observations_sha256':sha256(obs),'camera':'cam','scene_sha256':'scene','reference_sha256':'ref','script_sha256':sha256(probe),'weights_sha256':sha256(model),'video_sha256':sha256(video),'sensor_sha256':sha256(sensor)})
   js('data/processed/site03-pose-floor/summary.json',{'scene_sha256':'scene','cameras':[{'camera':'cam'}]})
   inputs={'cam':{'kind':'direct_pose','observations_sha256':sha256(obs),'report_sha256':sha256(info)}}
   h=js('data/processed/site03-direct-pose-journeys/hypotheses.json',{'inputs':inputs,'hypotheses':[{'id':'test'}]})
   js('data/processed/site03-direct-pose-journeys/report.json',{'inputs':inputs,'hypotheses_sha256':sha256(h),'baseline_hypotheses_sha256':'base','reference_sha256':'ref','script_sha256':sha256(evaluate)})
   self.assertEqual(load_direct_pose(root,'base','ref','scene')['hypotheses'],[{'id':'test'}])
   obs.write_text('changed');self.assertIsNone(load_direct_pose(root,'base','ref','scene'))

if __name__=='__main__':unittest.main()
