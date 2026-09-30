"""Rechazo en SUBMIT si el beneficiario ya está inscrito en la MISMA actividad.

Por qué estos tests existen
---------------------------
El chequeo comparaba `enrollment.activity_code` contra el literal `"EDUCA"`, pero
esa columna guarda el **UUID** de la actividad (el mismo valor que
`extraction_batches.activity_id`). La comparación no podía coincidir nunca, así
que el rechazo por inscripción duplicada nunca se disparaba al aprobar a mano:
solo funcionaba en el reprocesado (`dossier_processor`), que sí usa el UUID.

Estos tests fijan el criterio real: se rechaza al mismo beneficiario en la misma
actividad, y NO se rechaza al mismo beneficiario en otra actividad.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import (
    SubmitCorrectionUseCase, REJECT_DUPLICATE_ENROLLMENT
)
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.value_objects.enrollment import Enrollment
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI

# UUID de la actividad del lote bajo prueba. Es lo que se guarda en
# `beneficiary_enrollments.activity_code`, NO un código de texto.
ACTIVITY_ID = uuid4()
OTRA_ACTIVITY_ID = uuid4()


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
        document_ids={
            "FINS": uuid4(), "DJ": uuid4(),
            "DNIBE": uuid4(), "DNIAP": uuid4()
        },
        confidence_scores={"FINS": 0.9, "DJ": 0.9, "DNIBE": 0.9, "DNIAP": 0.9},
        status=TriageStatus.PENDING_REVIEW,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=[],
    )


def _make_existing_beneficiary(activity_codes):
    """Beneficiario ya existente en MDM, con las matrículas que se le pidan."""
    b = Beneficiary(
        id=uuid4(),
        dni=DNI("12345678"),
        first_name="Juan",
        last_name="Perez",
    )
    for code in activity_codes:
        b.enrollments.append(Enrollment(
            id=uuid4(),
            beneficiary_id=b.id,
            activity_code=code,
            enrollment_date=None
        ))
    return b


def _make_session(activity_id=ACTIVITY_ID):
    """Session mockeada cuya consulta del lote devuelve `activity_id`."""
    session = AsyncMock()
    resultado = MagicMock()
    resultado.fetchone.return_value = (str(activity_id),)
    session.execute = AsyncMock(return_value=resultado)
    return session


def _make_uc(case, existing, activity_id=ACTIVITY_ID):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=case)
    repo.save = AsyncMock()
    repo.get_all_by_batch_id = AsyncMock(return_value=[case])

    validator = MagicMock()
    validator.validate_can_be_corrected = AsyncMock()

    beneficiary_repo = MagicMock()
    beneficiary_repo.get_by_dni = AsyncMock(return_value=existing)

    uc = SubmitCorrectionUseCase(
        triage_repo=repo,
        session=_make_session(activity_id),
        beneficiary_repo=beneficiary_repo,
        status_validator=validator,
    )
    return uc, repo


class TestRejectDuplicateEnrollment:
    """Se rechaza el mismo beneficiario en la misma actividad."""

    @pytest.mark.asyncio
    async def test_rechaza_si_ya_inscrito_en_la_misma_actividad(self):
        case = _make_pending_case()
        existing = _make_existing_beneficiary([str(ACTIVITY_ID)])
        uc, repo = _make_uc(case, existing)

        await uc.execute(case.id, uuid4(), case.dossier_data)

        assert case.status == TriageStatus.REJECTED
        assert case.rejection_reason == REJECT_DUPLICATE_ENROLLMENT

        # Discrepancy con el detalle para la UI
        assert len(case.discrepancies) == 1
        disc = case.discrepancies[0]
        assert disc.field_name == "beneficiary.dni"
        assert disc.severity == "ERROR"
        assert "ya está inscrito en esta actividad" in disc.rule_description
        assert "Juan Perez" in disc.rule_description
        assert "12345678" in disc.rule_description
        assert str(existing.id) in disc.rule_description

        assert repo.save.call_count == 1
        assert len(case.pending_events) == 0

    @pytest.mark.asyncio
    async def test_no_rechaza_si_el_codigo_de_actividad_no_coincide(self):
        """El criterio real: mismo beneficiario, DISTINTA actividad -> se acepta.

        Este es el caso que antes no se podia distinguir, porque el chequeo
        comparaba contra el literal `"EDUCA"` en vez del UUID de la actividad.
        """
        case = _make_pending_case()
        existing = _make_existing_beneficiary([str(OTRA_ACTIVITY_ID)])
        uc, _ = _make_uc(case, existing)

        await uc.execute(case.id, uuid4(), case.dossier_data)

        assert case.status == TriageStatus.APPROVED
        assert case.rejection_reason is None

    @pytest.mark.asyncio
    async def test_no_rechaza_si_no_tiene_ninguna_matricula(self):
        case = _make_pending_case()
        existing = _make_existing_beneficiary([])
        uc, _ = _make_uc(case, existing)

        await uc.execute(case.id, uuid4(), case.dossier_data)

        assert case.status == TriageStatus.APPROVED
        assert case.rejection_reason is None

    @pytest.mark.asyncio
    async def test_no_rechaza_si_beneficiario_no_existe(self):
        case = _make_pending_case()
        uc, _ = _make_uc(case, None)

        await uc.execute(case.id, uuid4(), case.dossier_data)

        assert case.status == TriageStatus.APPROVED

    @pytest.mark.asyncio
    async def test_no_rechaza_si_no_se_puede_resolver_la_actividad(self):
        """Si el lote no está, no se rechaza a nadie.

        Inventar un activity_id haría matchear el beneficiario contra cualquier
        otra actividad, que es peor que no rechazar.
        """
        case = _make_pending_case()
        existing = _make_existing_beneficiary([str(ACTIVITY_ID)])

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=case)
        repo.save = AsyncMock()
        repo.get_all_by_batch_id = AsyncMock(return_value=[case])

        session = AsyncMock()
        resultado = MagicMock()
        resultado.fetchone.return_value = (None,)
        session.execute = AsyncMock(return_value=resultado)

        validator = MagicMock()
        validator.validate_can_be_corrected = AsyncMock()

        beneficiary_repo = MagicMock()
        beneficiary_repo.get_by_dni = AsyncMock(return_value=existing)

        uc = SubmitCorrectionUseCase(
            triage_repo=repo,
            session=session,
            beneficiary_repo=beneficiary_repo,
            status_validator=validator,
        )

        await uc.execute(case.id, uuid4(), case.dossier_data)

        assert case.status == TriageStatus.APPROVED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
