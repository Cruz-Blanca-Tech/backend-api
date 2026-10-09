"""RF-11 / ISO/IEC 27001 A.8.11: enmascarado de datos personales en el servidor."""
from datetime import date
from uuid import uuid4

from src.contexts.core_beneficiary_management.presentation.mappers.privacy_mask import (
    mask_dni, mask_first_name, mask_last_name, mask_summary,
)
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import BeneficiarySummaryResponse


def test_dni_solo_muestra_los_ultimos_4_digitos():
    assert mask_dni("12345678") == "****5678"
    assert mask_dni("") == ""


def test_nombres_se_reducen_a_iniciales():
    assert mask_first_name("Carlos Andrés") == "C A****"
    assert mask_last_name("Condori Li") == "C**** L*"


def test_mask_summary_no_deja_datos_personales():
    item = BeneficiarySummaryResponse(
        id=uuid4(), dni="12345678", first_name="Luis", last_name="Quispe Flores",
        birth_date=date(2015, 3, 1), age=11, gender="MALE", is_active=True, grade="5TO_PRIMARIA",
    )
    masked = mask_summary(item)
    assert masked.dni == "****5678"
    assert masked.first_name == "L"
    assert masked.last_name == "Q**** F****"
    assert masked.birth_date is None
    # Datos agregables se conservan
    assert masked.age == 11 and masked.grade == "5TO_PRIMARIA"
    # El original no se modifica
    assert item.dni == "12345678"
