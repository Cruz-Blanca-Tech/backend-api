"""Pruebas unitarias de regresión y verificación para los defectos del Grupo 1:
- D29: Aceptación de teléfonos fijos peruanos además de celulares
- D7: Mapeo y no descarte de disease_when_and_treatment en ficha médica
- D28: Preservación de has_complete_vaccines en ficha médica y DTO
- D17: Separación inteligente de nombres y apellidos de adultos (evitar truncar en primer espacio)
- D22: Validación estricta de nombres y apellidos en esquemas backend (rechazo de vacíos / 1 letra)
- D30: Disparo de BatchTriageCompletedEvent al finalizar lote automáticamente
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import _is_valid_phone
from src.contexts.data_quality_triage.domain.shared.value_objects.phone_number import PhoneNumber
from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone

from src.contexts.data_quality_triage.domain.educa.mappers.medical_domain_mapper import MedicalDomainMapper
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedMedical
from src.contexts.data_quality_triage.domain.shared.value_objects.enriched_field import EnrichedField

from src.contexts.core_beneficiary_management.application.dtos.educa_dossier_dto import (
    EducaDossierDTO, EducaBeneficiaryDTO, EducaMedicalDTO, EducaAdultDTO, EducaRelatedAdultsDTO
)
from src.contexts.core_beneficiary_management.application.mappers.educa_dossier_mapper import (
    EducaDossierMapper, _build_adult
)
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import BeneficiaryCreateRequest

from src.contexts.data_quality_triage.application.shared.use_cases.finalize_batch_if_complete_use_case import (
    FinalizeBatchIfCompleteUseCase
)
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus


# ==============================================================================
# D29: Teléfonos fijos y celulares
# ==============================================================================
class TestD29PhoneValidation:
    @pytest.mark.parametrize("valid_phone", [
        "987654321",           # Celular 9 dígitos
        "+51 987 654 321",     # Celular con prefijo internacional
        "51987654321",         # Celular con 51
        "4567890",             # Fijo 7 dígitos (Lima)
        "014567890",           # Fijo con código de área Lima (01)
        "(01) 456-7890",       # Fijo formateado
        "+51014567890",        # Fijo con código país y área
        "+51 1 456 7890",      # Fijo internacional
    ])
    def test_d29_telefonos_validos_celulares_y_fijos(self, valid_phone):
        assert _is_valid_phone(valid_phone) is True
        assert PhoneNumber.is_valid(valid_phone) is True
        vo = Phone(valid_phone)
        assert vo.value == valid_phone

    @pytest.mark.parametrize("invalid_phone", [
        "",
        "   ",
        "123",                 # Muy corto
        "530045",              # 6 dígitos
        "47000001",            # 8 dígitos (DNI, no teléfono)
        "98765432",            # 8 dígitos celular incompleto
        "9876543210",          # 10 dígitos celular
        "900000021-900000022", # Dos teléfonos concatenados
    ])
    def test_d29_telefonos_invalidos_rechazados(self, invalid_phone):
        assert _is_valid_phone(invalid_phone) is False
        assert PhoneNumber.is_valid(invalid_phone) is False
        if invalid_phone:
            with pytest.raises(ValueError):
                Phone(invalid_phone)


# ==============================================================================
# D7: disease_when_and_treatment no se descarta
# ==============================================================================
class TestD7DiseaseWhenAndTreatmentMapping:
    def test_d7_texto_libre_de_enfermedad_se_agrega_a_diseases(self):
        mapper = MedicalDomainMapper()
        
        mock_med = MagicMock()
        mock_med.allergy_milk.normalized_value = False
        mock_med.allergy_citrus.normalized_value = False
        mock_med.allergy_penicillin.normalized_value = False
        mock_med.allergy_sulfa_drugs.normalized_value = False
        mock_med.allergy_fish_shellfish.normalized_value = False
        mock_med.allergy_nsaid_analgesics.normalized_value = False
        mock_med.allergy_others.normalized_value = None

        mock_med.disease_cancer.normalized_value = False
        mock_med.disease_seizures.normalized_value = False
        mock_med.disease_parasites.normalized_value = False
        mock_med.disease_chickenpox.normalized_value = True
        mock_med.disease_tuberculosis.normalized_value = False
        mock_med.disease_when_and_treatment.normalized_value = "Asma bronquial con inhalador"

        mock_med.medical_insurance_sis.normalized_value = False
        mock_med.medical_insurance_essalud.normalized_value = False
        mock_med.medical_insurance_fospoli.normalized_value = False
        mock_med.medical_insurance_other.normalized_value = None

        mock_med.received_tetanus_vaccine.normalized_value = False
        mock_med.is_taking_medication.normalized_value = False
        mock_med.medication_name.normalized_value = None
        mock_med.operation_reason.normalized_value = None
        mock_med.hospitalization_reason.normalized_value = None
        mock_med.has_been_operated.normalized_value = False
        mock_med.has_been_hospitalized.normalized_value = False
        mock_med.has_complete_vaccines.normalized_value = False

        mock_fins = MagicMock(spec=EnrichedFins)
        mock_fins.medical = mock_med
        
        result = mapper.map(mock_fins)
        assert "Varicela" in result.diseases
        assert "Asma Bronquial Con Inhalador" in result.diseases


# ==============================================================================
# D28: has_complete_vaccines preservado en DTO y m.vaccines
# ==============================================================================
class TestD28CompleteVaccinesPreservation:
    def test_d28_has_complete_vaccines_se_guarda_en_su_campo(self):
        dto = EducaDossierDTO(
            beneficiary=EducaBeneficiaryDTO(dni="10000001", first_name="JUAN", last_name="PEREZ LOPEZ"),
            medical=EducaMedicalDTO(
                has_complete_vaccines=True,
                vaccines=["Antitetánica"]
            )
        )
        
        entity = EducaDossierMapper.map_to_entity(dto)
        assert entity.medical_record.vaccines == ["Antitetánica"]
        assert entity.medical_record.has_complete_vaccines is True

    def test_d28_has_complete_vaccines_false_no_agrega_completas(self):
        dto = EducaDossierDTO(
            beneficiary=EducaBeneficiaryDTO(dni="10000001", first_name="JUAN", last_name="PEREZ LOPEZ"),
            medical=EducaMedicalDTO(
                has_complete_vaccines=False,
                vaccines=["Antitetánica"]
            )
        )
        
        entity = EducaDossierMapper.map_to_entity(dto)
        assert "Antitetánica" in entity.medical_record.vaccines
        assert "COMPLETAS" not in entity.medical_record.vaccines
        assert entity.medical_record.has_complete_vaccines is False


# ==============================================================================
# D17: Separación inteligente de nombres de adultos
# ==============================================================================
class TestD17AdultNameSplitting:
    @pytest.mark.parametrize("full_name, expected_first, expected_last", [
        ("JUAN CARLOS PEREZ LOPEZ", "JUAN CARLOS", "PEREZ LOPEZ"),
        ("MARIA ELENA SOTO QUISPE", "MARIA ELENA", "SOTO QUISPE"),
        ("MARIA ELENA CASTILLO", "MARIA", "ELENA CASTILLO"),
        ("CARLOS PEREZ", "CARLOS", "PEREZ"),
        ("PEDRO", "PEDRO", ""),
        ("ANA MARIA DEL CARMEN DIAZ PEREZ", "ANA MARIA DEL CARMEN", "DIAZ PEREZ"),
    ])
    def test_d17_build_adult_preserva_nombres_compuestos_correctamente(self, full_name, expected_first, expected_last):
        ad_dto = EducaAdultDTO(dni="10000001", full_name=full_name, relationship="FATHER")
        dossier_dto = MagicMock()
        dossier_dto.related_adults.emergency_contact_dni = None
        dossier_dto.related_adults.guardian_dni = None

        adult = _build_adult(ad_dto, dossier_dto, "10000001")
        assert adult is not None
        assert adult.first_name == expected_first
        assert adult.last_name == expected_last


# ==============================================================================
# D22: Validación estricta de nombres y apellidos
# ==============================================================================
class TestD22NameValidation:
    def test_d22_rechaza_nombres_vacios_o_espacios(self):
        with pytest.raises(ValueError):
            BeneficiaryCreateRequest(dni="10000001", first_name="", last_name="PEREZ")
        
        with pytest.raises(ValueError):
            BeneficiaryCreateRequest(dni="10000001", first_name="JUAN", last_name="   ")

        with pytest.raises(ValueError):
            BeneficiaryCreateRequest(dni="10000001", first_name="A", last_name="PEREZ") # 1 letra

        with pytest.raises(ValueError):
            EducaBeneficiaryDTO(dni="10000001", first_name="JUAN", last_name=" ")

    def test_d22_acepta_nombres_validos_y_hace_strip(self):
        req = BeneficiaryCreateRequest(dni="10000001", first_name="  JUAN CARLOS  ", last_name="  PEREZ LOPEZ ")
        assert req.first_name == "JUAN CARLOS"
        assert req.last_name == "PEREZ LOPEZ"


# ==============================================================================
# D30: Disparo de BatchTriageCompletedEvent en finalización automática
# ==============================================================================
class TestD30AutomaticBatchFinalizeDispatchesPdfEvent:
    @pytest.mark.asyncio
    async def test_d30_finalize_batch_if_complete_dispatches_event(self):
        batch_id = uuid4()
        case_id = uuid4()

        mock_case = MagicMock()
        mock_case.status = TriageStatus.APPROVED
        mock_case.sync_status = "SYNCED"
        mock_case.dni_reference = "10000001"
        mock_case.dossier_data = {"beneficiary": {"dni": "10000001"}}
        mock_case.document_ids = {"FINS": uuid4(), "DJ": uuid4()}

        mock_triage_repo = MagicMock()
        mock_triage_repo.get_all_by_batch_id = AsyncMock(return_value=[mock_case])

        mock_session = MagicMock()
        mock_lote = MagicMock()
        mock_lote.status = BatchStatus.COMPLETED.value
        mock_session.get = AsyncMock(return_value=mock_lote)
        mock_session.execute = AsyncMock()

        use_case = FinalizeBatchIfCompleteUseCase(session=mock_session, triage_repo=mock_triage_repo)

        with patch("src.core.events.event_dispatcher.EventDispatcher.dispatch_background") as mock_dispatch:
            status = await use_case.execute(batch_id)
            assert status == BatchStatus.FINALIZED.value
            assert mock_dispatch.called
            event = mock_dispatch.call_args[0][0]
            assert event.batch_id == batch_id
            assert "10000001" in event.approved_dossiers
