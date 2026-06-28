from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData

class EducationDomainMapper:
    def map(self, enriched_fins: EnrichedFins) -> EducationData:
        return EducationData(
            school=enriched_fins.education.school.normalized_value,
            grade=enriched_fins.education.grade.normalized_value,
            knows_read=enriched_fins.education.knows_how_to_read.normalized_value or False,
            knows_write=enriched_fins.education.knows_how_to_write.normalized_value or False,
            repeated_grade=enriched_fins.education.has_repeated_grade.normalized_value or False,
            learning_difficulties=enriched_fins.education.has_learning_difficulties.normalized_value or False
        )
