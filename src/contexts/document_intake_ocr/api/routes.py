from fastapi import APIRouter

router = APIRouter(prefix="/intake", tags=["Document Intake & OCR"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "context": "Document Intake & OCR"}
