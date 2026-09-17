from typing import Any
import re
from src.contexts.data_quality_triage.application.shared.normalizers.base_normalizer import BaseNormalizer

class GradeNormalizer(BaseNormalizer):
    def normalize(self, raw_value: Any) -> Any:
        if not raw_value or not isinstance(raw_value, str):
            return raw_value
        
        text = raw_value.upper().strip()
        
        # Si ya es un valor estandarizado perfecto, pasarlo
        valid_grades = {
            'INICIAL_3', 'INICIAL_4', 'INICIAL_5', 
            '1RO_PRIMARIA', '2DO_PRIMARIA', '3RO_PRIMARIA', '4TO_PRIMARIA', '5TO_PRIMARIA', '6TO_PRIMARIA',
            '1RO_SECUNDARIA', '2DO_SECUNDARIA', '3RO_SECUNDARIA', '4TO_SECUNDARIA', '5TO_SECUNDARIA',
            'SUPERIOR', 'NINGUNO'
        }
        if text in valid_grades:
            return text
            
        # Buscar el primer digito en el texto
        match = re.search(r'\d', text)
        if match:
            digit = match.group(0)
            
            # Detectar si menciona secundaria
            if 'SEC' in text:
                sec_map = {'1': '1RO', '2': '2DO', '3': '3RO', '4': '4TO', '5': '5TO'}
                if digit in sec_map:
                    return f"{sec_map[digit]}_SECUNDARIA"
            
            # Detectar si menciona inicial / anios
            elif 'INI' in text or 'AÑ' in text or 'AN' in text:
                if digit in ['3', '4', '5']:
                    return f"INICIAL_{digit}"
            
            # Por defecto, asumir PRIMARIA como lo requirio el usuario
            else:
                prim_map = {'1': '1RO', '2': '2DO', '3': '3RO', '4': '4TO', '5': '5TO', '6': '6TO'}
                if digit in prim_map:
                    return f"{prim_map[digit]}_PRIMARIA"
                    
        # Si es texto y dice superior o ninguno
        if 'SUP' in text:
            return 'SUPERIOR'
        if 'NING' in text:
            return 'NINGUNO'
            
        # Si no se pudo deducir nada seguro, devolver el texto original
        # para que la regla de validacion (EducationRules) lo marque en ROJO.
        return raw_value
