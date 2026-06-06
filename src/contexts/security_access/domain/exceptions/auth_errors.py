# src/contexts/auth/domain/exceptions/auth_errors.py

class AuthException(Exception):
    """Clase base para todas las excepciones del contexto de auth."""
    pass

class UserAlreadyExistsError(AuthException):
    """Se lanza cuando intentan registrar un DNI que ya existe."""
    def __init__(self, email: str):
        super().__init__(f"El usuario con email {email} ya está registrado.")

class InvalidCredentialsError(AuthException):
    """Se lanza cuando el login falla."""
    def __init__(self):
        super().__init__("Credenciales inválidas.")

class UserNotAuthorizedError(AuthException):
    """Se lanza cuando el usuario existe en Google pero no en nuestra BD."""
    def __init__(self, email: str):
        super().__init__(f"El usuario {email} no tiene permisos de acceso al sistema.")

class DomainValidationError(AuthException):
    """Se lanza cuando el Value Object falla (ej. email no es de Cruz Blanca)."""
    pass