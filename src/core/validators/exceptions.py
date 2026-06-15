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