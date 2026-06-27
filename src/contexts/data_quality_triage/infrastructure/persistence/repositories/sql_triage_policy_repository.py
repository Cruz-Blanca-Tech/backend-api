from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from src.contexts.data_quality_triage.domain.entities.triage_policy import TriagePolicy
from src.contexts.data_quality_triage.domain.repositories.policy_repository import PolicyRepository
from src.contexts.data_quality_triage.infrastructure.persistence.mappers.triage_policy_mapper import TriagePolicyMapper
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_policy_model import TriagePolicyModel

class SqlPolicyRepository(PolicyRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, policy: TriagePolicy) -> None:
        """Guarda o actualiza la política de triaje usando el Mapper."""
        activity_id_str = str(policy.activity_id)
        
        # 1. Buscamos si ya existe
        query = select(TriagePolicyModel).where(TriagePolicyModel.activity_id == activity_id_str)
        result = await self.db.execute(query)
        db_policy = result.scalars().first()

        # 2. Actualizamos o Creamos
        if db_policy:
            # Actualizamos los campos desde la entidad
            db_policy.required_document_codes = policy.required_document_codes
        else:
            # Usamos el mapper para convertir a modelo
            new_model = TriagePolicyMapper.to_model(policy)
            self.db.add(new_model)
            
        await self.db.commit()

    async def get_by_activity_id(self, activity_id: UUID) -> TriagePolicy | None:
        """Recupera y mapea a dominio."""
        query = select(TriagePolicyModel).where(TriagePolicyModel.activity_id == str(activity_id))
        result = await self.db.execute(query)
        db_policy = result.scalars().first()

        if not db_policy:
            return None

        # ¡Aquí el mapper brilla! Tu repositorio no instancia entidades manualmente.
        return TriagePolicyMapper.to_domain(db_policy)