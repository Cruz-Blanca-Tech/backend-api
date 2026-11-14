"""D30: si la descarga de uno de los documentos falla al generar el PDF consolidado,
ese documento se salta y el PDF se arma con los demás; el fallo no debe abortar
la generacion de todos los PDF del lote.

Antes de la correccion, el manejo del error usaba la variable `dni`, que no existe
en ese metodo (`NameError`): una sola descarga fallida interrumpia todo el lote.
"""
import io
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from PIL import Image

from src.contexts.document_intake_ocr.application.use_cases.generate_batch_pdfs_use_case import (
    GenerateBatchPdfsUseCase,
)
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
# Registra los modelos ORM (mismo bloque que test_cp05).
import src.contexts.document_intake_ocr.infrastructure.persistence.model.program_model  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.document_type_config  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model  # noqa: F401

DNI = "12345678"


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, "PNG")
    return buf.getvalue()


class _DriveFalso:
    """Drive simulado: la descarga del archivo `falla_custodia` lanza una excepcion."""

    def __init__(self, falla_custodia=None):
        self.falla_custodia = falla_custodia
        self.subidos = []

    def download_file_to_memory(self, custody_id):
        if custody_id == self.falla_custodia:
            raise RuntimeError("Drive no disponible")
        return _png()

    async def ensure_beneficiary_directory(self, dni):
        return f"carpeta-{dni}"

    async def upload_file_to_folder(self, folder_id, file_bytes, filename, mime_type="application/pdf"):
        self.subidos.append((folder_id, filename, file_bytes))
        return "pdf-1"


def _session(filas):
    session = AsyncMock()
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = filas
    session.execute = AsyncMock(return_value=resultado)
    return session


def _filas(n):
    return [DocumentItemModel(id=uuid4(), batch_id=uuid4(), code=f"DOC{i}", custody_id=f"custodia-{i}",
                              dni_reference=DNI, file_name=f"{DNI}_{i}.jpg", source_id=f"s{i}", status="PROCESSED")
            for i in range(n)]


@pytest.fixture
def sin_eventos(monkeypatch):
    from src.core.events.event_dispatcher import EventDispatcher
    publicados = []

    async def _dispatch(event):
        publicados.append(event)

    monkeypatch.setattr(EventDispatcher, "dispatch", _dispatch)
    return publicados


@pytest.mark.asyncio
async def test_una_descarga_fallida_no_aborta_el_pdf_del_expediente(sin_eventos):
    filas = _filas(3)
    drive = _DriveFalso(falla_custodia="custodia-1")
    uc = GenerateBatchPdfsUseCase(drive, _session(filas))

    await uc.execute(uuid4(), {DNI: {"corrected_dni": DNI, "documents": [f.id for f in filas]}})

    assert len(drive.subidos) == 1, "el PDF debia generarse con los documentos que si se descargaron"
    assert drive.subidos[0][2].startswith(b"%PDF")
    assert len(sin_eventos) == 1, "debia avisarse al maestro del PDF archivado"


@pytest.mark.asyncio
async def test_si_todas_las_descargas_fallan_no_se_genera_pdf_ni_se_rompe(sin_eventos):
    filas = _filas(2)
    drive = _DriveFalso(falla_custodia=None)
    drive.download_file_to_memory = MagicMock(side_effect=RuntimeError("sin red"))
    uc = GenerateBatchPdfsUseCase(drive, _session(filas))

    await uc.execute(uuid4(), {DNI: {"corrected_dni": DNI, "documents": [f.id for f in filas]}})

    assert drive.subidos == []
    assert sin_eventos == []
