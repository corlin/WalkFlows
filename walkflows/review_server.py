"""Loopback-only static review server with single-range video seeking."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import fcntl
import os
import re
import shutil

class RangeHandler(SimpleHTTPRequestHandler):
    def __init__(self,*args,prepare_lock=None,**kwargs):
        self.prepare_lock=Path(prepare_lock) if prepare_lock is not None else None
        super().__init__(*args,**kwargs)

    def _guarded(self,operation):
        if self.prepare_lock is None:return operation()
        try:lock=self.prepare_lock.open('a+')
        except OSError:
            self.send_error(503,'Review lock unavailable');return
        with lock:
            try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError:
                body=b'WalkFlows preparation is in progress; retry after it finishes.\n'
                self.send_response(503,'Preparation in progress');self.send_header('Content-Type','text/plain; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Retry-After','1');self.end_headers()
                if self.command!='HEAD':self.wfile.write(body)
                return
            except OSError:
                self.send_error(503,'Review lock unavailable');return
            try:return operation()
            finally:fcntl.flock(lock,fcntl.LOCK_UN)

    def do_GET(self):return self._guarded(super().do_GET)
    def do_HEAD(self):return self._guarded(super().do_HEAD)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store, max-age=0')
        super().end_headers()

    def send_head(self):
        # Different local runs can reuse the same URL and have older mtimes.
        # Never answer a conditional request with a stale cached representation.
        for name in ("If-Modified-Since", "If-None-Match"):
            if name in self.headers:
                del self.headers[name]
        self._byte_count = None
        header = self.headers.get('Range')
        # If-Range or multi-range requests are safely served as full responses.
        if not header or self.headers.get('If-Range') or ',' in header:
            return super().send_head()
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
        if not match or not any(match.groups()):
            return super().send_head()
        try:
            file = open(path, 'rb')
        except OSError:
            self.send_error(404, 'File not found')
            return None
        size = os.fstat(file.fileno()).st_size
        first, last = match.groups()
        if not first:
            suffix = int(last)
            start, end = max(0, size - suffix), size - 1
        else:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        if start >= size or start > end:
            file.close()
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        self._byte_count = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(self._byte_count))
        self.send_header('Last-Modified', self.date_time_string(os.fstat(file.fileno()).st_mtime))
        self.end_headers()
        file.seek(start)
        return file

    def copyfile(self, source, outputfile):
        if self._byte_count is None:
            return shutil.copyfileobj(source, outputfile)
        remaining = self._byte_count
        while remaining:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

def main():
    parser=argparse.ArgumentParser(description='Serve WalkFlows locally with video range support')
    parser.add_argument('--directory', default='data/processed/local-review')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--prepare-lock', default=None, help='coordinate reads with a preparation lock')
    args=parser.parse_args()
    directory=Path(args.directory).resolve(strict=True)
    if not directory.is_dir(): parser.error('directory must be a directory')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),lambda *a,**kw: RangeHandler(*a,directory=str(directory),prepare_lock=args.prepare_lock,**kw))
    print(f'WalkFlows: http://127.0.0.1:{server.server_port}/',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
