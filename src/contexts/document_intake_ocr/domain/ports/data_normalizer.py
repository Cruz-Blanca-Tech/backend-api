from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

class DataNormalizer(ABC):
    """
    Puerto (Interfaz) para la normalización de datos extraídos por OCR.
    Permite limpiar, estandarizar formatos, mapear a dominios conocidos y generar alertas.
    """
    
    @abstractmethod
    async def normalize(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Recibe la data cruda del OCR y devuelve un diccionario normalizado.
        El 'context' puede incluir catálogos (ej. colegios válidos) inyectados.
        """
        pass
