"""RF-01: el token de Google se rechaza si no pasa la verificación de firma."""
import pytest
from google.auth.exceptions import GoogleAuthError

from src.contexts.security_access.infrastructure.adapters import google_auth_adapter as mod
from src.contexts.security_access.infrastructure.adapters.google_auth_adapter import GoogleIdentityAdapter
from src.core.config import settings


def test_token_que_falla_la_verificacion_se_rechaza(monkeypatch):
    def falla(*args, **kwargs):
        raise ValueError("Wrong number of segments / firma inválida")

    monkeypatch.setattr(mod.id_token, "verify_oauth2_token", falla)
    with pytest.raises(ValueError):
        GoogleIdentityAdapter("client-id").verify_token("token-falsificado")


def test_token_con_firma_invalida_es_rechazado_retest_d23(monkeypatch):
    """D23 Retest: un token con firma criptográficamente inválida debe ser rechazado
    sin decodificar payloads inseguros."""
    def firma_invalida(*args, **kwargs):
        raise GoogleAuthError("Invalid token signature from Google IdP")

    monkeypatch.setattr(mod.id_token, "verify_oauth2_token", firma_invalida)
    
    with pytest.raises(ValueError, match="Token de Google inválido o expirado."):
        GoogleIdentityAdapter("client-id").verify_token("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.forged.signature")


def test_atajo_test_token_bloqueado_en_produccion_d26(monkeypatch):
    """D26: El atajo 'test-token' solo funciona en development. En producción debe ser
    enviado a Google y consecuentemente rechazado."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    
    def falla(*args, **kwargs):
        raise ValueError("Invalid token")
    
    monkeypatch.setattr(mod.id_token, "verify_oauth2_token", falla)
    
    with pytest.raises(ValueError, match="Token de Google inválido o expirado."):
        GoogleIdentityAdapter("client-id").verify_token("test-token")


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
