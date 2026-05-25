from fastapi import APIRouter

router = APIRouter(prefix="/triage", tags=["Data Quality & Triage"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "context": "Data Quality & Triage"}
