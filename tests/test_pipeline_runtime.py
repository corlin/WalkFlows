from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import hashlib,json,sys
from walkflows.pipeline_runtime import Asset,check_assets,fingerprint,run_steps,pipeline_lock

class PipelineRuntimeTest(TestCase):
    def test_asset_inventory_detects_missing_and_corruption(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'asset.bin';data=b'abc';digest=hashlib.sha256(data).hexdigest()
            specs=[Asset('asset.bin','sha256',digest,3)]
            self.assertEqual(check_assets(root,specs)[0]['state'],'missing')
            path.write_bytes(data);self.assertEqual(check_assets(root,specs)[0]['state'],'ready')
            path.write_bytes(b'bad');self.assertEqual(check_assets(root,specs)[0]['state'],'mismatch')
    def test_fingerprint_tracks_source_changes(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'walkflows').mkdir();p=root/'walkflows/a.py';p.write_text('a')
            first=fingerprint(root);p.write_text('b');self.assertNotEqual(first,fingerprint(root))
    def test_failed_stage_stops_following_stage_and_records_exit(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);journal=root/'state.json';marker=root/'marker'
            steps=[('fail',[sys.executable,'-c','raise SystemExit(7)']),('later',[sys.executable,'-c',f'open({str(marker)!r},"w").write("x")'])]
            self.assertEqual(run_steps(root,steps,journal),7)
            self.assertFalse(marker.exists());report=json.loads(journal.read_text());self.assertEqual(report['status'],'failed');self.assertEqual(report['steps'][0]['exit_code'],7)
    def test_lock_rejects_competing_preparation(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'prepare.lock'
            with pipeline_lock(path):
                with self.assertRaises(BlockingIOError):
                    with pipeline_lock(path):pass
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from walkflows.pipeline_runtime import bundle_fingerprint,manifest_current

class PipelineManifestTest(TestCase):
    def test_manifest_detects_changed_source_and_bundle(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'walkflows').mkdir();source=root/'walkflows/x.py';source.write_text('v1');bundle=root/'index.html';bundle.write_text('first')
            from walkflows.pipeline_runtime import fingerprint
            report={'status':'passed','source_fingerprint':fingerprint(root),'bundle_fingerprint':bundle_fingerprint(root,['index.html']),'packages':{'sample':'1'}}
            self.assertTrue(manifest_current(root,report,['index.html'],{'sample':'1'}))
            bundle.write_text('different');self.assertFalse(manifest_current(root,report,['index.html'],{'sample':'1'}))
            bundle.write_text('first');source.write_text('v2');self.assertFalse(manifest_current(root,report,['index.html'],{'sample':'1'}))
    def test_missing_bundle_never_matches(self):
        with TemporaryDirectory() as tmp:
            self.assertIsNone(bundle_fingerprint(Path(tmp),['absent.html']))
            self.assertFalse(manifest_current(Path(tmp),{'status':'passed'},['absent.html'],{}))
from walkflows.pipeline_runtime import fail_journal

class JournalFinalizationTest(TestCase):
    def test_failed_finalization_updates_existing_successful_stage_journal(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'state.json';p.write_text(json.dumps({'status':'passed','steps':[{'name':'verify','status':'passed'}]}))
            fail_journal(p,'bundle changed')
            result=json.loads(p.read_text());self.assertEqual(result['status'],'failed');self.assertEqual(result['error'],'bundle changed');self.assertEqual(result['steps'][0]['name'],'verify')
from unittest import skipUnless
import os,signal,subprocess,time

@skipUnless(os.name=='posix','POSIX process groups required')
class PipelineInterruptTest(TestCase):
    def test_interrupt_stops_owned_stage_and_records_interruption(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);marker=root/'pid';journal=root/'state.json'
            stage='import os,time;open('+repr(str(marker))+',"w").write(str(os.getpid()));time.sleep(30)'
            controller='from walkflows.pipeline_runtime import run_steps;import sys;run_steps('+repr(str(root))+',[("wait",[sys.executable,"-c",'+repr(stage)+'])],'+repr(str(journal))+')'
            project=Path(__file__).resolve().parents[1];env=os.environ.copy();env['PYTHONPATH']=str(project)
            process=subprocess.Popen([sys.executable,'-c',controller],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            child=None
            try:
                deadline=time.monotonic()+5
                while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.05)
                self.assertTrue(marker.exists(),'stage did not start');child=int(marker.read_text());process.send_signal(signal.SIGINT);process.wait(timeout=5)
                self.assertEqual(json.loads(journal.read_text())['status'],'interrupted')
                with self.assertRaises(ProcessLookupError):os.kill(child,0)
            finally:
                if process.poll() is None:process.kill();process.wait()
                if child is not None:
                    try:os.kill(child,signal.SIGKILL)
                    except ProcessLookupError:pass
from walkflows.pipeline_runtime import preparation_busy
import fcntl

class LockStateTest(TestCase):
    def test_readers_are_not_misreported_as_active_preparation(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'prepare.lock';path.touch()
            with path.open('r') as reader:
                fcntl.flock(reader,fcntl.LOCK_SH|fcntl.LOCK_NB)
                self.assertFalse(preparation_busy(path))
                fcntl.flock(reader,fcntl.LOCK_UN)
            with pipeline_lock(path):self.assertTrue(preparation_busy(path))
            self.assertFalse(preparation_busy(path))
from walkflows.pipeline_runtime import wait_for_readers_lock
import threading

class ReaderCoordinationTest(TestCase):
    def test_preparation_waits_briefly_for_active_reader(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'prepare.lock';path.touch();ready=threading.Event()
            def reader():
                with path.open('r') as f:
                    fcntl.flock(f,fcntl.LOCK_SH);ready.set();time.sleep(.15);fcntl.flock(f,fcntl.LOCK_UN)
            thread=threading.Thread(target=reader);thread.start();self.assertTrue(ready.wait(2))
            with wait_for_readers_lock(path,timeout=2):self.assertTrue(preparation_busy(path))
            thread.join(timeout=2);self.assertFalse(thread.is_alive())
    def test_running_preparation_is_not_restarted(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'prepare.lock'
            with pipeline_lock(path):
                started=time.monotonic()
                with self.assertRaises(BlockingIOError):
                    with wait_for_readers_lock(path,timeout=2):pass
                self.assertLess(time.monotonic()-started,1)
