from typing import Any, Optional
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedDj
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult

class FamilyDomainMapper:
    def map(self, enriched_fins: EnrichedFins, enriched_dj: Optional[EnrichedDj] = None, enriched_dniap: Any = None) -> FamilyData:
        adults = []
        for a in enriched_fins.adults:
            try:
                first_name = str(a.first_name.normalized_value) if a.first_name and a.first_name.normalized_value else ""
                last_name = str(a.last_name.normalized_value) if a.last_name and a.last_name.normalized_value else ""
                computed_full_name = f"{first_name} {last_name}".strip()

                dni_val = a.dni.normalized_value if a.dni else None
                phone_val = a.phone.normalized_value if a.phone else None

                if dni_val or computed_full_name:
                    adults.append(RelatedAdult(
                        relationship=a.role if a.role else "desconocido",
                        dni=dni_val,
                        full_name=computed_full_name or None,
                        phone=phone_val
                    ))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error mapeando adulto en FamilyDomainMapper: {e}")
                continue
        
        guardian_dni = None
        
        # 1. Intentamos obtener el DNI del apoderado desde la Declaración Jurada
        if enriched_dj and enriched_dj.guardian_dni.normalized_value:
            guardian_dni = str(enriched_dj.guardian_dni.normalized_value)
            
        # 2. Si no hay DJ, pero se extrajo el DNI físico del Apoderado (DNIAP)
        if not guardian_dni and enriched_dniap and enriched_dniap.document_number.normalized_value:
            guardian_dni = str(enriched_dniap.document_number.normalized_value)
            
            # Verificamos si este adulto ya está en la lista (mapeado desde la FINS)
            if not any(a.dni == guardian_dni for a in adults):
                full_name = ""
                if enriched_dniap.first_name.normalized_value:
                    full_name += str(enriched_dniap.first_name.normalized_value)
                if enriched_dniap.last_name.normalized_value:
                    full_name += " " + str(enriched_dniap.last_name.normalized_value)
                    
                adults.append(RelatedAdult(
                    relationship="apoderado",
                    dni=guardian_dni,
                    full_name=full_name.strip() or None
                ))
                
        from src.contexts.data_quality_triage.domain.shared.value_objects.adult_role import AdultRole

        emergency_contact_phone = enriched_fins.emergency_contact_phone.normalized_value if enriched_fins.emergency_contact_phone else None
        emergency_contact_dni = None
        
        # 1. Try to match explicit phone
        if emergency_contact_phone:
            matched_adult = next((a for a in adults if a.phone == emergency_contact_phone), None)
            if matched_adult:
                emergency_contact_dni = matched_adult.dni

        # 2. Fallback
        if not emergency_contact_dni:
            def get_role_str(rel):
                if hasattr(rel, 'value'): return str(rel.value).upper()
                return str(rel).upper()
                
            apoderado = next((a for a in adults if a.relationship and get_role_str(a.relationship) in ["OTHER", "APODERADO"] and a.phone), None)
            madre = next((a for a in adults if a.relationship and get_role_str(a.relationship) == "MOTHER" and a.phone), None)
            padre = next((a for a in adults if a.relationship and get_role_str(a.relationship) == "FATHER" and a.phone), None)
            
            if apoderado:
                emergency_contact_dni = apoderado.dni
            elif madre:
                emergency_contact_dni = madre.dni
            elif padre:
                emergency_contact_dni = padre.dni
                
        return FamilyData(
            adults=adults,
            guardian_dni=guardian_dni,
            emergency_contact_dni=emergency_contact_dni
        )
