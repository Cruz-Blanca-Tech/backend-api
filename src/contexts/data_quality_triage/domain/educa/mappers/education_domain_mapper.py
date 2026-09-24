from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
import difflib

class EducationDomainMapper:
    def __init__(self, context: dict = None):
        self.context = context or {}

    def map(self, enriched_fins: EnrichedFins) -> EducationData:
        school = enriched_fins.education.school.normalized_value
        grade = enriched_fins.education.grade.normalized_value
        
        validation_issues = []
        
        # Fuzzy match for school
        db_schools = self.context.get("schools", [])
        mapped_school = None
        
        if not school or school.lower() in ["no registrada", "no registrado", "unknown"]:
            validation_issues.append("Debe registrar la institucion educativa (School).")
        else:
            if db_schools:
                best_match = None
                best_ratio = 0.0
                query_name = school.lower().strip()
                
                for db_s in db_schools:
                    db_name = db_s.get("name", "").lower().strip()
                    if db_name in query_name or query_name in db_name:
                        ratio = 0.95
                    else:
                        ratio = difflib.SequenceMatcher(None, query_name, db_name).ratio()
                        
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = db_s.get("name")
                
                if best_ratio > 0.65 and best_match:
                    mapped_school = best_match
                else:
                    validation_issues.append(f"El colegio '{school}' la ia no ha podido clasificarlo. Por favor, seleccione el correcto en la lista.")
            else:
                mapped_school = school
            
        if not grade or grade.lower() in ["no registrada", "no registrado", "unknown"] or len(grade) > 10:
            validation_issues.append("Debe registrar un grado valido (ej. 3er grado).")
            
        knows_read = enriched_fins.education.knows_how_to_read.normalized_value
        if knows_read is None:
            knows_read = True
            
        knows_write = enriched_fins.education.knows_how_to_write.normalized_value
        if knows_write is None:
            knows_write = True
            
        repeated_grade = enriched_fins.education.has_repeated_grade.normalized_value
        if repeated_grade is None:
            repeated_grade = False
            
        learning_diff = enriched_fins.education.has_learning_difficulties.normalized_value
            
        return EducationData(
            school=mapped_school,
            grade=grade,
            knows_read=knows_read,
            knows_write=knows_write,
            repeated_grade=repeated_grade,
            learning_difficulties=learning_diff,
            validation_issues=validation_issues
        )
