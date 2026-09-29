"""Test para rechazo de inscripción duplicada en SubmitCorrectionUseCase.

Verifica que al hacer submit de una corrección para un beneficiario que YA
está inscrito en EDUCA, el caso se rechace con REJECT_DUPLICATE_ENROLLMENT
en lugar de aprobarse y disparar evento a MDM.
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import (
    SubmitCorrectionUseCase, REJECT_DUPLICATE_ENROLLMENT
)
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
from src.contexts.core_beneficiary_management.domain.value_objects.enrollment import Enrollment
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI


def _make_pending_case():
    return TriageCase(
        id=uuid4(),
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="12345678",
        dossier_data={
            "beneficiary": {
                "dni": "12345678", 
                "first_name": "Juan", 
                "last_name": "Perez", 
                "gender": "M",
                "birth_date": "2015-06-15",
                "age": 9,
                "address": "Av. Siempre Viva 123"
            },
            "related_adults": {
                "adults": [
                    {
                        "dni": "87654321",
                        "full_name": "Maria Perez",  # Apellido coincide con beneficiario
                        "relationship": "MOTHER",
                        "phone": "987654321",
                        "is_guardian": True,
                        "is_emergency_contact": True
                    }
                ],
                "guardian_dni": "87654321",
                "emergency_contact_dni": "87654321"
            },
            "education": {
                "school": "COLEGIO SAN MARTIN",
                "grade": "3RO_PRIMARIA",
                "knows_how_to_read": True,
                "knows_how_to_write": True
            }
        },
        # Documentos requeridos para EDUCA_INSCRIPTION
        document_ids={
            "FINS": uuid4(), "DJ": uuid4(), 
            "DNIBE": uuid4(), "DNIAP": uuid4()
        },
        confidence_scores={"FINS": 0.9, "DJ": 0.9, "DNIBE": 0.9, "DNIAP": 0.9},
        status=TriageStatus.PENDING_REVIEW,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=[],
    )


def _make_existing_beneficiary(with_educa=True):
    """Crea un beneficiario ya existente en MDM."""
    b = Beneficiary(
        id=uuid4(),
        dni=DNI("12345678"),
        first_name="Juan",
        last_name="Perez",
    )
    if with_educa:
        b.enrollments.append(Enrollment(
            id=uuid4(),
            beneficiary_id=b.id,
            activity_code="EDUCA",
            enrollment_date=None
        ))
    return b


class TestRejectDuplicateEnrollment:
    """Rechazo en SUBMIT si el beneficiario ya está inscrito en EDUCA."""

    @pytest.mark.asyncio
    async def test_rechaza_si_ya_inscrito_en_educa(self):
        case = _make_pending_case()
        existing = _make_existing_beneficiary(with_educa=True)

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=case)
        repo.save = AsyncMock()
        session = AsyncMock()
        validator = MagicMock()
        validator.validate_can_be_corrected = AsyncMock()

        beneficiary_repo = MagicMock()
        beneficiary_repo.get_by_dni = AsyncMock(return_value=existing)

        uc = SubmitCorrectionUseCase(
            triage_repo=repo,
            session=session,
            beneficiary_repo=beneficiary_repo,
            status_validator=validator
        )

        await uc.execute(case.id, uuid4(), case.dossier_data)

        # Verificaciones
        assert case.status == TriageStatus.REJECTED
        assert case.rejection_reason == REJECT_DUPLICATE_ENROLLMENT

        # Discrepancy con el detalle para la UI
        assert len(case.discrepancies) == 1
        disc = case.discrepancies[0]
        assert disc.field_name == "beneficiary.dni"
        assert disc.severity == "ERROR"
        assert "ya está inscrito en EDUCA" in disc.rule_description
        assert "Juan Perez" in disc.rule_description
        assert "12345678" in disc.rule_description
        assert str(existing.id) in disc.rule_description

        # Audit log con razón
        # El repo.save se llama una vez (no hay evento despachado)
        assert repo.save.call_count == 1
        # No se disparan eventos
        assert len(case.pending_events) == 0

    @pytest.mark.asyncio
    async def test_no_rechaza_si_no_tiene_educa(self):
        """Si el beneficiario existe pero NO tiene EDUCA, sigue flujo normal."""
        case = _make_pending_case()
        existing = _make_existing_beneficiary(with_educa=False)

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=case)
        repo.save = AsyncMock()
        session = AsyncMock()
        validator = MagicMock()
        validator.validate_can_be_corrected = AsyncMock()

        beneficiary_repo = MagicMock()
        beneficiary_repo.get_by_dni = AsyncMock(return_value=existing)

        uc = SubmitCorrectionUseCase(
            triage_repo=repo,
            session=session,
            beneficiary_repo=beneficiary_repo,
            status_validator=validator
        )

        await uc.execute(case.id, uuid4(), case.dossier_data)

        # No rechaza: sigue a approve si está completo
        assert case.status == TriageStatus.APPROVED
        assert case.rejection_reason is None

    @pytest.mark.asyncio
    async def test_no_rechaza_si_beneficiario_no_existe(self):
        """Beneficiario nuevo: flujo normal."""
        case = _make_pending_case()

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=case)
        repo.save = AsyncMock()
        session = AsyncMock()
        validator = MagicMock()
        validator.validate_can_be_corrected = AsyncMock()

        beneficiary_repo = MagicMock()
        beneficiary_repo.get_by_dni = AsyncMock(return_value=None)

        uc = SubmitCorrectionUseCase(
            triage_repo=repo,
            session=session,
            beneficiary_repo=beneficiary_repo,
            status_validator=validator
        )

        await uc.execute(case.id, uuid4(), case.dossier_data)

        assert case.status == TriageStatus.APPROVED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])