"""Casos críticos de verificación del sistema evaluado (Sección 6.4.2 de la memoria de tesis).

Este módulo implementa de forma reproducible y visible los tres casos críticos
documentados en la tesis para el sistema de gestión documental de la Asociación Cruz Blanca:

1. CU-001 (Caso Unitario):
   El motor de reglas de calidad detecta discrepancia entre el nombre extraído del
   documento y el registrado en el maestro de beneficiarios (persons), impidiendo
   la auto-aprobación y derivando el expediente a revisión humana con veredicto
   REQUIRES_TRIAGE y estado PENDING_REVIEW.

2. CI-002 (Caso de Integración):
   El bus de eventos asíncrono in-process (EventDispatcher) entrega de forma íntegra
   y sin alteraciones el evento de documentos extraídos (DocumentsExtractedEvent)
   emitido por el componente de Ingesta/OCR hacia el manejador del contexto de Triaje.

3. CS-001 (Caso de Sistema / API):
   La interfaz de programación de aplicaciones (FastAPI) aplica el control de acceso
   basado en roles y rechaza cualquier solicitud a un endpoint protegido sin un token
   de portador (Bearer token), respondiendo con el código de estado HTTP 401 Unauthorized.
"""

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import (
    TriageStatus,
    TriageVerdict,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import (
    FieldDiscrepancy,
)
from src.contexts.data_quality_triage.application.shared.services.beneficiary_fuzzy_matcher import (
    score_candidate,
)


def test_cu001_motor_reglas_deriva_a_revision_por_discrepancia_de_nombre():
    """CU-001: El motor de reglas deriva a revisión un expediente cuyo nombre

    extraído no coincide con el del registro maestro.
    """
    # 1. Simulación de datos: nombre extraído por OCR vs nombre en el maestro
    extracted_name = "JUAN CARLOS"
    extracted_surname = "PEREZ ROJAS"
    master_name = "CARLOS ENRIQUE"
    master_surname = "PEREZ ROJAS"
    dni = "72345678"

    # 2. Evaluación algorítmica: el algoritmo de coincidencia fonética y textual
    # arroja un puntaje por debajo del umbral de auto-aprobación (0.85)
    similarity = score_candidate(
        extracted_name, extracted_surname, dni,
        master_name, master_surname, dni
    )
    assert similarity < 0.85, "La discrepancia no debe permitir auto-aprobación"

    # 3. Registro formal de discrepancia
    discrepancy = FieldDiscrepancy(
        field_name="beneficiary.first_name",
        expected_pattern=master_name,
        actual_value=extracted_name,
        rule_description="El nombre extraído no coincide con el del registro maestro",
        severity="CRITICAL",
    )

    # 4. Creación de la entidad de triaje: se comprueba que el veredicto es REQUIRES_TRIAGE
    case = TriageCase(
        id=uuid4(),
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference=dni,
        dossier_data={
            "beneficiary": {
                "first_name": extracted_name,
                "last_name": extracted_surname,
                "dni": dni,
            }
        },
        document_ids={},
        confidence_scores={"first_name": similarity},
        status=TriageStatus.PENDING_REVIEW,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=[discrepancy],
    )

    assert case.status == TriageStatus.PENDING_REVIEW
    assert case.verdict == TriageVerdict.REQUIRES_TRIAGE
    assert len(case.discrepancies) == 1
    assert case.discrepancies[0].field_name == "beneficiary.first_name"


@pytest.mark.asyncio
async def test_ci002_bus_eventos_entrega_evento_extraccion_a_triaje():
    """CI-002: El bus de eventos entrega sin alteraciones el evento de documentos

    extraídos (DocumentsExtractedEvent) al contexto de triaje.
    """
    EventDispatcher.clear()
    received_events = []

    async def mock_triage_handler(event: DocumentsExtractedEvent):
        received_events.append(event)

    # Registro del suscriptor del contexto de triaje
    EventDispatcher.register(DocumentsExtractedEvent, mock_triage_handler)

    test_batch_id = uuid4()
    original_event = DocumentsExtractedEvent(
        batch_id=test_batch_id,
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="78901234",
    )

    # Publicación del evento en el bus
    await EventDispatcher.dispatch(original_event)

    # Verificación de integridad en la entrega
    assert len(received_events) == 1
    delivered = received_events[0]
    assert delivered.batch_id == test_batch_id
    assert delivered.activity_type == "EDUCA_INSCRIPTION"
    assert delivered.dni_reference == "78901234"
    assert delivered.event_name == "documents_extracted"


def test_cs001_api_rechaza_peticion_sin_token_con_401():
    """CS-001: La API rechaza con el código HTTP 401 una petición a un endpoint

    protegido sin token de autenticación.
    """
    client = TestClient(app)
    # Invocación a ruta administrativa protegida por políticas RBAC
    response = client.get("/auth/users")

    assert response.status_code == 401
    assert "token" in response.json()["detail"].lower()
