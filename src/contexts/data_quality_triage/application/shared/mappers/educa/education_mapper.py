
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.fins_raw import FichaInscripcionRaw
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType

class EducationMapper:
    def __init__(self, registry: NormalizerRegistry):
        self.bool_normalizer = registry.get(DataType.BOOL)

    def map(self, fins_raw: FichaInscripcionRaw) -> EducationData:
        if not fins_raw:
            return EducationData()
            
        return EducationData(
            school=fins_raw.child_school,
            grade=fins_raw.child_grade,
            knows_read=self.bool_normalizer.normalize(fins_raw.educational_knows_how_to_read_yes),
            knows_write=self.bool_normalizer.normalize(fins_raw.educational_knows_how_to_write_yes),
            repeated_grade=self.bool_normalizer.normalize(fins_raw.educational_has_repeated_grade_yes),
            learning_difficulties=self.bool_normalizer.normalize(fins_raw.educational_has_learning_difficulties_yes)
        )
