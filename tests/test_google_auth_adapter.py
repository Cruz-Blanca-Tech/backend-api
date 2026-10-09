"""RF-01: el token de Google se rechaza si no pasa la verificación de firma."""
import pytest

from src.contexts.security_access.infrastructure.adapters import google_auth_adapter as mod
from src.contexts.security_access.infrastructure.adapters.google_auth_adapter import GoogleIdentityAdapter


def test_token_que_falla_la_verificacion_se_rechaza(monkeypatch):
    def falla(*args, **kwargs):
        raise ValueError("Wrong number of segments / firma inválida")

    monkeypatch.setattr(mod.id_token, "verify_oauth2_token", falla)
    with pytest.raises(ValueError):
        GoogleIdentityAdapter("client-id").verify_token("token-falsificado")


def test_correo_no_verificado_se_rechaza(monkeypatch):
    monkeypatch.setattr(
        mod.id_token, "verify_oauth2_token",
        lambda *a, **k: {"email": "x@cruz-blanca.org", "email_verified": False},
    )
    with pytest.raises(ValueError):
        GoogleIdentityAdapter("client-id").verify_token("token")


def test_token_valido_devuelve_la_identidad(monkeypatch):
    capturado = {}

    def ok(token, request, audience, **kwargs):
        capturado.update(audience=audience, **kwargs)
        return {"email": "ana@cruz-blanca.org", "email_verified": True, "name": "Ana", "picture": ""}

    monkeypatch.setattr(mod.id_token, "verify_oauth2_token", ok)
    identity = GoogleIdentityAdapter("client-id").verify_token("token")
    assert str(identity.email) == "ana@cruz-blanca.org"
    assert capturado["audience"] == "client-id"
    assert capturado["clock_skew_in_seconds"] == 30
