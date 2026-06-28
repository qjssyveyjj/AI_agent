import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.kb import service as kb_service
from app.kb.parser import UnsupportedFileType
from app.security.auth import get_current_user

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])
logger = logging.getLogger("ai_agent.kb")


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None


@router.post("/documents")
async def upload_document(
    file: UploadFile, _: str = Depends(get_current_user)
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")
    try:
        return await kb_service.ingest_document(file.filename or "未命名", data)
    except UnsupportedFileType as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("文档入库失败")
        raise HTTPException(status_code=500, detail=f"入库失败：{type(e).__name__}: {e}")


@router.get("/documents")
async def list_documents(_: str = Depends(get_current_user)) -> dict:
    return {"documents": await kb_service.list_documents()}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, _: str = Depends(get_current_user)) -> dict:
    ok = await kb_service.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"deleted": doc_id}


@router.post("/search")
async def search(req: SearchRequest, _: str = Depends(get_current_user)) -> dict:
    return {"hits": await kb_service.search(req.query, top_k=req.top_k)}
