from __future__ import annotations
from uuid import UUID
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.activity_mapper import ActivityMapper
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model import ActivityModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model import ActivityRequirementModel

class SqlActivityRepository(ActivityRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, activity_id: UUID) -> Optional[Activity]:
        # Usamos 'select' en lugar de 'query' para sintaxis async
        query = (
            select(ActivityModel)
            .options(
                selectinload(ActivityModel.requirements)
                .joinedload(ActivityRequirementModel.document_config)
            )
            .filter(ActivityModel.id == activity_id)
        )
        
        result = await self.session.execute(query)
        db_activity = result.scalar_one_or_none()
        
        if not db_activity:
            return None
            
        return ActivityMapper.to_domain(db_activity)
    
    async def get_by_program_id(self, program_id: UUID) -> List[Activity]:
        """
        Recupera todas las actividades asociadas a un programa específico.
        Implementa eager loading para los requerimientos y la configuración documental
        para optimizar el rendimiento de la consulta.
        """ 
        query = (
            select(ActivityModel)
            .options(
                joinedload(ActivityModel.requirements)
                .joinedload(ActivityRequirementModel.document_config)
            )
            .filter(ActivityModel.program_id == program_id)
        )
        
        result = await self.session.execute(query)
        # Usamos scalars().all() para obtener la lista de entidades del modelo
        db_activities = result.scalars().unique().all()
        
        return [ActivityMapper.to_domain(activity) for activity in db_activities]
    
    async def list_all_active(self) -> List[Activity]:
        query = (
            select(ActivityModel)
            .options(
                joinedload(ActivityModel.requirements)
                .joinedload(ActivityRequirementModel.document_config)
            )
            .filter(ActivityModel.is_active == True)
        )
        result = await self.session.execute(query)
        db_activities = result.scalars().unique().all()
        return [ActivityMapper.to_domain(a) for a in db_activities]

    async def save(self, activity: Activity) -> None:
        # 1. Buscar la actividad existente
        query = (
            select(ActivityModel)
            .options(selectinload(ActivityModel.requirements))
            .filter_by(id=activity.id)
        )
        
        result = await self.session.execute(query)
        db_activity = result.scalar_one_or_none()
        
        if db_activity:
            db_activity.name = activity.name
            db_activity.is_active = activity.is_active
        else:
            db_activity = ActivityModel(
                id=activity.id,
                program_id=activity.program_id,
                name=activity.name,
                is_active=activity.is_active
            )
            self.session.add(db_activity)
        # 2. Sincronización asíncrona (AQUÍ ESTÁ EL CAMBIO CLAVE)
        await self.session.flush() 
        
        # FORZAMOS LA CARGA ASÍNCRONA DE LA COLECCIÓN
        # Esto le dice a SQLAlchemy: "Carga esto ahora mismo de forma segura"
        await self.session.refresh(db_activity, ["requirements"])
        
        # Ahora el .clear() es seguro porque la colección está cargada en memoria
        db_activity.requirements.clear() 
        
        for req_doc in activity.required_documents: 
            new_requirement = ActivityRequirementModel(
                activity_id=activity.id,
                document_type_config_id=req_doc.document_config.id,
                is_required=req_doc.is_required,
                confidence_threshold=req_doc.confidence_threshold
            )
            db_activity.requirements.append(new_requirement)
        
        # 3. COMMIT ASÍNCRONO
        await self.session.commit()