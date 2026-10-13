"""API 服务层：把核心能力整理成 JSON 友好的结构。

Inbox（workspace）→ 资料库（library）
Fetch / Convert → Preview → Keep / Rename / Delete / Download
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app import manage, storage
from app.fetch import fetch
from app.preview import OUTPUT_DIR, load, list_outputs, parse_front_matter

SCOPES = storage.SCOPES


def _check_scope(scope):
    if scope not in SCOPES:
        raise ValueError("未知文件空间")
    return scope


def resolve_id(scope, file_id):
    """把前端传来的 id 解析为指定空间内的绝对路径，拒绝越界访问。"""
    return storage.resolve(_check_scope(scope), file_id)


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
    if p.suffix.lower() == ".pdf":
        try:
            meta = json.loads(p.with_name(f".{p.name}.source.json").read_text(encoding="utf-8"))
            if meta.get("title"):
                return meta["title"]
        except (OSError, ValueError):
            pass
    return p.stem


def file_record(path, scope):
    """文件列表 / 预览头部的结构化记录。"""
    p = Path(path)
    base = storage.dir_for(scope).resolve()
    try:
        file_id = str(p.resolve().relative_to(base))
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
        "scope": scope,
        "title": _title(path),
        "format": p.suffix.lstrip(".").lower(),
        "size": size,
        "mtime": _iso(mtime) if mtime else None,
    }


def list_files(scope="workspace"):
    scope = _check_scope(scope)
    return [file_record(path, scope) for _, path in list_outputs(storage.dir_for(scope))]


def fetch_url(url, fmt="md", attachments=None):
    result = fetch(url, fmt, attachments=attachments)
    if result.get("ok") and not result.get("needs_selection"):
        if "results" in result:
            result["files"] = [file_record(item["path"], storage.WORKSPACE) for item in result["results"]]
            result["file"] = result["files"][0]
        else:
            result["file"] = file_record(result["path"], storage.WORKSPACE)
    return result


def config():
    """运行配置：两个空间的目录。"""
    return {
        "workspace_dir": str(storage.WORKSPACE_DIR),
        "library_dir": str(storage.LIBRARY_DIR),
    }


def open_inbox(scope="workspace", file_id=None):
    """在本机 Finder 打开固定的抓取输出目录。"""
    if sys.platform != "darwin":
        raise ValueError("Finder 入口仅支持 macOS")
    directory = storage.dir_for(_check_scope(scope)).resolve()
    target = resolve_id(scope, file_id) if file_id is not None else directory
    if file_id is not None and not target.is_file():
        raise ValueError("文件不存在")
    directory.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["/usr/bin/open", "-R", str(target)] if file_id is not None else ["/usr/bin/open", str(directory)], check=True,
                       capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("无法打开 Finder，请按显示的路径手动打开文件夹") from exc
    return {"ok": True, "path": str(directory)}


def rename(scope, file_id, name):
    """重命名指定空间的文件，返回新的文件记录。"""
    scope = _check_scope(scope)
    path = manage.rename(scope, file_id, name)
    return {"file": file_record(path, scope)}


def delete(scope, file_id):
    """永久删除指定空间的文件。"""
    scope = _check_scope(scope)
    manage.delete(scope, file_id)
    return {"ok": True}


def keep(file_id):
    """把 Inbox 文件移动（转移）到资料库，返回新的文件记录。"""
    dst = manage.keep(file_id)
    return {
        "ok": True,
        "name": dst.name,
        "path": str(dst),
        "scope": storage.LIBRARY,
        "library_dir": str(storage.LIBRARY_DIR),
        "file": file_record(dst, storage.LIBRARY),
    }


def batch(scope, action, ids):
    """批量文件操作：逐项执行，返回成功与失败清单。

    action: "delete" | "move_to_library"
    单个文件失败不影响其他文件，便于文件整理场景。
    """
    scope = _check_scope(scope)
    if action not in ("delete", "move_to_library"):
        raise ValueError("不支持的操作")
    if action == "move_to_library" and scope != storage.WORKSPACE:
        raise ValueError("只有 Inbox 可以移入资料库")
    if not ids:
        raise ValueError("未选择文件")

    succeeded, failed = [], []
    expanded = []
    for file_id in ids:
        try:
            path = resolve_id(scope, file_id)
            if action == "move_to_library" and path.is_dir():
                if path == storage.WORKSPACE_DIR.resolve():
                    raise ValueError("请选择具体文件夹")
                files = sorted(p for p in path.rglob("*") if p.is_file()
                               and not p.name.startswith("."))
                if not files:
                    raise ValueError("文件夹中没有可移入的文件")
                expanded.extend(str(p.relative_to(storage.WORKSPACE_DIR.resolve())) for p in files)
            else:
                expanded.append(file_id)
        except ValueError as exc:
            failed.append({"id": file_id, "error": str(exc)})
    for file_id in dict.fromkeys(expanded):
        try:
            if action == "delete":
                manage.delete(scope, file_id)
            else:
                manage.keep(file_id)
            succeeded.append(file_id)
        except ValueError as exc:
            failed.append({"id": file_id, "error": str(exc)})

    return {
        "ok": True,
        "scope": scope,
        "action": action,
        "succeeded": succeeded,
        "failed": failed,
    }


def preview(scope, file_id):
    scope = _check_scope(scope)
    path = resolve_id(scope, file_id)
    data = load(str(path))
    record = file_record(path, scope)
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
    elif kind == "pdf":
        sidecar = Path(path).with_name(f".{Path(path).name}.source.json")
        if sidecar.is_file():
            try:
                record["meta"] = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
    elif kind in ("json", "text"):
        record["content"] = data.get("content", "")
    else:
        record["error"] = data.get("error", "无法预览该文件")

    return record
