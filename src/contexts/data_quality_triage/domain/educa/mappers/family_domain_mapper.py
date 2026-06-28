from typing import Any, Optional
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedDj
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult

class FamilyDomainMapper:
    def map(self, enriched_fins: EnrichedFins, enriched_dj: Optional[EnrichedDj] = None, enriched_dniap: Any = None) -> FamilyData:
        adults = []
        for a in enriched_fins.adults:
            if a.dni.normalized_value or a.full_name.normalized_value:
                adults.append(RelatedAdult(
                    relationship=a.role,
                    dni=a.dni.normalized_value,
                    full_name=a.full_name.normalized_value,
                    phone=a.phone.normalized_value if a.phone else None
                ))
        
        guardian_dni = None
        
        # 1. Intentamos obtener el DNI del apoderado desde la Declaración Jurada
        if enriched_dj and enriched_dj.guardian_dni.normalized_value:
            guardian_dni = str(enriched_dj.guardian_dni.normalized_value)
            
        # 2. Si no hay DJ, pero se extrajo el DNI físico del Apoderado (DNIAP)
        if not guardian_dni and enriched_dniap and hasattr(enriched_dniap, "document_number") and enriched_dniap.document_number.normalized_value:
            guardian_dni = str(enriched_dniap.document_number.normalized_value)
            
            # Verificamos si este adulto ya está en la lista (mapeado desde la FINS)
            if not any(a.dni == guardian_dni for a in adults):
                full_name = ""
                if hasattr(enriched_dniap, "first_name") and enriched_dniap.first_name.normalized_value:
                    full_name += str(enriched_dniap.first_name.normalized_value)
                if hasattr(enriched_dniap, "last_name") and enriched_dniap.last_name.normalized_value:
                    full_name += " " + str(enriched_dniap.last_name.normalized_value)
                    
                adults.append(RelatedAdult(
                    relationship="apoderado",
                    dni=guardian_dni,
                    full_name=full_name.strip() or None
                ))
                
        return FamilyData(
            adults=adults,
            guardian_dni=guardian_dni
        )
