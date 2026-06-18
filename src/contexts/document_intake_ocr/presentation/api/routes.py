from fastapi import FastAPI
from src.contexts.document_intake_ocr.presentation.api.routers.program_router import router as program_router
from src.contexts.document_intake_ocr.presentation.api.routers.document_catalog_router import router as catalog_router
from src.contexts.document_intake_ocr.presentation.api.routers.activity_router import router as activity_router
from src.contexts.document_intake_ocr.presentation.api.routers.batch_router import router as batch_router

from fastapi.openapi.utils import get_openapi


# Creamos una instancia de FastAPI, no un APIRouter
intake_app = FastAPI(
    title="Document Intake & Extraction Context",
    description="API para la gestión de documentos, actividades y configuración OCR",
    version="1.0.0"
)

def custom_openapi():
    if intake_app.openapi_schema:
        return intake_app.openapi_schema
    openapi_schema = get_openapi(
        title=intake_app.title,
        version="1.0.0",
        routes=intake_app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"Bearer Auth": []}]
    intake_app.openapi_schema = openapi_schema
    return intake_app.openapi_schema

intake_app.openapi = custom_openapi

# Definimos rutas raíz para esta sub-app
@intake_app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "context": "Document Intake & OCR"}

# Incluimos los routers. 
# Nota: al montar esta app en main.py, los prefijos se combinarán.
intake_app.include_router(program_router)
intake_app.include_router(catalog_router)
intake_app.include_router(activity_router)
intake_app.include_router(batch_router)