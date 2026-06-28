from typing import List, Any
from src.contexts.data_quality_triage.domain.shared.entities.triage_policy import TriagePolicy
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO

class TriageEngine:
    def evaluate(self, documents: List[DocumentDTO], policy: TriagePolicy) -> bool:
        """
        Evalúa si la lista de documentos cumple con la política de triaje.
        """
        # Extraer los códigos de documentos presentes
        present_codes = {doc.document_type for doc in documents if doc.document_type}
        
        # Verificar si todos los requeridos por la política están presentes
        missing = [code for code in policy.required_document_codes if code not in present_codes]
        
        return len(missing) == 0
