"""读取本地文件并按类型准备 Preview 数据。"""
import csv
import json
from pathlib import Path

from app.storage import OUTPUT_DIR

PREVIEWABLE_EXTS = {".md", ".csv", ".json"}


def list_outputs(out_dir=None):
    """列出目录下可预览的文件，最新的在前。默认列出 Inbox（output/）。"""
    out_dir = Path(out_dir) if out_dir else OUTPUT_DIR
    if not out_dir.exists():
        return []
    files = [p for p in out_dir.rglob("*") if p.is_file() and p.suffix.lower() in PREVIEWABLE_EXTS]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [(str(p.relative_to(out_dir)), str(p)) for p in files]


def parse_front_matter(text):
    """解析 .md 文件头部的 YAML front matter，返回 (meta dict, 正文)。"""
    meta = {}
    if not text.startswith("---"):
        return meta, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return meta, text
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            value = value.strip().strip('"')
            meta[key.strip()] = value
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return meta, body


def describe(path):
    """生成 Preview 元信息文本。"""
    p = Path(path)
    if not p.exists():
        return ""
    size_kb = p.stat().st_size / 1024
    lines = [f"**{p.name}** · {p.suffix.lstrip('.').upper()} · {size_kb:.1f} KB"]
    if p.suffix.lower() == ".md":
        meta, _ = parse_front_matter(p.read_text(encoding="utf-8", errors="ignore"))
        for key in ("title", "author", "source", "fetched_at"):
            if meta.get(key):
                lines.append(f"- {key}: {meta[key]}")
    return "\n".join(lines)


def load(path):
    """加载文件，返回 {'kind': ..., 'content'/'rows'/'header': ...}。"""
    p = Path(path)
    if not p.exists():
        return {"kind": "error", "error": f"文件不存在: {path}"}

    ext = p.suffix.lower()
    if ext == ".md":
        return {"kind": "markdown", "content": p.read_text(encoding="utf-8", errors="ignore")}
    if ext == ".csv":
        with p.open(encoding="utf-8", errors="ignore", newline="") as f:
            rows = [row for row in csv.reader(f) if row]
        if not rows:
            return {"kind": "markdown", "content": "*（空表格）*"}
        header, body = rows[0], rows[1:]
        return {"kind": "table", "header": header, "rows": body}
    if ext == ".json":
        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        return {"kind": "json", "content": json.dumps(data, ensure_ascii=False, indent=2)}
    return {"kind": "text", "content": p.read_text(encoding="utf-8", errors="ignore")}
