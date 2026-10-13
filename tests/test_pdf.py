"""PDF downloads use a local HTTP fixture; no external network required."""
import json
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests.test_api import client
from app import storage

PDF = b'%PDF-1.4\n\x00\xff\n%%EOF\n'
ROOT = Path(__file__).resolve().parent.parent


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/download?id=1')
            self.end_headers()
            return
        if self.path in ('/page', '/multi'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            html = '<a href="/download?id=1">报告.pdf</a><a href="/download?id=1">重复.pdf</a>'
            if self.path == '/multi':
                html += '<a href="/html">坏附件.pdf</a>'
            self.wfile.write(html.encode())
            return
        status = 404 if self.path == '/missing' else 200
        self.send_response(status)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Disposition', "attachment; filename*=UTF-8''%E6%8A%A5%E5%91%8A.pdf")
        self.end_headers()
        self.wfile.write(b'<html>Error</html>' if self.path in ('/html', '/missing') else PDF)

    def log_message(self, *args):
        pass


class PdfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def cli(self, route, directory):
        proc = subprocess.run(['node', str(ROOT / 'src/cli.js'), self.url + route,
                               '--format', 'pdf', '--out', directory],
                              capture_output=True, text=True, timeout=15)
        return json.loads(proc.stdout), proc.returncode

    def test_redirect_binary_and_duplicate_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            first, code = self.cli('/redirect', directory)
            second, _ = self.cli('/redirect', directory)
            self.assertEqual(code, 0)
            self.assertEqual(first['format'], 'pdf')
            self.assertEqual(first['meta']['title'], '报告')
            self.assertEqual(Path(first['path']).read_bytes(), PDF)
            self.assertNotEqual(first['path'], second['path'])
            self.assertEqual(len(list(Path(directory).glob("*.pdf"))), 2)

    def test_invalid_content_and_http_error_leave_no_files(self):
        with tempfile.TemporaryDirectory() as directory:
            for route in ('/html', '/missing'):
                result, code = self.cli(route, directory)
                self.assertFalse(result['ok'])
                self.assertNotEqual(code, 0)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_api_fetch_list_preview_download_and_move(self):
        result = client.post('/api/fetch', json={'url': self.url + '/redirect', 'format': 'pdf'}).json()
        self.assertTrue(result['ok'], result)
        file_id = result['file']['id']
        original_library = storage.LIBRARY_DIR
        try:
            listed = client.get('/api/files').json()['files']
            self.assertIn(file_id, [f['id'] for f in listed])
            preview = client.get('/api/preview', params={'id': file_id}).json()
            self.assertEqual(preview['kind'], 'pdf')
            self.assertEqual(preview['meta']['download_url'], self.url + '/download?id=1')
            download = client.get('/api/download', params={'id': file_id})
            self.assertEqual(download.content, PDF)
            self.assertEqual(download.headers['content-type'], 'application/pdf')
            with tempfile.TemporaryDirectory() as directory:
                storage.LIBRARY_DIR = Path(directory)
                moved = client.post('/api/keep', json={'id': file_id}).json()
                self.assertTrue(moved['ok'])
                self.assertEqual((Path(directory) / file_id).read_bytes(), PDF)
                renamed = client.post('/api/rename', json={'scope': 'library', 'id': file_id, 'name': '已整理报告'}).json()['file']['id']
                preview = client.get('/api/preview', params={'scope': 'library', 'id': renamed}).json()
                self.assertEqual(preview['meta']['download_url'], self.url + '/download?id=1')
                client.post('/api/delete', json={'scope': 'library', 'id': renamed})
                self.assertEqual(list(Path(directory).iterdir()), [])
        finally:
            storage.LIBRARY_DIR = original_library
            Path(result['path']).unlink(missing_ok=True)
            Path(result['path']).with_name(f".{Path(result['path']).name}.source.json").unlink(missing_ok=True)

    def test_single_page_attachment_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            result, code = self.cli('/page', directory)
            self.assertEqual(code, 0)
            self.assertEqual(len(result['results']), 1)
            item = result['results'][0]
            self.assertEqual(item['meta']['source'], self.url + '/page')
            self.assertEqual(item['meta']['title'], '报告')
            self.assertEqual(Path(item['path']).read_bytes(), PDF)

    def test_multiple_attachments_selection_and_partial_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            result, code = self.cli('/multi', directory)
            self.assertTrue(result['needs_selection'])
            self.assertEqual(len(result['attachments']), 2)
            self.assertEqual(list(Path(directory).iterdir()), [])
            proc = subprocess.run(['node', str(ROOT / 'src/cli.js'), self.url + '/multi',
                                   '--format', 'pdf', '--out', directory, '--attachments',
                                   json.dumps([item['url'] for item in result['attachments']])],
                                  capture_output=True, text=True, timeout=15)
            downloaded = json.loads(proc.stdout)
            self.assertTrue(downloaded['ok'])
            self.assertEqual(len(downloaded['results']), 1)
            self.assertEqual(len(downloaded['failed']), 1)
            self.assertEqual(list(Path(directory).glob('*.part')), [])
