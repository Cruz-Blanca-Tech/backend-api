import pytest
from pydantic import ValidationError
from src.core.config import Settings


def test_d24_production_rejects_dev_only_key():
    with pytest.raises(ValidationError) as exc:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            SECRET_KEY="dev-only-insecure-key",
        )
    assert "SECRET_KEY no es segura" in str(exc.value)


def test_d24_production_rejects_historical_leaked_key():
    with pytest.raises(ValidationError) as exc:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            SECRET_KEY="super-secret-key-change-in-production-1234567890",
        )
    assert "SECRET_KEY no es segura" in str(exc.value)


def test_d24_production_rejects_short_key():
    with pytest.raises(ValidationError) as exc:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            SECRET_KEY="too-short-key",
        )
    assert "SECRET_KEY no es segura" in str(exc.value)


def test_d24_production_accepts_valid_strong_key():
    valid_key = "a" * 64
    s = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
        SECRET_KEY=valid_key,
    )
    assert s.SECRET_KEY == valid_key
