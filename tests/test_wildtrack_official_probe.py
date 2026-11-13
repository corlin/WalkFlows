import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.probe_wildtrack_official import match_counts


class WildtrackProbeTest(unittest.TestCase):
    def test_selected_frame_rejects_missing_inputs_before_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"manifest.json").write_text(json.dumps({"files":[]}))
            proc=subprocess.run([sys.executable,"-m","scripts.probe_wildtrack_official",
                "--directory",str(root),"--weights",str(root/"unused.pt"),
                "--output",str(root/"report.json"),"--frame","500"],capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn("annotations_positions/00000500.json",proc.stderr)
            self.assertFalse((root/"report.json").exists())

    def test_matches_are_one_to_one_and_respect_threshold(self):
        reference=[[0,0,10,10],[20,20,30,30]]
        self.assertEqual(match_counts([[0,0,10,10],[0,0,10,10]],reference,.5),1)
        self.assertEqual(match_counts([[0,0,10,10],[20,20,30,30]],reference,.5),2)
        self.assertEqual(match_counts([[100,100,110,110]],reference,.5),0)
        self.assertEqual(match_counts([],reference,.5),0)


if __name__=="__main__":
    unittest.main()
