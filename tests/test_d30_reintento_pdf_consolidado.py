"""D30: la generacion del PDF consolidado se reintenta y, si falla, queda registrada en el lote."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.document_intake_ocr.application.event_handlers import intake_event_handlers as h


@pytest.mark.asyncio
async def test_exito_al_primer_intento_no_registra_fallo(monkeypatch):
    rec = AsyncMock(); monkeypatch.setattr(h, "_record_pdf_failure", rec)
    run = AsyncMock()
    assert await h.generate_pdfs_with_retry(run, MagicMock(), "b1", attempts=3, delay=0) is True
    run.assert_awaited_once(); rec.assert_not_called()


@pytest.mark.asyncio
async def test_reintenta_y_se_recupera(monkeypatch):
    rec = AsyncMock(); monkeypatch.setattr(h, "_record_pdf_failure", rec)
    run = AsyncMock(side_effect=[RuntimeError("drive"), None])
    assert await h.generate_pdfs_with_retry(run, MagicMock(), "b1", attempts=3, delay=0) is True
    assert run.await_count == 2; rec.assert_not_called()


@pytest.mark.asyncio
async def test_agota_intentos_y_registra_el_fallo(monkeypatch):
    rec = AsyncMock(); monkeypatch.setattr(h, "_record_pdf_failure", rec)
    run = AsyncMock(side_effect=RuntimeError("drive caido"))
    assert await h.generate_pdfs_with_retry(run, MagicMock(), "b1", attempts=3, delay=0) is False
    assert run.await_count == 3
    rec.assert_awaited_once()
    assert "drive caido" in rec.await_args.args[2]


@pytest.mark.asyncio
async def test_registro_del_fallo_escribe_failure_reason():
    session = MagicMock()
    session.rollback = AsyncMock(); session.execute = AsyncMock(); session.commit = AsyncMock()
    await h._record_pdf_failure(session, "b1", "x")
    session.execute.assert_awaited_once()
    assert h.PDF_FAILURE_PREFIX in str(session.execute.await_args.args[0].compile().params)
