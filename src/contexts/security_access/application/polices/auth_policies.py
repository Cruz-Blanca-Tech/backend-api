
def cruz_blanca_domain_policy(email: str):
    """Política específica: Solo permite correos de la ONG."""
    if not email.endswith("@cruz-blanca.org"):
        raise PermissionError("Dominio no autorizado. Solo miembros de Cruz Blanca.")