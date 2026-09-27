"""Agrupación por clave numérica, no por DNI validado.

Cubre el escenario real del operador: al renombrar el escaneo a mano escribe un
dígito de más o de menos (`123456789_FINS.pdf`, `1234567_DNIBE.pdf`). Esos
archivos se perdían enteros, sin expediente y sin forma de recuperarlos.

El contrato que se fija acá:
  - La clave de agrupación es el token antes del primer `_`, tal cual venga.
  - Solo se rechaza lo que no tiene arreglo por grouping (no hay `_`, el token
    no es numérico, la extensión no sirve, el código no es de la actividad).
  - La longitud del token NO es motivo de rechazo.
  - Un expediente incompleto NO aborta el lote: se guarda INCOMPLETE, se nombra
    en triaje el documento que falta y, cuando lo suben, se reprocesa con IA.
"""
import asyncio

import pytest
from uuid import uuid4

from src.contexts.document_intake_ocr.application.services.single_dossier_processor import (
    SingleDossierProcessor,
)
from src.contexts.document_intake_ocr.domain.entities.activity import Activity, ActivityRequirement
from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode
from src.contexts.document_intake_ocr.domain.value_objects.group_key import GroupKey
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile
from src.contexts.document_intake_ocr.domain.factories.extraction_batch_factory import (
    ExtractionBatchFactory,
)
from src.contexts.document_intake_ocr.domain.services.document_filter_service import (
    DocumentFilterService,
)
from src.contexts.document_intake_ocr.domain.services.document_grouper_service import (
    DocumentGrouperService,
)

CODES = ["FINS", "DJ", "DNIBE", "DNIAP"]


class ExplodingDocProcessor:
    """Falla si le piden procesar algo. Sirve para probar que NO se pide OCR."""

    def __init__(self):
        self.calls = 0

    async def execute(self, doc, model_id, target_folder_id, user_email):
        self.calls += 1
        raise AssertionError(f"No debería haberse procesado {doc.file_name} con OCR")


class CountingDocProcessor:
    """Cuenta a quién se le pidió OCR."""

    def __init__(self):
        self.calls = 0

    async def execute(self, doc, model_id, target_folder_id, user_email):
        self.calls += 1
        doc.mark_as_processed_successfully({}, confidence=0.99)


def _activity(required_codes=None) -> Activity:
    required_codes = required_codes if required_codes is not None else CODES
    reqs = [
        ActivityRequirement(
            document_config=DocumentTypeConfig(
                id=uuid4(),
                name=code,
                code=DocumentTypeCode(code),
                year=2026,
                model_id=f"model-{code.lower()}",
                version=1,
                preview_image_url=f"http://example.com/{code.lower()}.png",
            ),
            is_required=True,
            confidence_threshold=0.85,
        )
        for code in required_codes
    ]
    return Activity(
        id=uuid4(),
        program_id=uuid4(),
        name="INSCRIPCIÓN A EDUCA 2026 - I",
        activity_type="EDUCA_INSCRIPTION",
        start_date=None,
        end_date=None,
        required_documents=reqs,
        is_active=True,
    )


def _file(name: str) -> RawFile:
    return RawFile(file_name=name, source_id=f"src_{name}")


def _dossier_names(batch, key_value):
    dossier = next(d for d in batch.dossiers if d.dni_reference == key_value)
    return sorted(d.document_code.code for d in dossier.documents)


# --------------------------------------------------------------------------
# GroupKey
# --------------------------------------------------------------------------


class TestGroupKey:
    def test_acepta_token_de_nueve_digitos(self):
        key = GroupKey("123456789")
        assert key.value == "123456789"
        assert key.is_standard_dni is False

    def test_acepta_token_de_siete_digitos(self):
        key = GroupKey("1234567")
        assert key.is_standard_dni is False

    def test_token_de_ocho_digitos_es_dni(self):
        key = GroupKey("12345678")
        assert key.is_standard_dni is True

    def test_no_expone_un_dni_derivado(self):
        # La tentación de castear la clave a `DNI` para escribirla en el
        # maestro es el error que la clase existe para evitar. La clave NO
        # ofrece ese atajo a propósito.
        assert not hasattr(GroupKey("12345678"), "dni")

    def test_rechaza_token_no_numerico(self):
        with pytest.raises(ValueError, match="no es numérica"):
            GroupKey("ABCDEFGH")

    def test_rechaza_token_vacio(self):
        with pytest.raises(ValueError, match="no puede estar vacía"):
            GroupKey("")

    def test_str_devuelve_el_token(self):
        assert str(GroupKey("123456789")) == "123456789"


# --------------------------------------------------------------------------
# RawFile.group_key
# --------------------------------------------------------------------------


class TestRawFileGroupKey:
    def test_extrae_token_de_nueve_digitos(self):
        # El caso que antes se perdía: la ValueError de DNI() se tragaba.
        assert _file("123456789_FINS.pdf").group_key.value == "123456789"

    def test_extrae_token_de_siete_digitos(self):
        assert _file("1234567_DNIBE.pdf").group_key.value == "1234567"

    def test_ignora_tokens_sin_guion_bajo(self):
        assert _file("escaneo.jpg").group_key is None

    def test_ignora_token_no_numerico(self):
        assert _file("ABCDEFGH_FINS.pdf").group_key is None


# --------------------------------------------------------------------------
# Filtro: la longitud del token deja de ser motivo de rechazo
# --------------------------------------------------------------------------


class TestFilterAceptsMalformedDniLength:
    def test_token_de_nueve_digitos_pasa_el_filtro(self):
        valid, rejected = DocumentFilterService.filter_batch(
            [_file("123456789_FINS.pdf")], _activity()
        )
        assert len(valid) == 1
        assert rejected == []

    def test_token_de_siete_digitos_pasa_el_filtro(self):
        valid, rejected = DocumentFilterService.filter_batch(
            [_file("1234567_DJ.pdf")], _activity()
        )
        assert len(valid) == 1
        assert rejected == []

    def test_sin_guion_bajo_sigue_rechazado(self):
        valid, rejected = DocumentFilterService.filter_batch(
            [_file("escaneo.pdf")], _activity()
        )
        assert valid == []
        assert len(rejected) == 1
        assert "separador '_'" in rejected[0].reason

    def test_token_no_numerico_sigue_rechazado(self):
        valid, rejected = DocumentFilterService.filter_batch(
            [_file("ABCDEFGH_FINS.pdf")], _activity()
        )
        assert valid == []
        assert "no es numérico" in rejected[0].reason

    def test_extension_no_soportada_sigue_rechazada(self):
        valid, rejected = DocumentFilterService.filter_batch(
            [_file("12345678_FINS.docx")], _activity()
        )
        assert valid == []
        assert "Formato de archivo" in rejected[0].reason

    def test_codigo_fuera_de_catalogo_sigue_rechazado(self):
        valid, rejected = DocumentFilterService.filter_batch(
            [_file("12345678_PASAPORTE.pdf")], _activity()
        )
        assert valid == []
        assert "no es un documento válido para esta actividad" in rejected[0].reason

    def test_rechazado_conserva_la_clave_cuando_la_hay(self):
        # `12345678_PASAPORTE.pdf` es rechazo, pero su clave sí se persiste:
        # antes el DNI se guardaba y ahora también, para que se pueda reasignar.
        _, rejected = DocumentFilterService.filter_batch(
            [_file("12345678_PASAPORTE.pdf")], _activity()
        )
        assert rejected[0].file.group_key.value == "12345678"


# --------------------------------------------------------------------------
# Agrupación
# --------------------------------------------------------------------------


class TestGrouper:
    def test_agrupa_por_token_literal(self):
        proposals = DocumentGrouperService.group_valid_files(
            [_file("123456789_FINS.pdf"), _file("123456789_DJ.pdf")]
        )
        assert len(proposals) == 1
        assert proposals[0].key.value == "123456789"
        assert len(proposals[0].files) == 2

    def test_no_mezcla_claves_distintas(self):
        # El typo y el DNI correcto son DOS expedientes, no uno mezclado.
        proposals = DocumentGrouperService.group_valid_files(
            [_file("12345678_FINS.pdf"), _file("123456789_DJ.pdf")]
        )
        assert sorted(p.key.value for p in proposals) == ["12345678", "123456789"]


# --------------------------------------------------------------------------
# Fábrica: el comportamiento de punta a punta
# --------------------------------------------------------------------------


class TestFactoryEndToEnd:
    def _build(self, files):
        return ExtractionBatchFactory.create_from_raw_files(
            raw_files=[_file(n) for n in files],
            activity=_activity(),
            user_id=uuid4(),
            description="Test",
        )

    def test_lote_con_token_malformado_completo_se_crea(self):
        files = [f"123456789_{c}.pdf" for c in CODES]
        batch = self._build(files)

        assert len(batch.dossiers) == 1
        dossier = batch.dossiers[0]
        assert dossier.dni_reference == "123456789"
        assert dossier.key.is_standard_dni is False
        assert _dossier_names(batch, "123456789") == sorted(CODES)

    def test_expediente_incompleto_NO_aborta_el_lote(self):
        # El lote NUNCA se aborta por un expediente incompleto. Antes el
        # `raise ValueError` de la fábrica tumbaba el lote entero (y encima con
        # AttributeError, o sea 500) si un solo grupo tenía un documento de
        # menos. El control de calidad vive en la UI, que no deja subir un lote
        # con expedientes incompletos.
        files = [f"12345678_{c}.pdf" for c in CODES[:-1]]  # falta DNIAP
        batch = self._build(files)

        assert len(batch.dossiers) == 1
        dossier = batch.dossiers[0]
        assert dossier.status.value == "INCOMPLETE"
        # El error nombra el documento que falta: es lo que lee el revisor.
        assert "DNIAP" in " ".join(dossier.errors)

    def test_expediente_incompleto_no_arrastra_al_resto_del_lote(self):
        good = [f"12345678_{c}.pdf" for c in CODES]
        batch = self._build(good + ["123456789_FINS.pdf"])

        assert sorted(d.dni_reference for d in batch.dossiers) == [
            "12345678",
            "123456789",
        ]
        by_key = {d.dni_reference: d for d in batch.dossiers}
        assert by_key["12345678"].status.value == "COMPLETE"
        assert by_key["123456789"].status.value == "INCOMPLETE"

    @pytest.mark.parametrize("key", ["12345678", "123456789"])
    def test_incompleto_no_aborta_para_ninguna_longitud_de_clave(self, key):
        # Ni el DNI estándar ni el token mal tipeado abortan el lote.
        files = [f"{key}_{c}.pdf" for c in CODES[:-1]]
        batch = self._build(files)

        assert [d.dni_reference for d in batch.dossiers] == [key]
        assert batch.dossiers[0].status.value == "INCOMPLETE"

    def test_expediente_incompleto_no_entra_al_ocr(self):
        # Los documentos quedan PENDING (el estado que AppendDocumentsUseCase
        # reprocesa cuando sube el faltante) y no se le pide OCR a nadie.
        files = [f"12345678_{c}.pdf" for c in CODES[:-1]]
        dossier = self._build(files).dossiers[0]

        assert all(
            d.status.value == "PENDING" for d in dossier.documents
        ), "no debería haberse tocado el estado de los documentos"

        processed = asyncio.run(
            SingleDossierProcessor(single_doc_processor=ExplodingDocProcessor()).execute(
                dossier=dossier,
                activity=_activity(),
                target_folder_id="folder",
                user_email="test@test.com",
            )
        )
        assert processed == 0

    def test_expediente_completo_SI_entra_al_ocr(self):
        # Contrapeso del test anterior: no se saltó OCR por todos.
        files = [f"12345678_{c}.pdf" for c in CODES]
        dossier = self._build(files).dossiers[0]

        processor = CountingDocProcessor()
        processed = asyncio.run(
            SingleDossierProcessor(single_doc_processor=processor).execute(
                dossier=dossier,
                activity=_activity(),
                target_folder_id="folder",
                user_email="test@test.com",
            )
        )
        assert processed == len(CODES)
        assert processor.calls == len(CODES)

    def test_documentos_rechazados_conservan_la_clave(self):
        # `123456789_PASAPORTE.pdf`: código fuera de catálogo, así que es
        # rechazo, pero la clave 123456789 tiene que quedar guardada.
        files = [f"12345678_{c}.pdf" for c in CODES] + ["123456789_PASAPORTE.pdf"]
        batch = self._build(files)

        assert len(batch.rejected_documents) == 1
        rejected = batch.rejected_documents[0]
        assert rejected.dni_reference.value == "123456789"
        assert rejected.failure_reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
