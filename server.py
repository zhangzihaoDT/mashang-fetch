"""FastAPI 服务：提供 /api 接口并托管 React 前端构建产物。

启动：python -m uvicorn server:app --host 0.0.0.0 --port 7860
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import service
from app.fetch import FORMATS

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "web" / "dist"

app = FastAPI(title="mashang-fetch")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FetchRequest(BaseModel):
    url: str
    format: str = "md"


@app.get("/api/formats")
def api_formats():
    return {"formats": [{"label": label, "value": value} for label, value in FORMATS.items()]}


@app.get("/api/files")
def api_files():
    return {"files": service.list_files()}


@app.post("/api/fetch")
def api_fetch(req: FetchRequest):
    overview = req.url.strip()
    if not overview:
        return {"ok": False, "error": "请先输入 URL"}
    fmt = req.format if req.format in ("md", "csv") else "md"
    return service.fetch_url(overview, fmt)


@app.get("/api/preview")
def api_preview(id: str = Query(...)):
    try:
        return service.preview(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/download")
def api_download(id: str = Query(...)):
    try:
        path = service.resolve_id(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(str(path), filename=path.name)


if DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="web")
