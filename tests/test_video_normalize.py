import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from walkflows.multicamera_preview import ffmpeg_executable
from walkflows.multicamera_processing import file_sha256
from walkflows.video_normalize import normalize_video
from walkflows.multicamera_project import build_project, apply_offsets
from walkflows.plane_calibration import apply_calibration


class NormalizeVideoTest(unittest.TestCase):
    def test_normalizes_variable_timestamps_without_overwriting_input(self):
        try: ffmpeg=ffmpeg_executable()
        except (ValueError,OSError): self.skipTest("FFmpeg unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/"base.avi";source=root/"vfr.mkv"
            writer=cv2.VideoWriter(str(base),cv2.VideoWriter_fourcc(*"MJPG"),10,(64,48))
            if not writer.isOpened():self.skipTest("MJPG unavailable")
            for i in range(12):writer.write(np.full((48,64,3),i*15,np.uint8))
            writer.release()
            subprocess.run([str(ffmpeg),"-hide_banner","-loglevel","error","-i",str(base),
                "-vf",r"setpts=(N+gte(N\,4)*4)/(10*TB)","-fps_mode","passthrough",
                "-c:v","libx264",str(source)],check=True,capture_output=True)
            original=file_sha256(source);output=root/"normalized"
            result=normalize_video(source,10,output)
            self.assertEqual(file_sha256(source),original)
            self.assertGreater(result["source"]["max_nominal_deviation_seconds"],.35)
            self.assertLess(result["output"]["max_nominal_deviation_seconds"],.001)
            self.assertGreater(result["output"]["frames"],result["source"]["frames"])
            self.assertEqual(result["output"]["sha256"],file_sha256(output/"normalized.mp4"))
            self.assertEqual(result["dimensions"],{"width":64,"height":48})
            self.assertEqual(json.loads((output/"state.json").read_text())["status"],"completed")
            project_path=root/"project.json"
            command=[sys.executable,"-m","walkflows","project-create","--name","test",
                     "--normalized-camera","a="+str(output),"--output",str(project_path)]
            subprocess.run(command,check=True,capture_output=True,text=True)
            project=build_project(project_path)
            provenance=project["cameras"][0]["normalization"]
            self.assertEqual(provenance["source_sha256"],original)
            self.assertEqual(provenance["output_sha256"],result["output"]["sha256"])
            self.assertEqual(provenance["manifest_sha256"],file_sha256(output/"manifest.json"))
            config=json.loads(project_path.read_text())
            config["cameras"][0]["normalization_manifest"]="normalized/manifest.json"
            project_path.write_text(json.dumps(config))
            offsets=root/"offsets.json";offsets.write_text(json.dumps({"offsets":{"a":0.1}}))
            changed=root/"nested";changed.mkdir()
            apply_offsets(project_path,offsets,changed/"timed.json")
            self.assertEqual(build_project(changed/"timed.json")["cameras"][0]["normalization"]["source_sha256"],original)
            points=root/"points.json"
            points.write_text(json.dumps({"image_points":[[0,0],[10,0],[10,10],[0,10]],
                                          "plane_points":[[0,0],[1,0],[1,1],[0,1]]}))
            apply_calibration(project_path,"a",points,changed/"mapped.json")
            self.assertEqual(build_project(changed/"mapped.json")["cameras"][0]["normalization"]["source_sha256"],original)
            state_path=output/"state.json"
            state_path.write_text(json.dumps({"status":"failed"}))
            with self.assertRaisesRegex(ValueError,"normalization"):
                build_project(project_path)
            state_path.write_text(json.dumps({"status":"completed"}))
            manifest_path=output/"manifest.json";manifest=json.loads(manifest_path.read_text())
            manifest["output"]["sha256"]="0"*64
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"normalization"):
                build_project(project_path)
            with self.assertRaises(FileExistsError):normalize_video(source,10,output)

    def test_rejects_invalid_target_fps_without_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):normalize_video(root/"unused",0,root/"result")
            self.assertFalse((root/"result").exists())


if __name__=="__main__":
    unittest.main()
