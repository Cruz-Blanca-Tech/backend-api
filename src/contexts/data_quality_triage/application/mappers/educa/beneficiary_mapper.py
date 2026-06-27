from typing import Any, Dict
from src.contexts.data_quality_triage.application.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.value_objects.field_mapping import DataType

from src.contexts.data_quality_triage.domain.value_objects.raw_data.fins_raw import FichaInscripcionRaw

class BeneficiaryMapper:
    def __init__(self, registry: NormalizerRegistry):
        self.registry = registry
        self.dni_normalizer = registry.get(DataType.DNI)
        self.date_normalizer = registry.get(DataType.DATE)
        self.name_normalizer = registry.get(DataType.NAME)
        self.int_normalizer = registry.get(DataType.INT)
        self.string_normalizer = registry.get(DataType.STRING)

    def map(self, fins_raw: FichaInscripcionRaw) -> BeneficiaryData:
        if not fins_raw:
            return BeneficiaryData()
        
        age_raw = fins_raw.child_age
        if age_raw:
            age = self.int_normalizer.normalize("".join(c for c in str(age_raw) if c.isdigit()) or None)
        else:
            age = None
            
        return BeneficiaryData(
            dni=self.dni_normalizer.normalize(fins_raw.child_dni),
            first_name=fins_raw.child_first_name,
            last_name=fins_raw.child_last_name,
            birth_date=self.date_normalizer.normalize(fins_raw.child_birth_date),
            gender=self.string_normalizer.normalize(fins_raw.child_gender),
            age=age
        )
