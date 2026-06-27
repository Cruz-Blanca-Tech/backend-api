from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from src.contexts.data_quality_triage.presentation.api.__init__ import triage_api_router

triage_app = FastAPI(
    title="Data Quality & Triage Context",
    description="API para orquestar la revisión manual y automática de calidad de los expedientes",
    version="1.0.0"
)

def custom_openapi():
    if triage_app.openapi_schema:
        return triage_app.openapi_schema
    openapi_schema = get_openapi(
        title=triage_app.title,
        version="1.0.0",
        routes=triage_app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"Bearer Auth": []}]
    triage_app.openapi_schema = openapi_schema
    return triage_app.openapi_schema

triage_app.openapi = custom_openapi

# Incluimos el enrutador consolidado (que a su vez tiene batch y dossier)
triage_app.include_router(triage_api_router)
