"""工作区文件管理：Keep / Rename / Delete。

- Keep：把 Inbox（workspace）内的文件**移动**到资料库（library），即空间之间的转移。
- Rename / Delete：作用于指定 scope（workspace 或 library）。

所有动作都拒绝越界访问；Keep 目标已存在同名文件时不覆盖、不创建副本，直接报错。
"""
import os
import re
import shutil
import tempfile
from pathlib import Path

from app import storage

_ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _clean_name(name):
    """清洗用户输入的文件名，拒绝空名与路径分隔符。"""
    cleaned = _ILLEGAL.sub("_", (name or "").strip()).strip(" .")
    if not cleaned or cleaned in (".", ".."):
        raise ValueError("文件名无效")
    return cleaned


def rename(scope, file_id, new_name):
    """重命名指定空间的文件，保留原扩展名，返回新路径。"""
    src = storage.resolve(scope, file_id)
    if not src.is_file():
        raise ValueError("文件不存在")

    base = _clean_name(new_name)
    if src.suffix and base.lower().endswith(src.suffix.lower()):
        base = base[: -len(src.suffix)].strip(" .")
        if not base:
            raise ValueError("文件名无效")

    dst = src.with_name(base + src.suffix)
    if dst == src:
        return src
    if dst.exists():
        raise ValueError("同名文件已存在")
    src.rename(dst)
    _move_source(src, dst)
    sidecar = dst.with_name(f".{dst.name}.source.json")
    if dst.suffix.lower() == ".pdf" and sidecar.is_file():
        import json
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        meta["title"] = base
        sidecar.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return dst


def delete(scope, file_id):
    """永久删除指定空间的文件，返回被删除的路径。"""
    path = storage.resolve(scope, file_id)
    if not path.is_file():
        raise ValueError("文件不存在")
    path.unlink()
    path.with_name(f".{path.name}.source.json").unlink(missing_ok=True)
    return path


def keep(file_id):
    """保留相对目录归档，目标存在时不覆盖，失败时保留源文件。"""
    src = storage.resolve(storage.WORKSPACE, file_id)
    if not src.is_file():
        raise ValueError("文件不存在")
    relative = src.relative_to(storage.WORKSPACE_DIR.resolve())
    dst = storage.resolve(storage.LIBRARY, str(relative))
    source_meta = src.with_name(f".{src.name}.source.json")
    target_meta = dst.with_name(f".{dst.name}.source.json")
    if dst.exists() or target_meta.exists():
        raise ValueError(f"资料库已存在同名文件：{relative}")
    tmp = None
    created = False
    meta_created = False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".keep-", dir=str(dst.parent))
        os.close(fd)
        tmp = Path(tmp_name)
        shutil.copy2(src, tmp)
        # 原子创建目标；并发出现同名文件时也不会覆盖。
        os.link(tmp, dst)
        created = True
        if source_meta.is_file():
            with target_meta.open("xb") as output:
                meta_created = True
                output.write(source_meta.read_bytes())
        src.unlink()
    except OSError as exc:
        if created:
            dst.unlink(missing_ok=True)
        if meta_created:
            target_meta.unlink(missing_ok=True)
        raise ValueError(f"移入资料库失败：{relative}（{exc.strerror or str(exc)}）") from exc
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)
    source_meta.unlink(missing_ok=True)
    # 只清理本次移动后空出的父目录，Inbox 根目录始终保留。
    parent = src.parent
    root = storage.WORKSPACE_DIR.resolve()
    while parent != root:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent
    return dst


def _move_source(src, dst):
    sidecar = src.with_name(f".{src.name}.source.json")
    if sidecar.is_file():
        shutil.move(str(sidecar), str(dst.with_name(f".{dst.name}.source.json")))
