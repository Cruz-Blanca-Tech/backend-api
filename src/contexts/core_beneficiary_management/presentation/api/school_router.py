from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, UUID4

from src.core.database import get_async_db
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.school_model import SchoolModel

router = APIRouter(prefix="/schools", tags=["MDM - Schools"])

class SchoolCreate(BaseModel):
    name: str
    location: str | None = None
    phone: str | None = None
    is_active: bool = True

class SchoolUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    phone: str | None = None
    is_active: bool | None = None

class SchoolResponse(BaseModel):
    id: UUID4
    name: str
    location: str | None = None
    phone: str | None = None
    is_active: bool

    class Config:
        from_attributes = True

@router.get("", response_model=List[SchoolResponse])
async def list_schools(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(SchoolModel).order_by(SchoolModel.name))
    schools = result.scalars().all()
    return schools

@router.post("", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school(school: SchoolCreate, db: AsyncSession = Depends(get_async_db)):
    new_school = SchoolModel(
        name=school.name,
        location=school.location,
        phone=school.phone,
        is_active=school.is_active
    )
    db.add(new_school)
    try:
        await db.commit()
        await db.refresh(new_school)
        return new_school
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="El colegio ya existe o hubo un error.")

@router.patch("/{school_id}", response_model=SchoolResponse)
async def update_school(school_id: UUID4, update_data: SchoolUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(SchoolModel).filter(SchoolModel.id == school_id))
    school = result.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="Colegio no encontrado")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(school, key, value)

    await db.commit()
    await db.refresh(school)
    return school
