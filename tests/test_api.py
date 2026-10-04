"""API 冒烟测试：直接使用 FastAPI TestClient，无需启动服务。"""
import unittest

from fastapi.testclient import TestClient

import server
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
        self.path = OUTPUT_DIR / "test_service_sample.md"
        self.path.write_text(SAMPLE, encoding="utf-8")
        self.file_id = self.path.name

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_formats(self):
        r = client.get("/api/formats")
        self.assertEqual(r.status_code, 200)
        values = {f["value"] for f in r.json()["formats"]}
        self.assertEqual(values, {"md", "csv"})

    def test_files_contains_sample(self):
        r = client.get("/api/files")
        self.assertEqual(r.status_code, 200)
        ids = {f["id"] for f in r.json()["files"]}
        self.assertIn(self.file_id, ids)

    def test_preview_markdown(self):
        r = client.get("/api/preview", params={"id": self.file_id})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["kind"], "markdown")
        self.assertEqual(data["title"], "测试标题")
        self.assertEqual(data["meta"]["author"], "张三")
        self.assertIn("你好", data["content"])
        self.assertFalse(data["content"].startswith("---"))

    def test_download(self):
        r = client.get("/api/download", params={"id": self.file_id})
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r.headers.get("content-disposition", ""))

    def test_traversal_blocked(self):
        r = client.get("/api/preview", params={"id": "../requirements.txt"})
        self.assertEqual(r.status_code, 400)

    def test_fetch_requires_url(self):
        r = client.post("/api/fetch", json={"url": "   ", "format": "md"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["ok"])


if __name__ == "__main__":
    unittest.main()
