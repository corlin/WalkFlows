import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from walkflows.multicamera_preview import ffmpeg_executable
from walkflows.multicamera_processing import file_sha256
from walkflows.video_normalize import normalize_video


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
            with self.assertRaises(FileExistsError):normalize_video(source,10,output)

    def test_rejects_invalid_target_fps_without_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):normalize_video(root/"unused",0,root/"result")
            self.assertFalse((root/"result").exists())


if __name__=="__main__":
    unittest.main()
