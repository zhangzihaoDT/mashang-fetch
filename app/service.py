"""API 服务层：把核心能力整理成 JSON 友好的结构。

Link → File → Preview → Download
"""
from datetime import datetime
from pathlib import Path

from app.fetch import fetch
from app.preview import OUTPUT_DIR, load, list_outputs, parse_front_matter


def resolve_id(file_id):
    """把前端传来的 id 解析为 output 目录内的绝对路径，拒绝越界访问。"""
    base = OUTPUT_DIR.resolve()
    target = (base / file_id).resolve()
    if target != base and base not in target.parents:
        raise ValueError("非法路径")
    return target


def _iso(ts):
    return datetime.fromtimestamp(ts).isoformat()


def _human_time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime(
            "%Y-%m-%d %H:%M"
        )
    except (ValueError, AttributeError):
        return value


def _title(path):
    """Markdown 取 front matter 的 title，其余回退到文件名。"""
    p = Path(path)
    if p.suffix.lower() == ".md":
        try:
            meta, _ = parse_front_matter(p.read_text(encoding="utf-8", errors="ignore"))
            if meta.get("title"):
                return meta["title"]
        except OSError:
            pass
    return p.stem


def file_record(path):
    """文件列表 / 预览头部的结构化记录。"""
    p = Path(path)
    try:
        file_id = str(p.resolve().relative_to(OUTPUT_DIR.resolve()))
    except ValueError:
        file_id = p.name
    try:
        st = p.stat()
        size, mtime = st.st_size, st.st_mtime
    except OSError:
        size, mtime = 0, 0
    return {
        "id": file_id,
        "name": p.name,
        "title": _title(path),
        "format": p.suffix.lstrip(".").lower(),
        "size": size,
        "mtime": _iso(mtime) if mtime else None,
    }


def list_files():
    return [file_record(path) for _, path in list_outputs()]


def fetch_url(url, fmt="md"):
    result = fetch(url, fmt)
    if result.get("ok"):
        result["file"] = file_record(result["path"])
    return result


def preview(file_id):
    path = resolve_id(file_id)
    data = load(str(path))
    record = file_record(path)
    kind = data.get("kind")
    record["kind"] = kind
    record["meta"] = {}

    if kind == "markdown":
        meta, body = parse_front_matter(data["content"])
        record["title"] = meta.get("title") or record["title"]
        record["meta"] = {
            "source": meta.get("source"),
            "author": meta.get("author"),
            "fetched_at": _human_time(meta["fetched_at"]) if meta.get("fetched_at") else None,
        }
        record["content"] = body
    elif kind == "table":
        record["header"] = data["header"]
        record["rows"] = data["rows"]
    elif kind in ("json", "text"):
        record["content"] = data.get("content", "")
    else:
        record["error"] = data.get("error", "无法预览该文件")

    return record
