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
    return dst


def delete(scope, file_id):
    """永久删除指定空间的文件，返回被删除的路径。"""
    path = storage.resolve(scope, file_id)
    if not path.is_file():
        raise ValueError("文件不存在")
    path.unlink()
    return path


def keep(file_id):
    """把 Inbox 文件移动（转移）到资料库，返回目标路径。

    同名文件已存在时不覆盖、不创建副本，直接报错，源文件保留。
    """
    src = storage.resolve(storage.WORKSPACE, file_id)
    if not src.is_file():
        raise ValueError("文件不存在")

    storage.ensure_library_dir()
    dst = Path(storage.LIBRARY_DIR) / src.name
    if dst.exists():
        raise ValueError(f"资料库已存在同名文件：{dst.name}")

    # 先复制到资料库内的临时文件，确认写入成功后再删除源文件并改名，
    # 避免任何中途失败导致文件丢失。
    fd, tmp_name = tempfile.mkstemp(prefix=".keep-", dir=str(storage.LIBRARY_DIR))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy2(src, tmp)
        src.unlink()
        os.replace(tmp, dst)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return dst
