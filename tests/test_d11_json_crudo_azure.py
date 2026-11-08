"""D11: se guarda lo que leyó Azure además de lo que dejó la normalización del LLM."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.contexts.document_intake_ocr.application.services.single_document_processor import SingleDocumentProcessor
from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.document_item_mapper import DocumentItemMapper

AZURE = {"child_names": {"value": "JUAN PERES", "confidence": 0.71}, "child_dni": {"value": "1234567B", "confidence": 0.55}}
LLM = {"child_names": {"value": "JUAN PÉREZ", "confidence": 0.71}, "child_dni": {"value": "12345678", "confidence": 0.55}}


def _doc():
    return DocumentItem(id=uuid4(), source_id="drive-id", file_name="12345678_FINS.pdf", dni_reference=None)


def _processor(normalizer=None):
    storage = AsyncMock()
    storage.copy_to_custody = AsyncMock(return_value="custody-uri")
    storage.download_file = AsyncMock(return_value=b"%PDF")
    extractor = AsyncMock()
    extractor.extract_data = AsyncMock(return_value={"fields": AZURE, "confidence": 0.8})
    return SingleDocumentProcessor(storage, extractor, normalizer)


@pytest.mark.asyncio
async def test_guarda_el_json_de_azure_y_el_normalizado():
    normalizer = AsyncMock()
    normalizer.normalize = AsyncMock(return_value=LLM)
    doc = _doc()
    await _processor(normalizer).execute(doc, "model", "folder", "user@cruz-blanca.org")
    assert doc.extracted_data == LLM
    assert doc.raw_extracted_data == AZURE


@pytest.mark.asyncio
async def test_el_llm_no_puede_alterar_la_copia_cruda():
    async def normalize_in_place(data, ctx):
        data["child_dni"]["value"] = "99999999"
        return data
    normalizer = AsyncMock()
    normalizer.normalize = normalize_in_place
    doc = _doc()
    await _processor(normalizer).execute(doc, "model", "folder", "user@cruz-blanca.org")
    assert doc.raw_extracted_data["child_dni"]["value"] == "1234567B"


def test_se_persiste_y_se_lee_de_la_base():
    doc = _doc()
    doc.mark_as_processed_successfully(LLM, 0.8, raw_data=AZURE)
    back = DocumentItemMapper.to_domain(DocumentItemMapper.to_model(doc, uuid4()))
    assert back.raw_extracted_data == AZURE
    assert back.extracted_data == LLM
