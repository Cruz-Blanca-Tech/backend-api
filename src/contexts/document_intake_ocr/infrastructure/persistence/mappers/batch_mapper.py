from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch, BatchStatus
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.document_item_mapper import DocumentItemMapper
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel

class BatchMapper:
    @staticmethod
    def to_model(entity: ExtractionBatch) -> ExtractionBatchModel:
        model = ExtractionBatchModel(
            id=entity.id,
            activity_id=entity.activity_id,
            created_by=entity.created_by,
            status=entity.status.value,
            created_at=entity.created_at
        )
        
        # We must gather ALL documents (valid from dossiers + rejected) to save them
        all_domain_docs = entity.get_all_documents() 
        
        model.documents = [
            DocumentItemMapper.to_model(doc_entity, batch_id=entity.id) 
            for doc_entity in all_domain_docs
        ]   
        
        return model

    @staticmethod
    def to_domain(model: ExtractionBatchModel) -> ExtractionBatch:
        # 1. Crear el Batch de dominio básico
        batch = ExtractionBatch(
            id=model.id,
            activity_id=model.activity_id,
            created_by=model.created_by,
            status=BatchStatus(model.status),
            created_at=model.created_at
        )
        
        # 2. AGRUPAR documentos por DNI para formar los Dossiers
        dossiers_dict = {}

        for doc_model in model.documents:
            # Protegemos por si algún documento no tiene DNI
            dni = doc_model.dni_reference or "SIN_DNI" 
            
            if dni not in dossiers_dict:
                dossiers_dict[dni] = Dossier(
                    dni=dni, 
                    activity_id=model.activity_id, 
                    batch_id=model.id
                )
            
            # Convertir documento a dominio y añadirlo al dossier
            domain_doc = DocumentItemMapper.to_domain(doc_model)
            dossiers_dict[dni].add_document(domain_doc)
            
        # 3. Registrar los dossiers en el Batch de dominio
        for dossier in dossiers_dict.values():
            batch.add_dossier(dossier)
            
        # SI ESTE LOG APARECE, EL ORQUESTADOR ENCONTRARÁ LOS ARCHIVOS
        print(f"DEBUG MAPPER: Agrupados {len(dossiers_dict)} expedientes (dossiers).")
        
        return batch
