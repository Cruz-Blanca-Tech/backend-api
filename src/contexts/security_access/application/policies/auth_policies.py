class DomainRestrictionPolicy():
    def __init__(self, allowed_domain: str):
        self.allowed_domain = allowed_domain

    def check(self, email: str) -> None:
        if not email.endswith(f"@{self.allowed_domain}"):
            raise PermissionError(f"Dominio no autorizado. Solo se permiten correos de @{self.allowed_domain}")