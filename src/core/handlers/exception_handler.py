from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.validators.exceptions import DomainValidationError, EntityNotFoundException


def configure_exception_handlers(application: FastAPI):
    """
    Inyecta los manejadores de excepciones estándar a cualquier aplicación FastAPI.
    """
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        print(f"Error detectado: {exc}") 
        return JSONResponse(
            status_code=500,
            content={"message": "Error interno del sistema", "detail": "Contacte a soporte"},
        )

    @application.exception_handler(EntityNotFoundException)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundException):
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found", "message": exc.message}
        )

    @application.exception_handler(DomainValidationError)
    async def domain_validation_handler(request: Request, exc: DomainValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": "Validation Error", "message": exc.message}
        )