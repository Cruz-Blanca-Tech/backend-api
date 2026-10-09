import pytest
from unittest.mock import MagicMock
from src.contexts.data_quality_triage.domain.educa.mappers.beneficiary_domain_mapper import BeneficiaryDomainMapper

def test_beneficiary_domain_mapper_with_related_adults():
    mapper = BeneficiaryDomainMapper()

    # Mock enriched_fins
    enriched_fins = MagicMock()
    enriched_fins.child_first_name.normalized_value = "JUAN CARLOS PEREZ"
    enriched_fins.child_last_name.normalized_value = "GOMEZ"
    enriched_fins.child_dni.normalized_value = "77665544"
    enriched_fins.child_birth_date.normalized_value = "2015-05-10"
    enriched_fins.child_gender.normalized_value = "M"
    enriched_fins.child_age.normalized_value = 10
    enriched_fins.address_line.normalized_value = "Av. Lima 123"
    enriched_fins.address_reference.normalized_value = "Frente al parque"
    enriched_fins.address_district.normalized_value = "Callao"
    enriched_fins.address_province.normalized_value = "Callao"
    enriched_fins.address_department.normalized_value = "Lima"
    enriched_fins.adults = []

    # Mock related_adults with father and mother
    adult_father = MagicMock()
    adult_father.relationship.value = "FATHER"
    adult_father.full_name = "CARLOS PEREZ LOPEZ"

    adult_mother = MagicMock()
    adult_mother.relationship.value = "MOTHER"
    adult_mother.full_name = "ANA GOMEZ DIAZ"

    related_adults = MagicMock()
    related_adults.adults = [adult_father, adult_mother]

    beneficiary = mapper.map(enriched_fins, related_adults=related_adults)

    assert beneficiary.first_name == "JUAN CARLOS"
    assert "PEREZ" in beneficiary.last_name
    assert "GOMEZ" in beneficiary.last_name
    assert beneficiary.dni == "77665544"
    assert beneficiary.birth_date == "2015-05-10"

def test_beneficiary_domain_mapper_fallback_to_dnibe():
    mapper = BeneficiaryDomainMapper()

    # Enriched fins has empty child names/dni/dob
    enriched_fins = MagicMock()
    enriched_fins.child_first_name = None
    enriched_fins.child_last_name = None
    enriched_fins.child_dni = None
    enriched_fins.child_birth_date = None
    enriched_fins.child_gender = None
    enriched_fins.child_age = None
    enriched_fins.address_line = None
    enriched_fins.address_reference = None
    enriched_fins.address_district = None
    enriched_fins.address_province = None
    enriched_fins.address_department = None

    # Adults in enriched_fins
    adult1 = MagicMock()
    adult1.role.value = "PADRE"
    adult1.first_name.normalized_value = "ROBERTO"
    adult1.last_name.normalized_value = "SANCHEZ"

    adult2 = MagicMock()
    adult2.role.value = "MADRE"
    adult2.first_name.normalized_value = "MARIA"
    adult2.last_name.normalized_value = "FLORES"

    enriched_fins.adults = [adult1, adult2]

    # Mock dnibe fallback
    dnibe = MagicMock()
    dnibe.first_name.normalized_value = "LUCAS"
    dnibe.last_name.normalized_value = "SANCHEZ FLORES"
    dnibe.document_number.normalized_value = "88990011"
    dnibe.date_of_birth.normalized_value = "2016-08-20"
    dnibe.address_line.normalized_value = "Jr. Junin 456"
    dnibe.district.normalized_value = "Rimac"
    dnibe.province.normalized_value = "Lima"
    dnibe.department.normalized_value = "Lima"

    beneficiary = mapper.map(enriched_fins, enriched_dnibe=dnibe)

    assert beneficiary.first_name == "LUCAS"
    assert beneficiary.last_name == "SANCHEZ FLORES"
    assert beneficiary.dni == "88990011"
    assert beneficiary.birth_date == "2016-08-20"
