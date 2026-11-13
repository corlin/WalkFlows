import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import cv2
import numpy as np

from walkflows.multicamera_preview import ffmpeg_executable
from walkflows.multicamera_processing import file_sha256
from walkflows.video_normalize import normalize_video, normalize_project
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

    def test_batch_preserves_camera_settings_and_records_source_chain(self):
        try: ffmpeg_executable()
        except (ValueError,OSError): self.skipTest("FFmpeg unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cameras=[]
            for name in ("front","back"):
                video=root/(name+".avi")
                writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),5,(64,48))
                if not writer.isOpened():self.skipTest("MJPG unavailable")
                for i in range(5):writer.write(np.full((48,64,3),i*30,np.uint8))
                writer.release()
                cameras.append({"id":name,"path":video.name,"offset_seconds":0.2,
                                "homography":[[1,0,0],[0,1,0],[0,0,1]]})
            config=root/"project.json";config.write_text(json.dumps({"name":"batch","cameras":cameras}))
            original={c["id"]:file_sha256(root/c["path"]) for c in cameras}
            destination=root/"converted"
            report=normalize_project(config,5,destination)
            self.assertEqual(report["status"],"completed")
            result=build_project(destination/"project.json")
            self.assertEqual(len(result["cameras"]),2)
            for camera in result["cameras"]:
                self.assertEqual(camera["offset_seconds"],0.2)
                self.assertEqual(camera["homography"],[[1,0,0],[0,1,0],[0,0,1]])
                self.assertEqual(camera["normalization"]["source_sha256"],original[camera["id"]])
            self.assertEqual(json.loads((destination/"state.json").read_text())["status"],"completed")
            with self.assertRaises(FileExistsError):normalize_project(config,5,destination)
            with self.assertRaisesRegex(ValueError,"already normalized"):
                normalize_project(destination/"project.json",5,root/"twice")
            self.assertFalse((root/"twice").exists())

    def test_batch_failure_does_not_publish_project(self):
        try: ffmpeg_executable()
        except (ValueError,OSError): self.skipTest("FFmpeg unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/"source.avi"
            writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),5,(64,48))
            if not writer.isOpened():self.skipTest("MJPG unavailable")
            for _ in range(2):writer.write(np.zeros((48,64,3),np.uint8))
            writer.release()
            config=root/"project.json"
            config.write_text(json.dumps({"cameras":[{"id":"a","path":"source.avi"},{"id":"b","path":"source.avi"}]}))
            destination=root/"failed"
            def fail_second(video,fps,bundle):
                if bundle.name=="b":raise ValueError("simulated failure")
                return normalize_video(video,fps,bundle)
            with patch("walkflows.video_normalize.normalize_video",side_effect=fail_second):
                with self.assertRaisesRegex(ValueError,"simulated"):
                    normalize_project(config,5,destination)
            self.assertFalse((destination/"project.json").exists())
            state=json.loads((destination/"state.json").read_text())
            self.assertEqual(state["status"],"failed")
            self.assertEqual([c["status"] for c in state["cameras"]],["completed","failed"])

    def test_rejects_invalid_target_fps_without_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):normalize_video(root/"unused",0,root/"result")
            self.assertFalse((root/"result").exists())


if __name__=="__main__":
    unittest.main()
