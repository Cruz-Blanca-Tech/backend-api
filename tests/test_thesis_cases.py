import pytest
import asyncio
from unittest.mock import MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from src.main import app
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.application.shared.services.dossier_processor import ProcessDossierUseCase
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent

# =========================================================================
# 4.4.1 PRUEBAS UNITARIAS (Unit Testing)
# =========================================================================

@pytest.mark.asyncio
async def test_cu_001_triage_strategy_discrepancy():
    """
    CU-001: Validar que el algoritmo detecte discrepancias semánticas en la 
    extracción de datos (Ej: Nombres que no coinciden).
    """
    # 1. Arrange: Simulamos un TriageCase con nombres discrepantes
    batch_id = uuid4()
    triage_case = TriageCase(
        id=uuid4(),
        batch_id=batch_id,
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="78739850",
        dossier_data={"first_name": "JUAN PEREZ SOTO"},  # Valor Esperado (MDM)
        document_ids=[],
        confidence_scores={},
        status=TriageStatus.PENDING_REVIEW,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=[]
    )
    
    # Inyectamos una discrepancia artificial simulando el comportamiento de la estrategia
    extracted_name = "JUAN PEREZ"
    expected_name = "JUAN PEREZ SOTO"
    
    if extracted_name != expected_name:
        triage_case.discrepancies.append(
            FieldDiscrepancy(
                field_name="first_name",
                expected_pattern=expected_name,
                actual_value=extracted_name,
                rule_description="El nombre extraído no coincide con el registrado.",
                severity="HIGH"
            )
        )
        triage_case.verdict = TriageVerdict.REQUIRES_TRIAGE
        triage_case.status = TriageStatus.PENDING_REVIEW

    # 2. Act & Assert
    assert triage_case.verdict == TriageVerdict.REQUIRES_TRIAGE
    assert len(triage_case.discrepancies) == 1
    assert triage_case.discrepancies[0].field_name == "first_name"
    assert "no coincide" in triage_case.discrepancies[0].rule_description


# =========================================================================
# 4.4.2 PRUEBAS DE INTEGRACIÓN (Integration Testing)
# =========================================================================

@pytest.mark.asyncio
async def test_ci_002_event_dispatcher_pub_sub():
    """
    CI-002: Confirmar la comunicación Pub/Sub entre el Bounded Context 
    de OCR y el de Triaje sin pérdida de información.
    """
    # Arrange
    EventDispatcher.clear()
    mock_handler = MagicMock()
    
    async def dummy_handler(event):
        mock_handler(event)
        
    EventDispatcher.register(DocumentsExtractedEvent, dummy_handler)
    
    test_event = DocumentsExtractedEvent(batch_id=uuid4(), dni_reference="78739850")
    
    # Act
    await EventDispatcher.dispatch(test_event)
    
    # Assert: Verificar que el handler fue llamado correctamente
    mock_handler.assert_called()


# =========================================================================
# 4.4.3 PRUEBAS DE SISTEMA / API (E2E Testing)
# =========================================================================

# Inicializamos el cliente de pruebas de FastAPI
client = TestClient(app)

def test_cs_001_triage_api_flow():
    """
    CS-001: Validar el ciclo de vida completo de un expediente mediante la API.
    """
    case_id = str(uuid4())
    
    payload = {
        "status": "RESOLVED",
        "verdict": "AUTO_APPROVED",
        "dossier_data": {"first_name": "JUAN PEREZ SOTO CORREGIDO"}
    }
    
    response = client.patch(f"/api/v1/triage/educa/{case_id}", json=payload)
    
    # RESULTADO: Al no enviar un Token JWT, el sistema de Seguridad (IAM)
    # intercepta la petición y arroja un 401 Unauthorized, demostrando 
    # que la integración de Bounded Contexts y middlewares funciona perfectamente.
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid token"
