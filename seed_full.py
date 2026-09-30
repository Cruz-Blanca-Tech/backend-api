#!/usr/bin/env python3
"""
Script completo para sembrar: programa EDUCA, actividades (semestres 1 y 2),
configuraciones de documentos y requisitos de actividad.
"""

import asyncio
import sys
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from sqlalchemy import text

EDUCA_PROGRAM_ID = UUID("e561e788-f053-40cc-a4a3-5040627f27de")
ACTIVIDAD_SEM1_ID = UUID("05194c0c-9ff7-4b4d-97f6-af51d62521c3")

# Configuración de documentos para EDUCA
DOCUMENT_CONFIGS = [
    {"code": "FINS", "name": "Ficha de Inscripción", "year": 2026, "model_id": "azure-fins", "version": 1},
    {"code": "DJ", "name": "Declaración Jurada", "year": 2026, "model_id": "azure-dj", "version": 1},
    {"code": "DNIBE", "name": "DNI Beneficiario", "year": 2026, "model_id": "azure-dni", "version": 1},
    {"code": "DNIAP", "name": "DNI Apoderado", "year": 2026, "model_id": "azure-dni", "version": 1},
]

# Requisitos para EDUCA_INSCRIPTION
REQUIREMENTS = [
    {"code": "FINS", "is_required": True, "confidence_threshold": 0.80},
    {"code": "DJ", "is_required": True, "confidence_threshold": 0.55},
    {"code": "DNIBE", "is_required": True, "confidence_threshold": 0.65},
    {"code": "DNIAP", "is_required": True, "confidence_threshold": 0.65},
]

async def seed_full():
    async with async_session_maker() as session:
        # 1. Programa EDUCA
        result = await session.execute(text("SELECT id FROM programs WHERE name = 'EDUCA'"))
        existing = result.fetchone()
        if not existing:
            await session.execute(text("""
                INSERT INTO programs (id, name, description, is_active, created_at)
                VALUES (:id, :name, :description, :is_active, now())
            """), {
                "id": str(EDUCA_PROGRAM_ID),
                "name": "EDUCA",
                "description": "Programa de Acompañamiento Educativo Integral",
                "is_active": True,
            })
            print("Programa EDUCA creado")
        else:
            print(f"Programa EDUCA ya existe: {existing[0]}")

        # 2. Document Type Configs
        doc_config_ids = {}
        for doc in DOCUMENT_CONFIGS:
            result = await session.execute(text("SELECT id FROM document_type_configs WHERE code = :code AND year = :year"),
                                          {"code": doc["code"], "year": doc["year"]})
            existing = result.fetchone()
            if existing:
                doc_config_ids[doc["code"]] = existing[0]
                print(f"Config doc ya existe: {doc['code']}")
            else:
                new_id = uuid4()
                await session.execute(text("""
                    INSERT INTO document_type_configs (id, code, name, year, model_id, version, is_active, created_at)
                    VALUES (:id, :code, :name, :year, :model_id, :version, :is_active, now())
                """), {
                    "id": str(new_id),
                    "code": doc["code"],
                    "name": doc["name"],
                    "year": doc["year"],
                    "model_id": doc["model_id"],
                    "version": doc["version"],
                    "is_active": True,
                })
                doc_config_ids[doc["code"]] = new_id
                print(f"Creado config doc: {doc['code']}")

        # 3. Actividades y requisitos
        ACTIVIDADES = [
            {
                "id": ACTIVIDAD_SEM1_ID,
                "name": "INSCRIPCIÓN A EDUCA 2026 - I",
                "start_date": date(2026, 3, 15),
                "end_date": date(2026, 7, 15),
            },
            {
                "id": uuid4(),
                "name": "INSCRIPCIÓN A EDUCA 2026 - II",
                "start_date": date(2026, 7, 15),
                "end_date": date(2026, 11, 30),
            },
        ]

        for act in ACTIVIDADES:
            result = await session.execute(text("SELECT id FROM activities WHERE id = :id"), {"id": str(act["id"])})
            existing = result.fetchone()
            if existing:
                await session.execute(text("""
                    UPDATE activities 
                    SET activity_type = 'EDUCA_INSCRIPTION',
                        start_date = :start_date,
                        end_date = :end_date,
                        program_id = :program_id,
                        is_active = true
                    WHERE id = :id
                """), {
                    "id": str(act["id"]),
                    "program_id": str(EDUCA_PROGRAM_ID),
                    "start_date": act["start_date"],
                    "end_date": act["end_date"],
                })
                print(f"Actualizada actividad: {act['name']}")
            else:
                await session.execute(text("""
                    INSERT INTO activities (id, program_id, name, activity_type, start_date, end_date, is_active, created_at)
                    VALUES (:id, :program_id, :name, :activity_type, :start_date, :end_date, :is_active, now())
                """), {
                    "id": str(act["id"]),
                    "program_id": str(EDUCA_PROGRAM_ID),
                    "name": act["name"],
                    "activity_type": "EDUCA_INSCRIPTION",
                    "start_date": act["start_date"],
                    "end_date": act["end_date"],
                    "is_active": True,
                })
                print(f"Creada actividad: {act['name']}")

            # Requisitos de documentos para esta actividad
            for req in REQUIREMENTS:
                doc_id = doc_config_ids.get(req["code"])
                if not doc_id:
                    print(f"  ADVERTENCIA: No se encontró config para {req['code']}")
                    continue
                
                result = await session.execute(text("""
                    SELECT id FROM activity_requirements 
                    WHERE activity_id = :act_id AND document_type_config_id = :doc_id
                """), {"act_id": str(act["id"]), "doc_id": str(doc_id)})
                existing_req = result.fetchone()
                
                if not existing_req:
                    await session.execute(text("""
                        INSERT INTO activity_requirements (id, activity_id, document_type_config_id, is_required, confidence_threshold)
                        VALUES (:id, :activity_id, :document_type_config_id, :is_required, :confidence_threshold)
                    """), {
                        "id": str(uuid4()),
                        "activity_id": str(act["id"]),
                        "document_type_config_id": str(doc_id),
                        "is_required": req["is_required"],
                        "confidence_threshold": req["confidence_threshold"],
                    })
                    print(f"  Requisito creado: {act['name']} -> {req['code']} (req: {req['is_required']}, thr: {req['confidence_threshold']})")
                else:
                    print(f"  Requisito ya existe: {act['name']} -> {req['code']}")

        await session.commit()
        print("\n¡Seed completo!")

asyncio.run(seed_full())