"""路径配置：两个文件空间。

- workspace（Inbox）：项目内 output/，抓取结果先落在这里，是暂存工作区。
- library（资料库）：长期保存目录，默认 ~/Documents/github/notes/50_外部资料，
  是 myknbase 的导入源。

所有文件操作都必须携带 scope，避免两个空间存在同名文件时产生歧义。
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WORKSPACE_DIR = ROOT / "output"
OUTPUT_DIR = WORKSPACE_DIR  # 兼容旧引用

DEFAULT_LIBRARY_DIR = Path.home() / "Documents" / "github" / "notes" / "50_外部资料"
LIBRARY_DIR = Path(
    os.environ.get("MASHANG_FETCH_KEEP_DIR", str(DEFAULT_LIBRARY_DIR))
).expanduser()

WORKSPACE = "workspace"
LIBRARY = "library"
SCOPES = (WORKSPACE, LIBRARY)


def dir_for(scope):
    """返回 scope 对应的根目录，运行时读取，便于测试替换。"""
    if scope == WORKSPACE:
        return WORKSPACE_DIR
    if scope == LIBRARY:
        return LIBRARY_DIR
    raise ValueError("未知文件空间")


def ensure_library_dir():
    """确保资料库目录存在，返回其路径。"""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    return LIBRARY_DIR


def resolve(scope, file_id):
    """把 id 解析为指定空间内的绝对路径，拒绝越界访问。"""
    base = dir_for(scope).resolve()
    target = (base / file_id).resolve()
    if target != base and base not in target.parents:
        raise ValueError("非法路径")
    return target
