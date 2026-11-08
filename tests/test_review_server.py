from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from walkflows.review_server import RangeHandler
from walkflows.pipeline_runtime import pipeline_lock

class ReviewServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        Path(self.tmp.name,'video.mp4').write_bytes(b'0123456789')
        directory=self.tmp.name;self.lock=Path(directory)/'prepare.lock'
        self.server=ThreadingHTTPServer(('127.0.0.1',0),lambda *args,**kwargs: RangeHandler(*args,directory=directory,prepare_lock=self.lock,**kwargs))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}/video.mp4'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self, headers=None, method='GET'):
        return urlopen(Request(self.url,headers=headers or {},method=method))
    def test_full_and_range_requests(self):
        with self.request() as r: self.assertEqual((r.status,r.read()),(200,b'0123456789'))
        with self.request({'Range':'bytes=2-5'}) as r:
            self.assertEqual((r.status,r.headers['Content-Range'],r.headers['Content-Length'],r.read()),(206,'bytes 2-5/10','4',b'2345'))
        with self.request({'Range':'bytes=-3'}) as r:self.assertEqual(r.read(),b'789')
        with self.request({'Range':'bytes=8-'}) as r:self.assertEqual(r.read(),b'89')
        with self.request({'Range':'bytes=1-2'},'HEAD') as r:self.assertEqual((r.status,r.headers['Content-Length'],r.read()),(206,'2',b''))
    def test_unsatisfiable_range(self):
        with self.assertRaises(HTTPError) as raised:self.request({'Range':'bytes=20-30'})
        self.assertEqual(raised.exception.code,416)
        self.assertEqual(raised.exception.headers['Content-Range'],'bytes */10')

    def test_preparation_lock_temporarily_blocks_reads(self):
        with pipeline_lock(self.lock):
            with self.assertRaises(HTTPError) as raised:self.request()
            self.assertEqual(raised.exception.code,503)
            self.assertEqual(raised.exception.headers['Retry-After'],'1')
            with self.assertRaises(HTTPError) as head:self.request(method='HEAD')
            self.assertEqual(head.exception.code,503)
        with self.request({'Range':'bytes=0-1'}) as response:self.assertEqual(response.read(),b'01')
