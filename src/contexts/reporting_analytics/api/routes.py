from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from src.contexts.reporting_analytics.features.demographics.presentation.api.demographics_routes import router as demographics_router
from src.contexts.reporting_analytics.features.demographics.presentation.api.exports_routes import router as exports_router
from src.contexts.reporting_analytics.features.operations.presentation.api.operations_routes import router as ops_dashboard_router
from src.contexts.reporting_analytics.features.operations.presentation.api.operations_exports_routes import router as ops_exports_router

reporting_app = FastAPI(
    title="Reporting & Analytics API",
    description="API for dashboards and reporting metrics",
    version="1.0.0"
)

reporting_app.include_router(demographics_router)
reporting_app.include_router(exports_router)
reporting_app.include_router(ops_dashboard_router)
reporting_app.include_router(ops_exports_router)

@reporting_app.get("/health", tags=["Reporting & Analytics"])
async def health_check():
    return {"status": "ok", "context": "Reporting & Analytics"}

def custom_openapi():
    if reporting_app.openapi_schema:
        return reporting_app.openapi_schema
    openapi_schema = get_openapi(
        title=reporting_app.title,
        version="1.0.0",
        routes=reporting_app.routes,
    )
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"Bearer Auth": []}]
    reporting_app.openapi_schema = openapi_schema
    return reporting_app.openapi_schema

reporting_app.openapi = custom_openapi
