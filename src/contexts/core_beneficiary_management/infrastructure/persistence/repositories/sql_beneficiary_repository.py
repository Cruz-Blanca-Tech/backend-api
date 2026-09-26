from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.beneficiary_model import BeneficiaryModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.mappers.beneficiary.beneficiary_mapper import BeneficiaryMapper

class SqlBeneficiaryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_dni(self, dni: str) -> Optional[Beneficiary]:
        stmt = (
            select(BeneficiaryModel)
            .where(BeneficiaryModel.dni == dni)
            .options(
                selectinload(BeneficiaryModel.medical_record),
                selectinload(BeneficiaryModel.education_record),
                selectinload(BeneficiaryModel.relatives),
                selectinload(BeneficiaryModel.historical_documents),
                selectinload(BeneficiaryModel.enrollments)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return BeneficiaryMapper.to_domain(model) if model else None

    async def get_by_id(self, id: UUID) -> Optional[Beneficiary]:
        stmt = (
            select(BeneficiaryModel)
            .where(BeneficiaryModel.id == id)
            .options(
                selectinload(BeneficiaryModel.medical_record),
                selectinload(BeneficiaryModel.education_record),
                selectinload(BeneficiaryModel.relatives),
                selectinload(BeneficiaryModel.historical_documents),
                selectinload(BeneficiaryModel.enrollments)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return BeneficiaryMapper.to_domain(model) if model else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Beneficiary]:
        stmt = (
            select(BeneficiaryModel)
            .options(
                selectinload(BeneficiaryModel.medical_record),
                selectinload(BeneficiaryModel.education_record),
                selectinload(BeneficiaryModel.relatives),
                selectinload(BeneficiaryModel.historical_documents),
                selectinload(BeneficiaryModel.enrollments)
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [BeneficiaryMapper.to_domain(m) for m in models if m is not None]
        
    async def count(self) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(BeneficiaryModel)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def save(self, beneficiary: Beneficiary) -> None:
        from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_model import PersonModel
        from src.contexts.core_beneficiary_management.infrastructure.persistence.model.adult_model import AdultModel
        from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone
        from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole

        # Ensure that any relatives (adults) with existing DNIs in the persons table reuse that person's ID
        # to prevent unique constraint violations on ix_persons_dni
        dnis = [r.dni.value for r in beneficiary.relatives if r.dni and r.dni.value]
        existing_persons = {}
        if dnis:
            stmt = select(PersonModel.id, PersonModel.dni).where(PersonModel.dni.in_(dnis))
            res = await self.session.execute(stmt)
            existing_persons = {row.dni: row.id for row in res.all()}
            for r in beneficiary.relatives:
                if r.dni and r.dni.value in existing_persons:
                    r.id = existing_persons[r.dni.value]

            # REGLA DE CONTACTOS (contacto/rol del maestro manda):
            # Un adulto REUSADO ya existe en el maestro (misma persona en otro/mismo
            # núcleo familiar). El expediente nuevo PUEDE aportar una actualización
            # de teléfono (dato de contacto válido se actualiza), pero NUNCA debe
            # borrar/ensuciar lo que el maestro ya tiene:
            #   - teléfono vacío/inválido en la ficha  → conservar el del maestro
            #   - teléfono válido en la ficha          → actualizar (es una actualización)
            #   - rol padre/madre del maestro          → no degradar a OTHER
            reused_ids = list(set(existing_persons.values()))
            if reused_ids:
                res_meta = await self.session.execute(
                    select(AdultModel.id, AdultModel.phone, AdultModel.role).where(AdultModel.id.in_(reused_ids))
                )
                master_meta = {row.id: (row.phone, row.role) for row in res_meta.all()}
                for r in beneficiary.relatives:
                    if not (r.dni and r.dni.value in existing_persons):
                        continue
                    master_phone, master_role = master_meta.get(r.id, (None, None))
                    # Teléfono: conservar el maestro si la ficha no aporta uno válido.
                    has_valid_ficha_phone = bool(
                        r.phone and getattr(r.phone, "value", "") and r.phone.value.strip()
                    )
                    if not has_valid_ficha_phone and master_phone:
                        try:
                            r.phone = Phone(master_phone)
                        except ValueError:
                            pass
                    # Rol: no degradar padre/madre del maestro a OTHER.
                    if master_role:
                        try:
                            master_role_enum = RelationshipRole(master_role)
                        except ValueError:
                            master_role_enum = None
                        if master_role_enum in (RelationshipRole.FATHER, RelationshipRole.MOTHER):
                            if getattr(r, "role", None) not in (RelationshipRole.FATHER, RelationshipRole.MOTHER):
                                r.role = master_role_enum

        model = BeneficiaryMapper.to_persistence(beneficiary)
        # Merge is usually safer when we have complex detached graphs, or add if it's new
        # But if we just extracted from mapper, it is detached. Let's merge.
        merged_model = await self.session.merge(model)
        await self.session.commit()
        # Optional: update entity back? If we need generated IDs, but we use UUIDs.

