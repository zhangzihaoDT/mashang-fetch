"""Bounded raw-file import into Inbox; never overwrite existing files."""
import re
import uuid
from pathlib import Path
from app import storage, service

MAX_UPLOAD = 25 * 1024 * 1024
ALLOWED = {".pdf", ".md", ".csv", ".txt", ".json"}


def import_file(name, data):
    name = Path(name.replace("\\", "/")).name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED:
        raise ValueError("支持 PDF、Markdown、CSV、TXT 和 JSON")
    if not data or len(data) > MAX_UPLOAD:
        raise ValueError("文件不能为空，且不得超过 25 MB")
    if suffix == ".pdf" and not data.startswith(b"%PDF-"):
        raise ValueError("文件不是有效的 PDF")
    if suffix != ".pdf":
        try:
            text = data.decode("utf-8-sig")
            if suffix == ".json":
                import json
                json.loads(text)
        except (UnicodeError, ValueError):
            raise ValueError("文本文件须为 UTF-8 编码；JSON 须格式有效") from None
    stem = re.sub(r'[\x00-\x1f/:*?"<>|]', "_", Path(name).stem).strip(". ")[:100] or "资料"
    directory = storage.dir_for("workspace")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{stem}_{uuid.uuid4().hex[:12]}{suffix}"
    with target.open("xb") as handle:
        handle.write(data)
    return {"ok": True, "file": service.file_record(target, "workspace")}
