#!/usr/bin/env python3
"""
Script para actualizar/sembrar los colegios con los 4 colegios oficiales:
- Nuestra Señora de la Paz
- Sagrada Familia
- Generalísimo San Martín
- Avelino Cáceres
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.school_model import SchoolModel
from sqlalchemy import select

# Los 4 colegios oficiales
COLEGIOS_OFICIALES = [
    {
        "id": UUID("3f661126-d891-425a-be69-f0b215f1188d"),  # ID existente para mantener compatibilidad
        "name": "Nuestra Señora de la Paz",
        "location": "Av. Principal 123",
        "phone": "99723122",
        "is_active": True,
    },
    {
        "id": uuid4(),
        "name": "Sagrada Familia",
        "location": "Av. Sagrada 456",
        "phone": "987654321",
        "is_active": True,
    },
    {
        "id": uuid4(),
        "name": "Generalísimo San Martín",
        "location": "Av. San Martín 789",
        "phone": "976543210",
        "is_active": True,
    },
    {
        "id": uuid4(),
        "name": "Avelino Cáceres",
        "location": "Av. Cáceres 321",
        "phone": "965432109",
        "is_active": True,
    },
]

async def seed_schools():
    async with async_session_maker() as session:
        # Obtener colegios existentes
        result = await session.execute(select(SchoolModel))
        existing = {s.name: s for s in result.scalars().all()}
        
        for colegio in COLEGIOS_OFICIALES:
            if colegio["name"] in existing:
                # Actualizar existente
                school = existing[colegio["name"]]
                school.location = colegio["location"]
                school.phone = colegio["phone"]
                school.is_active = colegio["is_active"]
                print(f"Actualizado: {colegio['name']}")
            else:
                # Crear nuevo
                school = SchoolModel(
                    id=colegio["id"],
                    name=colegio["name"],
                    location=colegio["location"],
                    phone=colegio["phone"],
                    is_active=colegio["is_active"],
                )
                session.add(school)
                print(f"Creado: {colegio['name']}")
        
        # Desactivar colegios que ya no están en la lista oficial
        nombres_oficiales = {c["name"] for c in COLEGIOS_OFICIALES}
        for name, school in existing.items():
            if name not in nombres_oficiales:
                school.is_active = False
                print(f"Desactivado: {name}")
        
        await session.commit()
        print("\n¡Colegios actualizados correctamente!")

if __name__ == "__main__":
    asyncio.run(seed_schools())