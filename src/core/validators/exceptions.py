# src/core/exceptions.py

class DomainException(Exception):
    """Clase base para todas las excepciones de negocio."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class EntityNotFoundException(DomainException):
    """Se lanza cuando se busca un recurso que no existe (ej. ID de programa no válido)."""
    pass

class DomainValidationError(DomainException):
    """Se lanza cuando los datos de entrada violan una regla de negocio (ej. documentos incompletos)."""
    pass

class ExternalServiceException(Exception):
    """Se lanza cuando un proveedor externo (Google Drive, Azure, etc.) falla de forma técnica o de red."""
    def __init__(self, service_name: str, operation: str, details: str):
        self.service_name = service_name
        self.operation = operation
        self.message = f"Fallo crítico en [{service_name}] durante la operación [{operation}]: {details}"
        super().__init__(self.message)

# ==========================================
# EXCEPCIONES DE SEGURIDAD Y ACCESO
# ==========================================

class SecurityException(Exception):
    """Clase base para excepciones relacionadas con identidad y permisos."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class UnauthorizedException(SecurityException):
    """Se lanza cuando no hay token, el token es inválido o ha expirado (HTTP 401)."""
    pass

class ForbiddenException(SecurityException):
    """Se lanza cuando el usuario está identificado, pero su ROL no le permite hacer esta acción (HTTP 403)."""
    pass