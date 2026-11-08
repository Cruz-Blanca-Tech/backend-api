"""D28: «vacunas completas» se guarda en su propio campo de la ficha médica del maestro."""
from uuid import uuid4

from src.contexts.core_beneficiary_management.domain.value_objects.medical_record import MedicalRecord
from src.contexts.core_beneficiary_management.infrastructure.persistence.mappers.beneficiary.medical_record_mapper import MedicalRecordMapper
from src.contexts.core_beneficiary_management.presentation.mappers.medical_dto_mapper import MedicalDtoMapper
from src.contexts.core_beneficiary_management.presentation.schemas.medical_schemas import MedicalRecordPatchRequest


def _record(flag):
    return MedicalRecord(id=uuid4(), beneficiary_id=uuid4(), has_been_hospitalized=False,
                         hospitalization_reason=None, has_been_operated=False, operation_reason=None,
                         vaccines=["BCG"], medications=[], allergies=[], diseases=[], insurance=[],
                         has_complete_vaccines=flag)


def test_ida_y_vuelta_por_la_base_conserva_el_campo():
    for flag in (True, False, None):
        rec = _record(flag)
        back = MedicalRecordMapper.to_domain(MedicalRecordMapper.to_persistence(rec, rec.beneficiary_id))
        assert back.has_complete_vaccines is flag
        assert back.vaccines == ["BCG"]


def test_la_api_devuelve_el_campo():
    assert MedicalDtoMapper.to_response(_record(True)).has_complete_vaccines is True


def test_el_patch_puede_corregirlo():
    rec = MedicalDtoMapper.patch_domain(_record(None), MedicalRecordPatchRequest(has_complete_vaccines=True), uuid4())
    assert rec.has_complete_vaccines is True
