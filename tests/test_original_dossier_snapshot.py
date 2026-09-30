import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.infrastructure.persistence.mappers.triage_case_mapper import TriageCaseMapper
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import SubmitCorrectionUseCase


ORIGINAL_PRINCIPAL = {"beneficiary": {"dni": "11111111", "first_name": "ANA"}}
CORRECTED_FINAL = {"beneficiary": {"dni": "11111111", "first_name": "ANA MARIA"}}


def _make_case(**overrides) -> TriageCase:
    params = dict(
        id=uuid4(),
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="11111111",
        dossier_data=dict(ORIGINAL_PRINCIPAL),
        document_ids={},
        confidence_scores={},
        status=TriageStatus.PENDING_REVIEW,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=[],
    )
    params.update(overrides)
    return TriageCase(**params)


def test_create_from_quality_result_snapshots_original():
    doc = DocumentDTO(
        id=uuid4(), file_name="fins.jpg", document_code="FINS",
        extracted_data={}, confidence_score=0.9,
    )
    result = QualityRuleResult(is_valid=True, discrepancies=[], confidence_passed=True, enriched_docs={})
    case = TriageCase.create_from_quality_result(
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="11111111",
        documents=[doc],
        quality_result=result,
        dossier_data=dict(ORIGINAL_PRINCIPAL),
    )
    # En la creación, el "primer JSON" es el propio dossier_data post-LLM.
    assert case.original_dossier_data == ORIGINAL_PRINCIPAL
    assert case.dossier_data == case.original_dossier_data


def test_submit_correction_keeps_original_snapshot():
    case = _make_case(original_dossier_data=dict(ORIGINAL_PRINCIPAL))
    case.submit_correction(dict(CORRECTED_FINAL), uuid4())
    assert case.dossier_data == CORRECTED_FINAL
    assert case.original_dossier_data == ORIGINAL_PRINCIPAL  # no se sobrescribe


def test_mapper_round_trip_preserves_original():
    case = _make_case(original_dossier_data=dict(ORIGINAL_PRINCIPAL))
    model = TriageCaseMapper.to_model(case)
    domain = TriageCaseMapper.to_domain(model)
    assert domain.original_dossier_data == ORIGINAL_PRINCIPAL
    assert domain.id == case.id
    assert domain.dossier_data == ORIGINAL_PRINCIPAL


@pytest.mark.asyncio
async def test_submit_correction_use_case_captures_original_when_missing():
    # Caso previo al rollout: original_dossier_data = None. La primera
    # corrección debe capturar el dossier_data actual como "primer JSON".
    case = _make_case(original_dossier_data=None)
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=case)
    repo.save = AsyncMock()
    # El cierre de lote lee los casos del lote para ver si ya se cerrará solo.
    repo.get_all_by_batch_id = AsyncMock(return_value=[case])
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    validator = MagicMock()
    validator.validate_can_be_corrected = AsyncMock()
    
    # Mock beneficiary_repo para el check de duplicado
    beneficiary_repo = MagicMock()
    beneficiary_repo.get_by_dni = AsyncMock(return_value=None)

    uc = SubmitCorrectionUseCase(
        triage_repo=repo, 
        session=session, 
        beneficiary_repo=beneficiary_repo,
        status_validator=validator
    )
    await uc.execute(case.id, uuid4(), dict(CORRECTED_FINAL))

    # Snapshot capturado antes de sobrescribir, y final aplicado.
    assert case.original_dossier_data == ORIGINAL_PRINCIPAL
    assert case.dossier_data == CORRECTED_FINAL
    assert case.original_dossier_data != case.dossier_data