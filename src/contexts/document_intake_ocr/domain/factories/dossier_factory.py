# src/contexts/document_intake_ocr/domain/factories/dossier_factory.py

from uuid import UUID
from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.document_intake_ocr.domain.value_objects.dossier_proposal import DossierProposal

class DossierFactory:
    @staticmethod
    def create_from_proposal(
        clean_proposal: DossierProposal,
        activity: Activity,
        batch_id: UUID
    ) -> Dossier:
        
        dossier = Dossier(clean_proposal.dni, activity.id, batch_id)
        
        for f in clean_proposal.files: 
            # El filtrado previo nos asegura que el código existe
            code_vo = f.extracted_code
            config_id = activity.get_config_id_by_code(str(code_vo))
            
            # Usamos el constructor semántico de la Entidad
            doc = DocumentItem.create_valid(
                source_id=f.source_id,
                document_code= f.extracted_code,
                file_name=f.file_name,
                dni_ref=clean_proposal.dni,
                config_id=config_id
            )
            
            dossier.add_document(doc)
            
        dossier.update_status(activity.required_documents)
        return dossier