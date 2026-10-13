"""调用 Node 核心引擎，把 URL 转换为本地文件。"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "src" / "cli.js"

FORMATS = {"网页正文（Markdown）": "md", "网页表格（CSV）": "csv", "PDF 附件": "pdf"}


def fetch(url, fmt="md", out_dir=None, timeout=600, attachments=None):
    """调用 src/cli.js，返回其 JSON 结果 dict。

    成功: {"ok": True, "path": ..., "format": ..., "meta": {...}}
    失败: {"ok": False, "error": ...}
    """
    if fmt not in FORMATS.values():
        return {"ok": False, "error": f"不支持的格式: {fmt}"}

    out_dir = Path(out_dir) if out_dir else ROOT / "output"
    cmd = ["node", str(CLI), url, "--format", fmt, "--out", str(out_dir)]

    if attachments is not None:
        cmd.extend(["--attachments", json.dumps(attachments)])

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "error": "未找到 node，请先安装 Node.js"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "转换超时，请稍后重试"}

    stdout = (proc.stdout or "").strip()
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    stderr_lines = [l for l in (proc.stderr or "").strip().splitlines() if l.strip()]
    detail = stderr_lines[-1] if stderr_lines else "转换失败，未返回结果"
    return {"ok": False, "error": detail}
