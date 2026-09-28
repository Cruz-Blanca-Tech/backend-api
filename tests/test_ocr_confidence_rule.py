import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from src.contexts.data_quality_triage.domain.educa.rules.document.confidence_rules import OcrConfidenceRule
from src.contexts.data_quality_triage.domain.shared.strategies.inscription_strategy import InscriptionTriageStrategy
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict


def _doc(code: str, confidence) -> DocumentDTO:
    return DocumentDTO(
        id=uuid4(),
        file_name=f"x_{code}.jpg",
        document_code=code,
        extracted_data={},
        confidence_score=confidence,
    )


def _make_strategy() -> InscriptionTriageStrategy:
    strategy = InscriptionTriageStrategy()
    strategy._mapper = MagicMock()
    strategy._mapper.map.return_value = {}
    strategy._validator = MagicMock()
    strategy._validator.validate.return_value = []
    return strategy


def _issues_with_field(discrepancies, field_name: str):
    return [d for d in discrepancies if d.field_name == field_name]


@pytest.mark.asyncio
async def test_strategy_low_confidence_discrepancy_and_triage():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.45), _doc("FINS", 0.90)],
        context={"confidence_thresholds": {"DJ": 0.55, "FINS": 0.60}},
    )

    conf_issues = _issues_with_field(case.discrepancies, "general_confidence")
    assert len(conf_issues) == 1
    assert conf_issues[0].document_code == "DJ"
    assert conf_issues[0].severity == "WARNING"

    # Los scores se propagan al caso (lo que la UI usa como min_confidence_score)
    assert case.confidence_scores == {"DJ": 0.45, "FINS": 0.90}
    assert case.status == TriageStatus.PENDING_REVIEW
    assert case.verdict == TriageVerdict.REQUIRES_TRIAGE


@pytest.mark.asyncio
async def test_strategy_high_confidence_no_confidence_discrepancy():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.74), _doc("FINS", 0.70)],
        context={"confidence_thresholds": {"DJ": 0.55, "FINS": 0.60}},
    )
    assert _issues_with_field(case.discrepancies, "general_confidence") == []


@pytest.mark.asyncio
async def test_strategy_single_float_threshold_via_context():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.55), _doc("FINS", 0.70)],
        context={"confidence_threshold": 0.60},
    )
    conf_issues = _issues_with_field(case.discrepancies, "general_confidence")
    assert [d.document_code for d in conf_issues] == ["DJ"]


@pytest.mark.asyncio
async def test_strategy_threshold_dict_vs_float_priority():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.55), _doc("FINS", 0.70)],
        context={
            "confidence_thresholds": {"DJ": 0.55, "FINS": 0.60},
            "confidence_threshold": 0.60,
        },
    )
    conf_issues = _issues_with_field(case.discrepancies, "general_confidence")
    # El dict tiene prioridad: DJ 0.55 -> OK, FINS 0.60 -> OK
    assert _issues_with_field(case.discrepancies, "general_confidence") == []


@pytest.mark.asyncio
async def test_strategy_missing_threshold_uses_default():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.55), _doc("FINS", 0.70)],
        context={},
    )
    conf_issues = _issues_with_field(case.discrepancies, "general_confidence")
    # Default 0.80 -> DJ 0.55 WARNING, FINS 0.70 WARNING
    assert len(conf_issues) == 2
    codes = {d.document_code for d in conf_issues}
    assert codes == {"DJ", "FINS"}