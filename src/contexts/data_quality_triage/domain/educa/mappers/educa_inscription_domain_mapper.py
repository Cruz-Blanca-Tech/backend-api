from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedDj
from typing import Any
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData

from .beneficiary_domain_mapper import BeneficiaryDomainMapper
from .family_domain_mapper import FamilyDomainMapper
from .education_domain_mapper import EducationDomainMapper
from .medical_domain_mapper import MedicalDomainMapper
from .religion_domain_mapper import ReligionDomainMapper
from .permissions_domain_mapper import PermissionsDomainMapper
from src.contexts.data_quality_triage.domain.educa.value_objects.religion_data import ReligionData
from src.contexts.data_quality_triage.domain.educa.value_objects.permissions_data import PermissionsData

class EducaInscriptionDomainMapper:
    def __init__(self):
        self.beneficiary_mapper = BeneficiaryDomainMapper()
        self.family_mapper = FamilyDomainMapper()
        self.education_mapper = EducationDomainMapper()
        self.medical_mapper = MedicalDomainMapper()
        self.religion_mapper = ReligionDomainMapper()
        self.permissions_mapper = PermissionsDomainMapper()
        import logging
        self.logger = logging.getLogger(__name__)
        
    def map(self, enriched_fins: EnrichedFins, enriched_dj: EnrichedDj = None, enriched_dniap: Any = None) -> EducaInscriptionDossier:
        
        return EducaInscriptionDossier(
            beneficiary=self.map_beneficiary(enriched_fins),
            related_adults=self.map_parents(enriched_fins, enriched_dj, enriched_dniap),
            education=self.map_education(enriched_fins),
            medical=self.map_medical(enriched_fins),
            religion=self.map_religion(enriched_fins),
            permissions=self.map_permissions(enriched_fins)
        )
        
    def map_beneficiary(self, enriched_fins: EnrichedFins) -> BeneficiaryData:
        try:
            return self.beneficiary_mapper.map(enriched_fins)
        except Exception as e:
            self.logger.error(f"Error mapeando beneficiary: {e}")
            return BeneficiaryData(validation_issues=[f"Error interno mapeando sección: {e}"])

    def map_parents(self, enriched_fins: EnrichedFins, enriched_dj: EnrichedDj = None, enriched_dniap: Any = None) -> FamilyData:
        try:
            return self.family_mapper.map(enriched_fins, enriched_dj, enriched_dniap)
        except Exception as e:
            self.logger.error(f"Error mapeando parents: {e}")
            return FamilyData(validation_issues=[f"Error interno mapeando sección: {e}"])

    def map_education(self, enriched_fins: EnrichedFins) -> EducationData:
        try:
            return self.education_mapper.map(enriched_fins)
        except Exception as e:
            self.logger.error(f"Error mapeando education: {e}")
            # EducationData no tiene validation_issues por defecto, mandamos vacío
            return EducationData()

    def map_medical(self, enriched_fins: EnrichedFins) -> MedicalData:
        try:
            return self.medical_mapper.map(enriched_fins)
        except Exception as e:
            self.logger.error(f"Error mapeando medical: {e}")
            return MedicalData()

    def map_religion(self, enriched_fins: EnrichedFins) -> ReligionData:
        try:
            return self.religion_mapper.map(enriched_fins)
        except Exception as e:
            self.logger.error(f"Error mapeando religion: {e}")
            return ReligionData()

    def map_permissions(self, enriched_fins: EnrichedFins) -> PermissionsData:
        try:
            return self.permissions_mapper.map(enriched_fins)
        except Exception as e:
            self.logger.error(f"Error mapeando permissions: {e}")
            return PermissionsData()

