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
ACTIVIDAD_SEM2_ID = UUID("fa9e45e9-7e0c-4e71-bc17-64e8a8489344")

# Usuario de desarrollo. Se fija en ADMIN para que pueda administrar el maestro
# (crear/editar actividades y catálogo de documentos son ALLOW_ADMIN_ONLY).
# OJO: iniciar la extracción NO depende del rol — `POST /api/v1/batches` solo
# exige un usuario autenticado, no tiene RoleChecker.
SEED_USERS = [
    {"email": "enzo.trujillo@cruz-blanca.org", "name": "Enzo Trujillo", "role": "admin"},
    {"email": "orientacionfamiliar@cruz-blanca.org", "name": "Orientación Familiar Cruz Blanca", "role": "admin"},
]

# Configuración de documentos para EDUCA.
#
# `model_id` es el ID REAL del modelo en Azure Document Intelligence: el intake lo
# resuelve por código vía `Activity.get_model_id_for_document` y se lo pasa a
# `DocumentExtractor.extract_data`. Un id inventado acá hace fallar el OCR.
#
# `preview_image_url` es la imagen de ejemplo que ve el operador en "documentos
# esperados". Debe ser un archivo PÚBLICO de Drive ("cualquier persona con el
# enlace"): el frontend la normaliza con `toDriveThumbnailUrl` y la baja por su
# propio proxy `/api/drive-image` (Drive no permite hotlinkear ni con OAuth).
DOCUMENT_CONFIGS = [
    {
        "id": UUID("459da05e-1cb9-4f1f-b70e-abc0251f09b3"),
        "code": "FINS",
        "name": "Ficha de Inscripción EDUCA",
        "year": 2026,
        "model_id": "extractor-fichas-inscripcion-v3",
        "version": 1,
        "preview_image_url": "https://drive.google.com/uc?export=view&id=1GWYFqrVR_3zH_hAP2u7wYldcaDR8ADS3",
    },
    {
        "id": UUID("270072c7-39ee-45b3-b8d6-462e64af6dfc"),
        "code": "DJ",
        "name": "Declaración Jurada",
        "year": 2026,
        "model_id": "doc-extractor-declaracion-jurada-v1",
        "version": 1,
        "preview_image_url": "https://drive.google.com/uc?export=view&id=1Im5BWqMOZ5SI8A-7I2OAMYCZxjF803hP",
    },
    {
        "id": UUID("6d5ce9df-2674-4837-92a1-4f9220f0920b"),
        "code": "DNIBE",
        "name": "DNI Beneficiario",
        "year": 2026,
        "model_id": "prebuilt-idDocument",
        "version": 1,
        "preview_image_url": "https://drive.google.com/uc?export=view&id=1q2EAsFniC9jG8KgqCjqVLDL7l3C39cYb",
    },
    {
        "id": UUID("544b6c36-3aeb-4291-96d8-9b0e2b3a5107"),
        "code": "DNIAP",
        "name": "DNI Apoderado",
        "year": 2026,
        "model_id": "prebuilt-idDocument",
        "version": 1,
        "preview_image_url": "https://drive.google.com/uc?export=view&id=1RYgPwW31D4Y3Tb4tT2Yr1gTLyvZw_m5m",
    },
]

# Umbral de confianza OCR para los cuatro documentos de EDUCA_INSCRIPTION.
#
# Calibrado sobre los 24 documentos del lote de prueba (6 DNI x 4 docs), cuyos
# scores van de 0.0000 a 0.7900, promedio 0.66. El 0.85 que venía del seed
# historico era inalcanzable: ningun documento lo superaba, asi que el aviso
# salia en el 100% de los casos y no distinguia nada.
#
# 0.65 separa las lecturas reales de los fracasos del OCR: los 23 documentos
# leidos caen por encima, y el unico 0.0000 (DNIBE del DNI 78876488) queda
# fuera, que es justo lo que tiene que quedar fuera.
#
# OJO: el aviso de confianza es WARNING, y los WARNING bloquean la ruta
# touchless igual que los ERROR. Subir este numero encarece el touchless.
CONFIDENCE_THRESHOLD = 0.65

# Requisitos para EDUCA_INSCRIPTION (DJ excluido de umbral de confianza -> 0.0)
REQUIREMENTS = [
    {"code": "FINS", "is_required": True, "confidence_threshold": CONFIDENCE_THRESHOLD},
    {"code": "DJ", "is_required": True, "confidence_threshold": 0.0},
    {"code": "DNIBE", "is_required": True, "confidence_threshold": CONFIDENCE_THRESHOLD},
    {"code": "DNIAP", "is_required": True, "confidence_threshold": CONFIDENCE_THRESHOLD},
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

        # 2. Document Type Configs.
        # Upsert por (code, year): si el registro ya existe con otro id (p. ej. creado
        # por la UI), se actualiza en el sitio para no duplicar ni romper los
        # activity_requirements que ya lo referencian.
        doc_config_ids = {}
        for doc in DOCUMENT_CONFIGS:
            result = await session.execute(
                text("SELECT id FROM document_type_configs WHERE code = :code AND year = :year"),
                {"code": doc["code"], "year": doc["year"]},
            )
            existing = result.fetchone()
            doc_config_ids[doc["code"]] = existing[0] if existing else str(doc["id"])

            if existing:
                await session.execute(text("""
                    UPDATE document_type_configs
                    SET name = :name,
                        model_id = :model_id,
                        version = :version,
                        preview_image_url = :preview_image_url,
                        is_active = true
                    WHERE id = :id
                """), {
                    "id": str(existing[0]),
                    "name": doc["name"],
                    "model_id": doc["model_id"],
                    "version": doc["version"],
                    "preview_image_url": doc["preview_image_url"],
                })
                print(f"Config doc actualizada: {doc['code']}")
            else:
                await session.execute(text("""
                    INSERT INTO document_type_configs
                        (id, code, name, year, model_id, version, preview_image_url, is_active, created_at)
                    VALUES (:id, :code, :name, :year, :model_id, :version, :preview_image_url, true, now())
                """), {
                    "id": str(doc["id"]),
                    "code": doc["code"],
                    "name": doc["name"],
                    "year": doc["year"],
                    "model_id": doc["model_id"],
                    "version": doc["version"],
                    "preview_image_url": doc["preview_image_url"],
                })
                print(f"Config doc creada: {doc['code']}")

        # 3. Actividades y requisitos.
        # Los ids son FIJOS (no uuid4): con ids aleatorios cada corrida creaba una
        # actividad nueva y el semestre 2 quedaba duplicado.
        ACTIVIDADES = [
            {
                "id": ACTIVIDAD_SEM1_ID,
                "name": "INSCRIPCIÓN A EDUCA 2026 - I",
                "start_date": date(2026, 3, 15),
                "end_date": date(2026, 7, 15),
            },
            {
                "id": ACTIVIDAD_SEM2_ID,
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
                    print(f"  ADVERTENCIA: No se encontro config para {req['code']}")
                    continue

                result = await session.execute(text("""
                    SELECT id FROM activity_requirements
                    WHERE activity_id = :act_id AND document_type_config_id = :doc_id
                """), {"act_id": str(act["id"]), "doc_id": str(doc_id)})
                existing_req = result.fetchone()

                if existing_req:
                    await session.execute(text("""
                        UPDATE activity_requirements
                        SET is_required = :is_required,
                            confidence_threshold = :confidence_threshold
                        WHERE id = :id
                    """), {
                        "id": str(existing_req[0]),
                        "is_required": req["is_required"],
                        "confidence_threshold": req["confidence_threshold"],
                    })
                    print(f"  Requisito actualizado: {act['name']} -> {req['code']} (thr: {req['confidence_threshold']})")
                else:
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

        # 4. Roles de usuarios base.
        for su in SEED_USERS:
            result = await session.execute(
                text("SELECT role FROM users WHERE email = :email"),
                {"email": su["email"]},
            )
            user = result.fetchone()
            if user:
                if user[0] != su["role"]:
                    await session.execute(
                        text("UPDATE users SET role = :role, is_active = true WHERE email = :email"),
                        {"email": su["email"], "role": su["role"]},
                    )
                    print(f"Rol de {su['email']}: {user[0]} -> {su['role']}")
                else:
                    print(f"Rol de {su['email']}: ya es {su['role']}")
            else:
                await session.execute(text("""
                    INSERT INTO users (id, email, full_name, role, is_active, last_login)
                    VALUES (gen_random_uuid(), :email, :name, :role, true, now())
                """), {
                    "email": su["email"],
                    "name": su["name"],
                    "role": su["role"],
                })
                print(f"Usuario {su['email']} creado con rol {su['role']}")

        await session.commit()
        print("\n¡Seed completo!")

asyncio.run(seed_full())