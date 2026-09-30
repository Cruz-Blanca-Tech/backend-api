#!/usr/bin/env python3
"""
Script para actualizar/sembrar los colegios con los 4 oficiales.
Usa SQL directo para evitar problemas de relaciones ORM.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from sqlalchemy import select, text, update

# Los 4 colegios oficiales (ID fijo para Nuestra Señora de la Paz para mantener compatibilidad)
COLEGIOS_OFICIALES = [
    {
        "id": UUID("3f661126-d891-425a-be69-f0b215f1188d"),
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
        "name": "Andrés Avelino Cáceres",
        "location": "Av. Cáceres 321",
        "phone": "965432109",
        "is_active": True,
    },
]

NOMBRES_OFICIALES = {c["name"] for c in COLEGIOS_OFICIALES}

async def seed_schools():
    async with async_session_maker() as session:
        # Migrar nombre anterior "Avelino Cáceres" -> "Andrés Avelino Cáceres" si existe
        await session.execute(
            text("""
                UPDATE schools
                SET name = 'Andrés Avelino Cáceres', updated_at = now()
                WHERE name = 'Avelino Cáceres'
                  AND NOT EXISTS (SELECT 1 FROM schools WHERE name = 'Andrés Avelino Cáceres')
            """)
        )

        # Obtener colegios existentes
        result = await session.execute(text("SELECT id, name FROM schools"))
        existing = {row.name: row.id for row in result}
        
        for colegio in COLEGIOS_OFICIALES:
            if colegio["name"] in existing:
                # Actualizar existente
                await session.execute(
                    text("""
                        UPDATE schools 
                        SET location = :location, phone = :phone, is_active = :is_active, updated_at = now()
                        WHERE id = :id
                    """),
                    {
                        "id": str(existing[colegio["name"]]),
                        "location": colegio["location"],
                        "phone": colegio["phone"],
                        "is_active": colegio["is_active"],
                    }
                )
                print(f"Actualizado: {colegio['name']}")
            else:
                # Crear nuevo
                await session.execute(
                    text("""
                        INSERT INTO schools (id, name, location, phone, is_active, created_at, updated_at)
                        VALUES (:id, :name, :location, :phone, :is_active, now(), now())
                    """),
                    {
                        "id": str(colegio["id"]),
                        "name": colegio["name"],
                        "location": colegio["location"],
                        "phone": colegio["phone"],
                        "is_active": colegio["is_active"],
                    }
                )
                print(f"Creado: {colegio['name']}")
        
        # Desactivar colegios que ya no están en la lista oficial
        for name in existing:
            if name not in NOMBRES_OFICIALES:
                await session.execute(
                    text("UPDATE schools SET is_active = false, updated_at = now() WHERE id = :id"),
                    {"id": str(existing[name])}
                )
                print(f"Desactivado: {name}")
        
        await session.commit()
        print("\n¡Colegios actualizados correctamente!")

if __name__ == "__main__":
    asyncio.run(seed_schools())