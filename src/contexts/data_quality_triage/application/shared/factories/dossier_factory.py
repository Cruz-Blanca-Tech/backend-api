from typing import Dict, Any, Optional
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.value_objects.dossier_data import DossierData
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier
from src.contexts.data_quality_triage.domain.educa.mappers.educa_inscription_domain_mapper import EducaInscriptionDomainMapper
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedDj
from src.contexts.data_quality_triage.application.educa.schemas.educa_inscription_schemas import EducaInscriptionRequest
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData


class DossierFactory:
    
    @staticmethod
    def reconstitute(raw_data: dict, activity_type: ActivityType) -> DossierData:
        """
        Toma los datos crudos de la BD (el request payload guardado) y los convierte en tu entidad estricta de dominio.
        """
        if activity_type == ActivityType.EDUCA_INSCRIPTION:
            # Validamos con el schema de Pydantic para asegurar que la estructura es correcta
            validated_schema = EducaInscriptionRequest.model_validate(raw_data)
            
            # Mapeamos desde el schema validado a la entidad de dominio (dataclass)
            ben_dict = validated_schema.beneficiary.model_dump()
            edu_dict = validated_schema.education.model_dump()
            med_dict = validated_schema.medical.model_dump()
            fam_dict = validated_schema.related_adults.model_dump()
            
            adults_list = [RelatedAdult(**ad_data) for ad_data in fam_dict.get("adults", [])]
            family_obj = FamilyData(
                adults=adults_list,
                guardian_dni=fam_dict.get("guardian_dni")
            )
            
            # Creamos la entidad de dominio estricta
            return EducaInscriptionDossier(
                beneficiary=BeneficiaryData(**ben_dict),
                related_adults=family_obj,
                education=EducationData(**edu_dict),
                medical=MedicalData(**med_dict)
            )
            
        raise ValueError(f"ActivityType '{activity_type}' no está soportado para reconstituir un dossier.")

    @staticmethod
    def create_from_enriched(
        activity_type: ActivityType,
        **kwargs
    ) -> DossierData:
        """
        Crea un DossierData a partir de los documentos ENRIQUECIDOS.
        Delega toda la responsabilidad de consolidación al Mapper correspondiente según la actividad.
        """
        if activity_type == ActivityType.EDUCA_INSCRIPTION:
            enriched_fins = kwargs.get("FINS")
            enriched_dj = kwargs.get("DJ")
            enriched_dniap = kwargs.get("DNIAP")
            
            if not enriched_fins:
                raise ValueError("No se puede construir un Dossier Educa sin el documento principal FINS.")
            mapper = EducaInscriptionDomainMapper()
            return mapper.map(enriched_fins, enriched_dj, enriched_dniap)

        raise ValueError(f"ActivityType '{activity_type}' no está soportado en la creación desde enriquecidos.")
