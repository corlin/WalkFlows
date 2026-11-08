from pathlib import Path
from unittest import TestCase
import json,subprocess,sys

class LocalCliTest(TestCase):
    def test_status_is_machine_readable_and_uses_project_environment(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,'-m','walkflows','status','--json'],cwd=root,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        status=json.loads(result.stdout)
        self.assertTrue(status['environment']['using_project_venv'])
        self.assertEqual(status['assets']['total'],len(status['assets']['issues'])+status['assets']['ready'])
        self.assertIn('not validated',status['scope'])
