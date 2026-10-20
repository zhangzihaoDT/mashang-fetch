"""FastAPI 服务：提供 /api 接口并托管 React 前端构建产物。

启动：python -m uvicorn server:app --host 0.0.0.0 --port 7860
"""
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.search_http import bounded
from app import service
from app.fetch import FORMATS

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
    attachments: list[str] | None = None


class RenameRequest(BaseModel):
    scope: str = "workspace"
    id: str
    name: str


class ScopeIdRequest(BaseModel):
    scope: str = "workspace"
    id: str


class IdRequest(BaseModel):
    id: str


class BatchRequest(BaseModel):
    scope: str = "workspace"
    action: str
    ids: list[str]


class SearchRequest(BaseModel):
    query: str
    domains: list[str] = []
    after: str = ""
    before: str = ""
    entries: list[dict] | None = None


@app.post("/api/search/plan")
@bounded
def api_search_plan(req: SearchRequest):
    from app.research import generate
    try:
        return generate(req.query, req.domains, req.after, req.before)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/search")
@bounded
def api_search(req: SearchRequest):
    from app.research import generate, execute
    try:
        entries = req.entries
        warning = None
        plan_issues = []
        if entries is None:
            generated = generate(req.query, req.domains, req.after, req.before)
            entries, warning = generated['entries'], generated['warning']
            plan_issues = generated.get('plan_issues', [])
        result = execute(req.query, entries, req.domains, req.after, req.before)
        if warning:
            result['diagnostics']['warnings'].append(warning)
        if plan_issues:
            result['diagnostics'].setdefault('plan_issues', []).extend(plan_issues)
        return result
    except ValueError as exc:
        if hasattr(exc, "diagnostics"):
            return JSONResponse(status_code=400, content={"detail": str(exc), "diagnostics": exc.diagnostics})
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/import")
async def api_import(request: Request, name: str = Query(...)):
    from app.imports import import_file, MAX_UPLOAD
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="文件不得超过 25 MB")
    try:
        return import_file(name, bytes(data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/formats")
def api_formats():
    return {"formats": [{"label": label, "value": value} for label, value in FORMATS.items()]}


@app.get("/api/files")
def api_files(scope: str = Query("workspace")):
    try:
        return {"scope": scope, "files": service.list_files(scope)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/fetch")
def api_fetch(req: FetchRequest):
    overview = req.url.strip()
    if not overview:
        return {"ok": False, "error": "请先输入 URL"}
    return service.fetch_url(overview, req.format, req.attachments)


@app.get("/api/preview")
def api_preview(scope: str = Query("workspace"), id: str = Query(...)):
    try:
        return service.preview(scope, id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/download")
def api_download(scope: str = Query("workspace"), id: str = Query(...)):
    try:
        path = service.resolve_id(scope, id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(str(path), filename=path.name)


@app.get("/api/view")
def api_view(scope: str = Query("workspace"), id: str = Query(...)):
    try:
        path = service.resolve_id(scope, id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="仅支持 PDF 预览")
    return FileResponse(str(path), media_type="application/pdf", filename=path.name,
                        content_disposition_type="inline")


@app.get("/api/config")
def api_config():
    return service.config()


@app.post("/api/keep")
def api_keep(req: IdRequest):
    try:
        return service.keep(req.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/open-inbox")
def api_open_inbox(scope: str = Query("workspace"), id: str | None = Query(None)):
    try:
        return service.open_inbox(scope, id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/rename")
def api_rename(req: RenameRequest):
    try:
        return {"ok": True, **service.rename(req.scope, req.id, req.name)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/delete")
def api_delete(req: ScopeIdRequest):
    try:
        service.delete(req.scope, req.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


@app.post("/api/batch")
def api_batch(req: BatchRequest):
    try:
        return service.batch(req.scope, req.action, req.ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


if DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="web")
