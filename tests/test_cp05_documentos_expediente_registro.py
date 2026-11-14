"""CP-05 (HU-003, CA-003-01): los documentos escaneados (FINS, DJ, DNIBE, DNIAP)
quedan guardados en el expediente del menor y se pueden consultar desde su
registro.

Camino real que se ejercita (sin red ni base de datos remota)
-------------------------------------------------------------
1. OCR → triaje: `InscriptionTriageStrategy` recibe los cuatro documentos y arma
   el expediente (`TriageCase.document_ids` guarda el id de cada documento).
2. Consulta del expediente: `GetDocumentsByDossierUseCase` (GET
   /api/v1/intake/batches/{id}/dossiers/{dni}/documents) con la sesión simulada
   devolviendo las filas de `document_items` del menor.
3. Aprobación: `SubmitCorrectionUseCase` aprueba. El bus se intercepta y, al
   recibir `DossierApprovedEvent`, ejecuta el MDM real
   (`ProcessApprovedTriageCaseUseCase` → `SqlBeneficiaryRepository` sobre SQLite
   en memoria) y deja el caso en `sync_status = SYNCED`, igual que
   `handle_mdm_dossier_approved`. Así el lote se cierra solo
   (`FinalizeBatchIfCompleteUseCase` → FINALIZED), como en producción.
4. Registro del menor: `GetBeneficiaryByIdUseCase` (GET
   /api/v1/mdm/beneficiaries/{id}); el frontend lista `historical_documents`.

Qué fija el CA
--------------
- El expediente guarda y permite consultar los cuatro documentos.
- Tras aprobar y cerrar el lote, el registro del menor permite consultar los
  documentos de su expediente (al menos un documento enlazado).

Si no se cumple, el test FALLA con un mensaje que empieza con «HALLAZGO».

Datos ficticios. `openai` no está instalado en el venv de pruebas: si falta, se
registra un módulo sustituto vacío (el LLM no se invoca: `llm_client` es None).
"""

import io
import sys
import types
import copy
import pytest
from uuid import uuid4
from datetime import date
from unittest.mock import AsyncMock, MagicMock

try:  # pragma: no cover - depende del entorno
    import openai  # noqa: F401
except ImportError:  # el LLM no se usa en estas pruebas
    _openai = types.ModuleType("openai")
    _openai.AsyncAzureOpenAI = type("AsyncAzureOpenAI", (), {})
    sys.modules["openai"] = _openai

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.sql.dml import Update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.core.config import settings
from src.core.database import Base
from src.contexts.data_quality_triage.domain.shared.strategies.inscription_strategy import InscriptionTriageStrategy
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import (
    SubmitCorrectionUseCase,
)
from src.contexts.core_beneficiary_management.application.use_cases.process_approved_triage_case_use_case import (
    ProcessApprovedTriageCaseUseCase,
)
from src.contexts.core_beneficiary_management.application.use_cases.get_beneficiary_by_id_use_case import (
    GetBeneficiaryByIdUseCase,
)
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import (
    SqlBeneficiaryRepository,
)
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.batch_triage_completed_event import BatchTriageCompletedEvent
from src.contexts.core_beneficiary_management.domain.events.beneficiary_events import DossierPdfArchivedEvent
from src.contexts.core_beneficiary_management.infrastructure.events import beneficiary_event_handlers
from src.contexts.document_intake_ocr.application.event_handlers import intake_event_handlers
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.document_intake_ocr.application.use_cases.get_documents_by_dossier_use_case import (
    GetDocumentsByDossierUseCase,
)
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
# Registra los modelos ORM en SQLAlchemy (mismo bloque que
# test_batch_resilient_sync): sin esto, instanciar un modelo ORM falla al
# configurar los mappers de ExtractionBatchModel/DocumentItemModel.
import src.contexts.document_intake_ocr.infrastructure.persistence.model.program_model  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.document_type_config  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model  # noqa: F401
import src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model  # noqa: F401
import src.contexts.core_beneficiary_management.infrastructure.persistence.model  # noqa: F401

ACTIVITY_ID = uuid4()
DNI_MENOR = "12345678"
DNI_PADRE = "40000001"
DNI_MADRE = "40000002"
TEL_PADRE = "987654321"
TEL_MADRE = "912345678"

MDM_TABLES = (
    "persons", "beneficiaries", "adults", "person_relationships",
    "medical_records", "education_records", "historical_documents",
    "beneficiary_enrollments",
)


# ------------------------------------------------------------ documentos OCR


def _fins():
    """Ficha de inscripción completa, con las llaves que entrega Azure."""
    return {
        "child_first_name": "Juan Carlos", "child_last_name": "Quispe Mamani",
        "child_age": "9", "child_gender": "M", "child_birth_date": "15/06/2015",
        "child_dni": DNI_MENOR,
        "address_city": "Lima", "address_district": "Comas",
        "address_neighborhood": "Las Flores", "address_block": "B", "address_lot": "12",
        "parents_father_full_name": "Pedro Quispe Lopez", "parents_father_phone": TEL_PADRE,
        "parents_father_dni": DNI_PADRE,
        "parents_mother_full_name": "Rosa Mamani Torres", "parents_mother_phone": TEL_MADRE,
        "parents_mother_dni": DNI_MADRE,
        "parents_guardian_full_name": "Rosa Mamani Torres", "parents_guardian_phone": TEL_MADRE,
        "parents_guardian_dni": DNI_MADRE,
        "general_emergency_phone": TEL_MADRE,
        "child_school": "COLEGIO SAN MARTIN", "child_grade": "3RO PRIMARIA",
        "educational_knows_how_to_read_yes": "selected", "educational_knows_how_to_read_no": "unselected",
        "educational_knows_how_to_write_yes": "selected", "educational_knows_how_to_write_no": "unselected",
        "educational_has_repeated_grade_yes": "unselected", "educational_has_repeated_grade_no": "selected",
        "educational_has_learning_difficulties_yes": "unselected",
        "educational_has_learning_difficulties_no": "selected",
        "allergy_penicillin": "selected", "allergy_milk": "selected",
        "medical_insurance_sis": "selected", "medical_has_complete_vaccines": "SI",
        "general_is_baptized": "SI", "general_has_first_communion": "NO",
        "general_can_cut_hair": "SI", "general_can_take_medical_exams": "SI",
    }


def _dj():
    return {
        "child_dni": DNI_MENOR, "child_name": "Juan Carlos Quispe Mamani",
        "parents_father_dni": DNI_PADRE, "parents_father_name": "Pedro Quispe Lopez",
        "parents_mother_dni": DNI_MADRE, "parents_mother_name": "Rosa Mamani Torres",
        "guardian_dni": DNI_MADRE,
    }


def _dnibe():
    return {"DocumentNumber": DNI_MENOR, "FirstName": "Juan Carlos", "LastName": "Quispe Mamani",
            "DateOfBirth": "15 06 2015", "Gender": "M"}


def _dniap():
    return {"DocumentNumber": DNI_MADRE, "FirstName": "Rosa", "LastName": "Mamani Torres",
            "DateOfBirth": "01 01 1985", "Gender": "F"}


def _doc(code, data, confidence):
    return DocumentDTO(id=uuid4(), file_name=f"{DNI_MENOR}_{code}.jpg", document_code=code,
                       extracted_data=data, confidence_score=confidence)


async def _procesar_ocr(batch_id):
    documentos = [
        _doc("FINS", _fins(), 0.75),  # bajo el umbral por defecto → revisión humana
        _doc("DJ", _dj(), 0.95),
        _doc("DNIBE", _dnibe(), 0.95),
        _doc("DNIAP", _dniap(), 0.95),
    ]
    return await InscriptionTriageStrategy().execute(
        batch_id=batch_id,
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference=DNI_MENOR,
        documents=documentos,
        context={"schools": [{"name": "COLEGIO SAN MARTIN", "is_active": True}]},
    )


# ------------------------------------------------------------ dobles de prueba


class _SesionSqlite:
    """Adapta una `Session` síncrona de SQLite a la interfaz async que usa el
    repositorio del MDM. La SQL que se ejecuta es la del repositorio real."""

    def __init__(self, session):
        self._s = session

    @property
    def no_autoflush(self):
        return self._s.no_autoflush

    async def execute(self, statement, params=None):
        return self._s.execute(statement, params) if params is not None else self._s.execute(statement)

    async def scalar(self, statement):
        return self._s.scalar(statement)

    async def merge(self, model):
        return self._s.merge(model)

    async def commit(self):
        self._s.commit()

    async def flush(self):
        self._s.flush()


class _ActivitySession:
    """Reemplaza `async_session_maker()` del handler del MDM: devuelve el
    activity_id del lote sin abrir ninguna conexión."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, statement, params=None):
        res = MagicMock()
        res.fetchone.return_value = (str(ACTIVITY_ID),)
        return res


class _SesionMdm:
    """Reemplaza `async_session_maker()` del manejador del MDM: abre una sesion
    sobre la base maestra local y la entrega con la interfaz async."""

    def __init__(self, engine):
        self._engine = engine

    async def __aenter__(self):
        self._s = Session(self._engine)
        return _SesionSqlite(self._s)

    async def __aexit__(self, *exc):
        self._s.close()
        return False


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, "PNG")
    return buf.getvalue()


class _DriveFalso:
    """Drive simulado con la misma interfaz que `GoogleDriveStorageAdapter`. Como el
    adaptador real, el archivo se identifica por nombre dentro de la carpeta del
    beneficiario: si ya existe, se actualiza en lugar de duplicarse."""

    def __init__(self, *args, **kwargs):
        pass

    archivos = {}  # (carpeta, nombre) -> id; se reinicia en cada prueba
    subidas = []

    def download_file_to_memory(self, custody_id):
        return _png()

    async def ensure_beneficiary_directory(self, dni):
        return f"carpeta-{dni}"

    async def upload_file_to_folder(self, folder_id, file_bytes, filename, mime_type="application/pdf"):
        assert file_bytes.startswith(b"%PDF"), "lo que se sube a Drive debe ser un PDF"
        clave = (folder_id, filename)
        fid = _DriveFalso.archivos.setdefault(clave, f"pdf-{len(_DriveFalso.archivos) + 1}")
        _DriveFalso.subidas.append(clave)
        return fid


class _SesionLote:
    """Reemplaza `async_session_maker()` del manejador del lote: las consultas de
    documentos devuelven `filas` y los UPDATE no tocan ninguna base."""

    def __init__(self, filas):
        self._filas = filas

    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, statement, params=None):
        res = MagicMock()
        if isinstance(statement, Update):
            res.rowcount = 1
        else:
            res.scalars.return_value.all.return_value = self._filas
        return res

    async def commit(self):
        pass

    async def rollback(self):
        pass


@pytest.fixture
def drive_falso(monkeypatch):
    """Cambia el adaptador real de Google Drive por uno simulado."""
    _DriveFalso.archivos = {}
    _DriveFalso.subidas = []
    monkeypatch.setattr(intake_event_handlers, "GoogleDriveStorageAdapter", _DriveFalso)
    return _DriveFalso


@pytest.fixture
def sin_conexion(monkeypatch):
    """Ninguna sesión abre conexión: el handler del MDM solo lee el lote."""
    assert settings.ENVIRONMENT != "production", "Estas pruebas no deben correr con ENVIRONMENT=production"
    import src.core.database as database
    monkeypatch.setattr(database, "async_session_maker", lambda: _ActivitySession())


@pytest.fixture
def mdm_engine():
    """Base maestra local: SQLite en memoria con las tablas ORM del MDM."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[t] for t in MDM_TABLES])
    yield engine
    engine.dispose()


async def _registro(mdm_engine, beneficiary_id):
    """Lo que devuelve GET /api/v1/mdm/beneficiaries/{id} (sesión nueva)."""
    with Session(mdm_engine) as s:
        return await GetBeneficiaryByIdUseCase(SqlBeneficiaryRepository(_SesionSqlite(s))).execute(beneficiary_id)


# ---------------------------------------------------------------------- tests

CODIGOS = ("FINS", "DJ", "DNIBE", "DNIAP")


@pytest.fixture
def bus_con_mdm(monkeypatch, mdm_engine):
    """Bus in-process: guarda cada evento y, para `DossierApprovedEvent`, corre
    el MDM real y marca el caso como SYNCED (lo que hace
    `handle_mdm_dossier_approved`). Captura también `dispatch_background`."""
    publicados = []
    casos = {}

    async def _despachar(event):
        publicados.append(event)
        if isinstance(event, DossierApprovedEvent):
            with Session(mdm_engine) as s:
                handler = ProcessApprovedTriageCaseUseCase(SqlBeneficiaryRepository(_SesionSqlite(s)))
                await handler.execute(event)
            casos[event.triage_case_id].sync_status = "SYNCED"
        elif isinstance(event, DossierPdfArchivedEvent):
            # Manejador real del MDM: enlaza el PDF archivado al registro del menor.
            await beneficiary_event_handlers.handle_dossier_pdf_archived_event(event)

    def _despachar_en_segundo_plano(event):
        publicados.append(event)

    monkeypatch.setattr(EventDispatcher, "dispatch", _despachar)
    monkeypatch.setattr(EventDispatcher, "dispatch_background", _despachar_en_segundo_plano)
    monkeypatch.setattr(beneficiary_event_handlers, "async_session_maker", lambda: _SesionMdm(mdm_engine))
    return publicados, casos


def _estados_del_lote(session):
    """Estados escritos en extraction_batches por FinalizeBatchIfCompleteUseCase."""
    estados = []
    for llamada in session.execute.await_args_list:
        sentencia = llamada.args[0] if llamada.args else None
        params = getattr(sentencia, "compile", None) and sentencia.compile().params
        if params and "status" in params:
            estados.append(params["status"])
    return estados


async def _aprobar_y_cerrar_lote(case, casos):
    """Aprobación manual (PATCH /triage/educa/{id}); devuelve la sesión simulada."""
    casos[case.id] = case
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=case)
    repo.save = AsyncMock()
    repo.get_all_by_batch_id = AsyncMock(return_value=[case])

    validator = MagicMock()
    validator.validate_can_be_corrected = AsyncMock()

    beneficiary_repo = MagicMock()
    beneficiary_repo.get_by_dni = AsyncMock(return_value=None)

    session = AsyncMock()
    resultado = MagicMock()
    resultado.fetchone.return_value = (str(ACTIVITY_ID),)
    session.execute = AsyncMock(return_value=resultado)
    session.add = MagicMock()
    session.expire_all = MagicMock()
    lote = MagicMock()
    lote.status = "PROCESSED"
    session.get = AsyncMock(return_value=lote)

    uc = SubmitCorrectionUseCase(
        triage_repo=repo,
        session=session,
        beneficiary_repo=beneficiary_repo,
        status_validator=validator,
    )
    await uc.execute(case.id, uuid4(), copy.deepcopy(case.dossier_data))
    return session


async def _generar_pdf_del_lote(evento, case, monkeypatch):
    """Ejecuta el manejador real del lote completado (`handle_batch_triage_completed`):
    marca FINALIZED, genera el PDF con las imágenes del expediente y lo sube a Drive.
    Solo se simulan la base del lote y el adaptador de Drive."""
    filas = [
        DocumentItemModel(id=doc_id, batch_id=evento.batch_id, code=codigo, custody_id=f"custodia-{codigo}",
                          dni_reference=DNI_MENOR, file_name=f"{DNI_MENOR}_{codigo}.jpg",
                          source_id=f"drive-{codigo}", status="APPROVED")
        for codigo, doc_id in case.document_ids.items()
    ]
    monkeypatch.setattr(intake_event_handlers, "async_session_maker", _SesionLote(filas))
    await intake_event_handlers.handle_batch_triage_completed(evento)


class TestCP05DocumentosDelExpediente:

    @pytest.mark.asyncio
    async def test_el_expediente_guarda_y_lista_los_4_documentos(self):
        batch_id = uuid4()
        case = await _procesar_ocr(batch_id)
        assert set(case.document_ids) == set(CODIGOS), (
            f"HALLAZGO (CA-003-01): el expediente no guarda los 4 documentos; document_ids = "
            f"{sorted(case.document_ids)}"
        )

        filas = [
            DocumentItemModel(id=doc_id, batch_id=batch_id, code=codigo, dni_reference=DNI_MENOR,
                              file_name=f"{DNI_MENOR}_{codigo}.jpg", source_id=f"drive-{codigo}",
                              status="PROCESSED")
            for codigo, doc_id in case.document_ids.items()
        ]
        session = AsyncMock()
        res_docs = MagicMock()
        res_docs.scalars.return_value.all.return_value = filas
        res_lote = MagicMock()
        res_lote.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(side_effect=[res_docs, res_lote])

        respuesta = await GetDocumentsByDossierUseCase(session).execute(batch_id=batch_id, dni_reference=DNI_MENOR)
        listados = {d.code: d.id for d in respuesta.documents}
        assert listados == dict(case.document_ids), (
            f"HALLAZGO (CA-003-01): la consulta del expediente no lista los 4 documentos del menor: {listados}"
        )

    @pytest.mark.asyncio
    async def test_los_documentos_se_consultan_desde_el_registro_del_menor(
        self, bus_con_mdm, sin_conexion, mdm_engine, drive_falso, monkeypatch
    ):
        publicados, casos = bus_con_mdm
        case = await _procesar_ocr(uuid4())
        assert case.status == TriageStatus.PENDING_REVIEW, f"Precondición: revisión humana, quedó {case.status}"

        session = await _aprobar_y_cerrar_lote(case, casos)
        assert case.status == TriageStatus.APPROVED, f"Precondición: el revisor aprueba, quedó {case.status}"
        assert case.sync_status == "SYNCED", f"Precondición: el MDM debía cargar al menor, sync={case.sync_status}"
        assert "FINALIZED" in _estados_del_lote(session), (
            f"Precondición: el lote debía cerrarse solo; estados escritos = {_estados_del_lote(session)}"
        )

        # El cierre automático publica BatchTriageCompletedEvent (D30). Se ejecuta el manejador real:
        # genera el PDF con los documentos, lo sube a un Drive simulado y avisa al maestro.
        evento = next((e for e in publicados if isinstance(e, BatchTriageCompletedEvent)), None)
        assert evento is not None, (
            "HALLAZGO (CA-003-01, D30): el cierre automático del lote no publicó BatchTriageCompletedEvent; "
            f"eventos publicados: {sorted({type(e).__name__ for e in publicados})}"
        )
        await _generar_pdf_del_lote(evento, case, monkeypatch)

        with Session(mdm_engine) as s:
            guardado = await SqlBeneficiaryRepository(_SesionSqlite(s)).get_by_dni(DNI_MENOR)
        assert guardado is not None, f"Precondición: el menor {DNI_MENOR} debía estar en el maestro."
        registro = await _registro(mdm_engine, guardado.id)

        assert registro.historical_documents, (
            "HALLAZGO (CA-003-01, D30): con el expediente aprobado y el lote cerrado (FINALIZED), el "
            f"registro del menor {DNI_MENOR} no tiene ningún documento para consultar "
            f"(historical_documents = {registro.historical_documents}); el expediente tenía "
            f"{sorted(case.document_ids)}."
        )
        assert len(registro.historical_documents) == 1
        assert len(drive_falso.archivos) == 1, "debía subirse un solo PDF consolidado por expediente"
        (carpeta, nombre), file_id = next(iter(drive_falso.archivos.items()))
        assert nombre.startswith(f"Dossier_Inscripcion_{DNI_MENOR}_") and nombre.endswith(".pdf")
        assert registro.historical_documents[0].file_id == file_id

    @pytest.mark.asyncio
    async def test_reintentar_la_generacion_no_duplica_el_pdf_ni_el_enlace(
        self, bus_con_mdm, sin_conexion, mdm_engine, drive_falso, monkeypatch
    ):
        """Un reintento reemplaza el archivo de Drive (mismo nombre en la carpeta del
        menor) y el enlace del registro; no queda un segundo documento."""
        publicados, casos = bus_con_mdm
        case = await _procesar_ocr(uuid4())
        await _aprobar_y_cerrar_lote(case, casos)
        evento = next(e for e in publicados if isinstance(e, BatchTriageCompletedEvent))

        await _generar_pdf_del_lote(evento, case, monkeypatch)
        await _generar_pdf_del_lote(evento, case, monkeypatch)

        assert len(drive_falso.subidas) == 2, "se esperaban dos intentos de subida"
        assert len(drive_falso.archivos) == 1, f"el reintento duplicó el PDF en Drive: {drive_falso.archivos}"
        with Session(mdm_engine) as s:
            guardado = await SqlBeneficiaryRepository(_SesionSqlite(s)).get_by_dni(DNI_MENOR)
        registro = await _registro(mdm_engine, guardado.id)
        assert len(registro.historical_documents) == 1, "el reintento duplicó el enlace en el registro del menor"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
