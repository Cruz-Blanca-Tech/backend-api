from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedEducation
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw

class EducationEnrichedMapper(BaseEnrichedMapper):
    def map(self, raw_dto: FinsRaw) -> EnrichedEducation:
        return EnrichedEducation(
            school=self.build_field(raw_dto.child_school, "Colegio", DataType.STRING),
            grade=self.build_field(raw_dto.child_grade, "Grado", DataType.STRING),
            knows_how_to_read=self.build_field(raw_dto.educational_knows_how_to_read_yes, "¿Sabe leer?", DataType.BOOL),
            knows_how_to_write=self.build_field(raw_dto.educational_knows_how_to_write_yes, "¿Sabe escribir?", DataType.BOOL),
            has_repeated_grade=self.build_field(raw_dto.educational_has_repeated_grade_yes, "¿Ha repetido grado?", DataType.BOOL),
            has_learning_difficulties=self.build_field(raw_dto.educational_has_learning_difficulties_yes, "¿Tiene dificultades de aprendizaje?", DataType.BOOL)
        )
