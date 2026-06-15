
from typing import Dict, List
from uuid import uuid4
from src.contexts.document_intake_ocr.application.schemas.activity_schema import (
    ActivityCreateRequest, 
    ActivityRequirementResponse, 
    ActivityResponse, 
    ActivityUpdateRequest
)
from src.contexts.document_intake_ocr.domain.entities.activity import Activity, ActivityRequirement
from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig

class ActivityMapper:
    @staticmethod
    def to_domain(request: ActivityCreateRequest, configs: List[DocumentTypeConfig]) -> Activity:
        config_map = {c.id: c for c in configs}
        
        requirements = [
            ActivityRequirement(
                document_config=config_map[req.document_type_config_id],
                is_required=req.is_required,
                confidence_threshold=req.confidence_threshold
            ) for req in request.requirements
        ]
        
        return Activity(
            id=uuid4(),
            program_id=request.program_id,
            name=request.name,
            required_documents=requirements,
            is_active=True
        )

    @staticmethod
    def to_response(entity: Activity) -> ActivityResponse:
        return ActivityResponse(
            id=entity.id,
            program_id=entity.program_id,
            name=entity.name,
            is_active=entity.is_active,
            requirements=[
                ActivityRequirementResponse(
                    catalog_id=req.document_config.id,
                    is_required=req.is_required,
                    confidence_threshold=req.confidence_threshold
                ) for req in entity.required_documents
            ]
        )
    
    @staticmethod
    def update_from_request(entity: Activity, request: ActivityUpdateRequest, configs: List[DocumentTypeConfig]) -> Activity:
        """
        Actualiza los datos básicos. Se mantiene igual, ya que no toca la lista de documentos.
        """
        update_data = request.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        # B. Reemplazo de requerimientos (si se enviaron)
        if configs:
            config_map = {c.id: c for c in configs}
            entity.required_documents = [
                ActivityRequirement(
                    document_config=config_map[req.document_type_config_id],
                    is_required=req.is_required,
                    confidence_threshold=req.confidence_threshold
                ) for req in request.requirements
            ]
            
        return entity