"""归档保留分类目录及来源记录。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import manage, service, storage


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.inbox = root / 'inbox'
        self.library = root / 'library'
        self.inbox.mkdir()
        self.library.mkdir()
        self.workspace_patch = patch.object(storage, 'WORKSPACE_DIR', self.inbox)
        self.library_patch = patch.object(storage, 'LIBRARY_DIR', self.library)
        self.workspace_patch.start()
        self.library_patch.start()

    def tearDown(self):
        self.workspace_patch.stop()
        self.library_patch.stop()
        self.tmp.cleanup()

    def make(self, relative, content=b'%PDF-1.4\n%%EOF'):
        path = self.inbox / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_nested_pdf_keeps_structure_and_source(self):
        source = self.make('规划/项目A/report.pdf')
        sidecar = source.with_name('.report.pdf.source.json')
        sidecar.write_text(json.dumps({'title': '报告', 'source': 'https://example.com'}))
        result = service.keep('规划/项目A/report.pdf')
        self.assertEqual(result['file']['id'], '规划/项目A/report.pdf')
        self.assertEqual((self.library / result['file']['id']).read_bytes(), b'%PDF-1.4\n%%EOF')
        self.assertFalse(source.exists())
        self.assertFalse((self.inbox / '规划').exists())
        self.assertEqual(service.preview('library', result['file']['id'])['meta']['title'], '报告')

    def test_folder_merge_conflict_and_non_preview_files(self):
        self.make('规划/report.pdf')
        self.make('规划/子目录/note.txt', b'notes')
        self.make('规划/other.csv', b'a,b')
        destination = self.library / '规划/report.pdf'
        destination.parent.mkdir()
        destination.write_bytes(b'existing')
        result = service.batch('workspace', 'move_to_library', ['规划', '规划/other.csv'])
        self.assertEqual(set(result['succeeded']), {'规划/子目录/note.txt', '规划/other.csv'})
        self.assertEqual(len(result['failed']), 1)
        self.assertTrue((self.inbox / '规划/report.pdf').is_file())
        self.assertEqual(destination.read_bytes(), b'existing')
        self.assertEqual((self.library / '规划/子目录/note.txt').read_bytes(), b'notes')

    def test_same_name_in_different_folders(self):
        for directory in ['A', 'B']:
            self.make(f'{directory}/report.pdf')
            manage.keep(f'{directory}/report.pdf')
        self.assertTrue((self.library / 'A/report.pdf').is_file())
        self.assertTrue((self.library / 'B/report.pdf').is_file())

    def test_copy_failure_preserves_source(self):
        source = self.make('A/report.pdf')
        with patch('app.manage.shutil.copy2', side_effect=OSError('copy failed')):
            with self.assertRaises(ValueError):
                manage.keep('A/report.pdf')
        self.assertTrue(source.is_file())
        self.assertEqual(list(self.library.rglob('*.pdf')), [])
        self.assertEqual(list(self.library.rglob('.keep-*')), [])

    def test_target_symlink_escape_is_rejected(self):
        self.make('outside/report.pdf')
        (self.library / 'outside').symlink_to(self.inbox, target_is_directory=True)
        with self.assertRaises(ValueError):
            manage.keep('outside/report.pdf')
        self.assertTrue((self.inbox / 'outside/report.pdf').is_file())
