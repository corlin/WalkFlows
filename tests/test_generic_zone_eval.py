import unittest
import json
import subprocess
import sys
import csv
import tempfile
from pathlib import Path
from walkflows.multicamera_processing import file_sha256
from walkflows.generic_zone_eval import flows_for_camera, nearby_flows, validate_zones


class GenericZoneEvalTest(unittest.TestCase):
    def test_flows_require_continuous_unique_projected_frames(self):
        zones=[{"name":"A","points":[[0,0],[1,0],[1,1],[0,1]]},
               {"name":"B","points":[[2,0],[3,0],[3,1],[2,1]]}]
        rows=[{"id":"1","frame":i,"x":x,"y":0.5} for i,x in enumerate([0.5,1.5,2.5])]
        flows=flows_for_camera(rows,zones,"cam",5,0,10)
        self.assertEqual([(f["from"],f["to"],f["exit_frame"],f["arrival_frame"]) for f in flows],
                         [("A","B",1,2)])
        self.assertEqual(flows_for_camera([rows[0],rows[2]],zones,"cam",5,0,10),[])
        self.assertEqual(flows_for_camera(rows+[dict(rows[1])],zones,"cam",5,0,10),[])
        self.assertEqual(flows_for_camera(rows,zones,"cam",5,0,0.1),[])

    def test_reference_nearness_does_not_assert_identity(self):
        prediction={"from":"A","to":"B","exit_time":1.0,"arrival_time":2.0}
        references=[{"id":"r1","from":"A","to":"B","exit_time":1.1,"arrival_time":2.1},
                    {"id":"r2","from":"A","to":"B","exit_time":1.2,"arrival_time":2.2}]
        self.assertEqual(len(nearby_flows(prediction,references,0.25)),2)
        self.assertEqual(nearby_flows(prediction,references,0.05),[])

    def test_python_matches_browser_algorithm_for_conflict_and_gap(self):
        zones=[{"name":"A","points":[[0,0],[1,0],[1,1],[0,1]]},
               {"name":"B","points":[[2,0],[3,0],[3,1],[2,1]]}]
        rows=[{"id":"1","frame":i,"x":x,"y":0.5} for i,x in enumerate([0.5,1.5,2.5])]
        rows += [{"id":"2","frame":0,"x":0.5,"y":0.5},{"id":"2","frame":2,"x":2.5,"y":0.5}]
        payload=json.dumps({"rows":rows,"zones":zones})
        module=Path(__file__).resolve().parents[1]/"walkflows/web/analytics.js"
        script="""const a=require(process.argv[1]); const d=JSON.parse(process.argv[2]); const events=[];
          const frames=new Map();
          for(const p of d.rows){const k=JSON.stringify(['cam',p.id]);if(!frames.has(k))frames.set(k,new Map());
            frames.get(k).set(p.frame,(frames.get(k).get(p.frame)||0)+1);}
          d.zones.forEach((z,i)=>a.zoneTransitions(d.rows.map(r=>({...r,time:r.frame/5})),z.points)
            .forEach(e=>events.push({...e,camera:'cam',zone:z.name,zone_index:i})));
          console.log(JSON.stringify(a.regionFlows(events,frames,10)));"""
        output=subprocess.check_output(["node","-e",script,str(module),payload],text=True)
        self.assertEqual(json.loads(output),flows_for_camera(rows,zones,"cam",5,0,10))

    def test_zone_validation_rejects_degenerate_and_duplicate_names(self):
        valid=[{"name":"a","points":[[0,0],[2,0],[0,2]]}]
        validate_zones(valid)
        with self.assertRaisesRegex(ValueError,"zone"):
            validate_zones([{"name":"bad","points":[[0,0],[1,1],[2,2]]}])
        with self.assertRaisesRegex(ValueError,"zone"):
            validate_zones(valid+valid)

    def test_report_command_evaluates_reference_and_tracks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/"video.mp4";video.write_bytes(b"example")
            csv_path=root/"cam.csv"
            with csv_path.open("w",newline="") as file:
                writer=csv.DictWriter(file,fieldnames=["frame","local_id","world_x","world_y"])
                writer.writeheader()
                for frame,x in enumerate([0.5,1.5,2.5]):
                    writer.writerow({"frame":frame,"local_id":"7","world_x":x,"world_y":0.5})
            run={"status":"completed","project":{"cameras":[{"id":"cam","offset_seconds":0,
                "video":{"path":str(video),"sha256":file_sha256(video),"fps":5}}]},
                "cameras":[{"id":"cam","status":"completed","decoded_frames":3,
                            "observations_sha256":file_sha256(csv_path)}]}
            (root/"run.json").write_text(json.dumps(run))
            ref={"track_results":{"frames":3,"width":10,"height":10,"hist-sz":1,"top-left":[0,0],
                "frame-duration":0.2,"start-frame":0,
                "tracks":[{"id":8,"path":[[0.5,0.5,0],[1.5,0.5,1],[2.5,0.5,2]]}]}}
            refpath=root/"ref.json";refpath.write_text(json.dumps(ref))
            zones={"zones":[{"name":"A","points":[[0,0],[1,0],[1,1],[0,1]]},
                            {"name":"B","points":[[2,0],[3,0],[3,1],[2,1]]}]}
            zonepath=root/"zones.json";zonepath.write_text(json.dumps(zones))
            result=root/"report.json"
            repo=Path(__file__).resolve().parents[1]
            subprocess.run([sys.executable,"-m","scripts.evaluate_generic_zone_events",
                "--run",str(root),"--reference",str(refpath),"--zones",str(zonepath),
                "--max-duration","5","--time-tolerance","0.1","--assume-aligned","--output",str(result)],
                cwd=repo,check=True,capture_output=True,text=True)
            report=json.loads(result.read_text())
            self.assertEqual(len(report["reference_flows"]),1)
            self.assertEqual(report["cameras"][0]["flows_with_reference_nearby"],1)
            self.assertEqual(report["cameras"][0]["flows"][0]["reference_candidates"][0]["id"],"8")
