import unittest
import subprocess
import tempfile
from pathlib import Path
import cv2
import numpy as np
from walkflows.multicamera_preview import ffmpeg_executable
from walkflows.video_timing import compare_timing, audit_video_timing


class VideoTimingTest(unittest.TestCase):
    def test_real_variable_timestamps_with_matching_frame_count_and_fps(self):
        try:
            ffmpeg=ffmpeg_executable()
        except (ValueError,OSError):
            self.skipTest("FFmpeg is not available")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/"constant.avi";vfr=root/"irregular.mkv"
            writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*"MJPG"),10,(64,48))
            if not writer.isOpened():self.skipTest("MJPG encoder is not available")
            for i in range(12):writer.write(np.full((48,64,3),i*15,dtype=np.uint8))
            writer.release()
            subprocess.run([str(ffmpeg),"-hide_banner","-loglevel","error","-i",str(source),
                "-vf",r"setpts=(N+gte(N\,4)*4)/(10*TB)","-fps_mode","passthrough",
                "-c:v","libx264",str(vfr)],check=True,capture_output=True)
            result=audit_video_timing(vfr,source)
            self.assertEqual(result["frames"],12)
            self.assertAlmostEqual(result["nominal_fps"],10)
            self.assertAlmostEqual(result["max_nominal_deviation_seconds"],.4,places=5)
            self.assertAlmostEqual(result["max_preview_deviation_seconds"],.4,places=5)

    def test_constant_rate_and_preview_offset_are_normalized(self):
        report=compare_timing([2.,2.1,2.2],10.,[7.,7.1,7.2])
        self.assertAlmostEqual(report["max_nominal_deviation_seconds"],0.)
        self.assertAlmostEqual(report["max_preview_deviation_seconds"],0.)
        self.assertEqual(report["frames"],3)

    def test_irregular_and_misaligned_timestamps_are_reported(self):
        report=compare_timing([0.,.1,.4],10.,[0.,.1,.2])
        self.assertAlmostEqual(report["max_nominal_deviation_seconds"],.2)
        self.assertAlmostEqual(report["max_preview_deviation_seconds"],.2)

    def test_rejects_invalid_and_mismatched_timestamps(self):
        for source,fps,preview in [([],10,None),([0,0],10,None),([0,float("nan")],10,None),
                                    ([0,1],0,None),([0,1],1,[0])]:
            with self.subTest(source=source,fps=fps,preview=preview):
                with self.assertRaises(ValueError):compare_timing(source,fps,preview)


if __name__=="__main__":
    unittest.main()
