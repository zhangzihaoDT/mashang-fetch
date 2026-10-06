"""API 冒烟测试：直接使用 FastAPI TestClient，无需启动服务。"""
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import server
from app import storage
from app.preview import OUTPUT_DIR

client = TestClient(server.app)

SAMPLE = (
    "---\n"
    "title: 测试标题\n"
    "source: https://example.com\n"
    "author: 张三\n"
    "fetched_at: 2026-10-02T00:00:00.000Z\n"
    "format: markdown\n"
    "---\n\n"
    "# 正文\n\n你好。"
)


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.paths = []
        self.path = OUTPUT_DIR / "test_service_sample.md"
        self.path.write_text(SAMPLE, encoding="utf-8")
        self.paths.append(self.path)
        self.file_id = self.path.name
        self._library_dir = storage.LIBRARY_DIR
        self._tmp_library = Path(tempfile.mkdtemp(prefix="mashang-library-"))
        storage.LIBRARY_DIR = self._tmp_library

    def tearDown(self):
        storage.LIBRARY_DIR = self._library_dir
        shutil.rmtree(self._tmp_library, ignore_errors=True)
        for p in self.paths:
            Path(p).unlink(missing_ok=True)

    def test_formats(self):
        r = client.get("/api/formats")
        self.assertEqual(r.status_code, 200)
        values = {f["value"] for f in r.json()["formats"]}
        self.assertEqual(values, {"md", "csv"})

    def test_config_reports_both_scopes(self):
        r = client.get("/api/config")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["library_dir"], str(self._tmp_library))
        self.assertEqual(data["workspace_dir"], str(OUTPUT_DIR))

    def test_files_contains_sample(self):
        r = client.get("/api/files", params={"scope": "workspace"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        ids = {f["id"] for f in data["files"]}
        self.assertIn(self.file_id, ids)
        self.assertTrue(all(f["scope"] == "workspace" for f in data["files"]))

    def test_preview_markdown(self):
        r = client.get("/api/preview", params={"scope": "workspace", "id": self.file_id})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["kind"], "markdown")
        self.assertEqual(data["scope"], "workspace")
        self.assertEqual(data["title"], "测试标题")
        self.assertEqual(data["meta"]["author"], "张三")
        self.assertIn("你好", data["content"])
        self.assertFalse(data["content"].startswith("---"))

    def test_download(self):
        r = client.get("/api/download", params={"scope": "workspace", "id": self.file_id})
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r.headers.get("content-disposition", ""))

    def test_traversal_blocked(self):
        r = client.get("/api/preview", params={"scope": "workspace", "id": "../requirements.txt"})
        self.assertEqual(r.status_code, 400)

    def test_unknown_scope_rejected(self):
        r = client.get("/api/files", params={"scope": "nope"})
        self.assertEqual(r.status_code, 400)

    def test_fetch_requires_url(self):
        r = client.post("/api/fetch", json={"url": "   ", "format": "md"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["ok"])

    def test_rename_keeps_extension_and_content(self):
        r = client.post(
            "/api/rename",
            json={"scope": "workspace", "id": self.file_id, "name": "重命名样本"},
        )
        self.assertEqual(r.status_code, 200)
        new_id = r.json()["file"]["id"]
        new_path = OUTPUT_DIR / new_id
        self.paths.append(new_path)
        self.assertEqual(new_id, "重命名样本.md")
        self.assertTrue(new_path.is_file())
        self.assertFalse(self.path.exists())
        self.assertEqual(new_path.read_text(encoding="utf-8"), SAMPLE)

    def test_rename_rejects_conflict(self):
        other = OUTPUT_DIR / "test_service_other.md"
        other.write_text(SAMPLE, encoding="utf-8")
        self.paths.append(other)
        r = client.post(
            "/api/rename",
            json={"scope": "workspace", "id": self.file_id, "name": "test_service_other"},
        )
        self.assertEqual(r.status_code, 400)

    def test_delete_removes_file(self):
        r = client.post("/api/delete", json={"scope": "workspace", "id": self.file_id})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.path.exists())

    def test_keep_moves_to_library(self):
        r = client.post("/api/keep", json={"id": self.file_id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["file"]["scope"], "library")
        self.assertFalse(self.path.exists())
        self.assertTrue((self._tmp_library / self.file_id).is_file())

        listed = client.get("/api/files", params={"scope": "library"}).json()
        ids = {f["id"] for f in listed["files"]}
        self.assertIn(self.file_id, ids)

        preview = client.get(
            "/api/preview", params={"scope": "library", "id": self.file_id}
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["scope"], "library")

    def test_keep_conflict_keeps_source(self):
        (self._tmp_library / self.file_id).write_text("already here", encoding="utf-8")
        r = client.post("/api/keep", json={"id": self.file_id})
        self.assertEqual(r.status_code, 400)
        self.assertTrue(self.path.is_file())
        self.assertEqual(
            (self._tmp_library / self.file_id).read_text(encoding="utf-8"), "already here"
        )

    def test_manage_traversal_blocked(self):
        for path, body in (
            ("/api/keep", {"id": "../requirements.txt"}),
            ("/api/delete", {"scope": "workspace", "id": "../requirements.txt"}),
        ):
            r = client.post(path, json=body)
            self.assertEqual(r.status_code, 400)
        r = client.post(
            "/api/rename", json={"scope": "workspace", "id": "../requirements.txt", "name": "x"}
        )
        self.assertEqual(r.status_code, 400)

    def _extra(self, name):
        path = OUTPUT_DIR / name
        path.write_text(SAMPLE, encoding="utf-8")
        self.paths.append(path)
        return name

    def test_batch_move_to_library(self):
        second = self._extra("test_service_second.md")
        r = client.post(
            "/api/batch",
            json={"scope": "workspace", "action": "move_to_library", "ids": [self.file_id, second]},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(set(data["succeeded"]), {self.file_id, second})
        self.assertEqual(data["failed"], [])
        self.assertFalse(self.path.exists())
        self.assertTrue((self._tmp_library / self.file_id).is_file())
        self.assertTrue((self._tmp_library / second).is_file())

    def test_batch_move_reports_conflicts(self):
        second = self._extra("test_service_second.md")
        (self._tmp_library / second).write_text("already here", encoding="utf-8")
        r = client.post(
            "/api/batch",
            json={"scope": "workspace", "action": "move_to_library", "ids": [self.file_id, second]},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["succeeded"], [self.file_id])
        self.assertEqual([f["id"] for f in data["failed"]], [second])
        self.assertTrue((OUTPUT_DIR / second).is_file())

    def test_batch_delete(self):
        second = self._extra("test_service_second.md")
        r = client.post(
            "/api/batch",
            json={"scope": "workspace", "action": "delete", "ids": [self.file_id, second]},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()["succeeded"]), {self.file_id, second})
        self.assertFalse(self.path.exists())
        self.assertFalse((OUTPUT_DIR / second).exists())

    def test_batch_rejects_bad_action_and_empty(self):
        r = client.post(
            "/api/batch",
            json={"scope": "workspace", "action": "rename", "ids": [self.file_id]},
        )
        self.assertEqual(r.status_code, 400)
        r = client.post(
            "/api/batch",
            json={"scope": "workspace", "action": "delete", "ids": []},
        )
        self.assertEqual(r.status_code, 400)
        r = client.post(
            "/api/batch",
            json={"scope": "library", "action": "move_to_library", "ids": [self.file_id]},
        )
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
