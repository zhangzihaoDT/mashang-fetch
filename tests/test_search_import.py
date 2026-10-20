import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.search import search
from app.imports import import_file


class SearchImportTests(unittest.TestCase):

    def test_missing_key(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ValueError, '搜索尚未启用'):
                search('Tesla')

    def test_import_no_overwrite_or_escape(self):
        with tempfile.TemporaryDirectory() as directory, patch('app.storage.WORKSPACE_DIR', Path(directory)):
            a = import_file('../../hello.md', b'# hello')
            b = import_file('../../hello.md', b'# again')
            self.assertNotEqual(a['file']['id'], b['file']['id'])
            self.assertEqual(len(list(Path(directory).iterdir())), 2)
            for path in Path(directory).iterdir():
                self.assertEqual(path.parent, Path(directory))

    def test_import_reject_invalid_content(self):
        for name, content in [('bad.pdf', b'<html>'), ('bad.json', b'{'), ('bad.txt', b'\xff'), ('bad.exe', b'x')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                import_file(name, content)

    def test_import_api_then_preview(self):
        from fastapi.testclient import TestClient
        from server import app
        with tempfile.TemporaryDirectory() as directory, patch('app.storage.WORKSPACE_DIR', Path(directory)):
            client = TestClient(app)
            response = client.post('/api/import?name=sample.md', content=b'# Imported document')
            self.assertEqual(response.status_code, 200)
            file_id = response.json()['file']['id']
            preview = client.get('/api/preview', params={'scope': 'workspace', 'id': file_id})
            self.assertEqual(preview.status_code, 200)
            self.assertIn('Imported document', preview.json()['content'])
            self.assertEqual(client.post('/api/import?name=bad.pdf', content=b'bad').status_code, 400)

    def test_search_api_missing_config(self):
        from fastapi.testclient import TestClient
        from server import app
        with patch.dict('os.environ', {}, clear=True):
            response = TestClient(app).post('/api/search', json={'query': 'Tesla'})
            self.assertEqual(response.status_code, 400)
            self.assertIn('搜索尚未启用', response.json()['detail'])
