from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
app = FastAPI(title="WebIntParser 18.09")

class StartReq(BaseModel):
    sources: List[str] = ["twitter","telegram"]
    filters: dict = {}

@app.post("/parser/start")
def start(r: StartReq):
    return {"ok": True, "running": True, "sources": r.sources}

@app.post("/parser/stop")
def stop():
    return {"ok": True, "running": False}

@app.get("/health")
def health():
    return {"ok": True, "service": "webintparser", "version": "1.0.0"}

@app.post("/rules/import")
def rules_import(file: UploadFile = File(...)):
    return {"ok": True, "filename": file.filename}
