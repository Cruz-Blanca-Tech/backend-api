import sys
sys.path.insert(0, r"c:\Users\enzot\Documents\code\CruzBlanca\backend-api")
import asyncio
from sqlalchemy import text
from src.core.database import engine

async def seed():
    async with engine.begin() as conn:
        # 1. Program EDUCA (required for FK program_id)
        await conn.execute(text("""
            INSERT INTO programs (id, name, description, is_active, created_at)
            VALUES (
                'e561e788-f053-40cc-a4a3-5040627f27de',
                'EDUCA',
                'Programa de Acompañamiento Educativo Integral',
                TRUE,
                '2026-06-22 03:00:00'
            )
            ON CONFLICT (id) DO NOTHING;
        """))
        print("Program EDUCA verified/inserted.")

        # 2. Document Type Configs
        doc_configs = [
            {
                "id": "270072c7-39ee-45b3-b8d6-462e64af6dfc",
                "code": "DJ",
                "name": "Declaración Jurada",
                "year": 2026,
                "model_id": "doc-extractor-declaracion-jurada-v1",
                "version": 1,
                "preview_image_url": "https://drive.google.com/uc?export=view&id=1Im5BWqMOZ5SI8A-7I2OAMYCZxjF803hP",
                "is_active": True,
                "created_at": "2026-06-22 03:03:11.653303"
            },
            {
                "id": "459da05e-1cb9-4f1f-b70e-abc0251f09b3",
                "code": "FINS",
                "name": "Ficha de Inscripción EDUCA",
                "year": 2026,
                "model_id": "extractor-fichas-inscripcion-v3",
                "version": 1,
                "preview_image_url": "https://drive.google.com/uc?export=view&id=1GWYFqrVR_3zH_hAP2u7wYldcaDR8ADS3",
                "is_active": True,
                "created_at": "2026-06-22 03:02:59.075432"
            },
            {
                "id": "544b6c36-3aeb-4291-96d8-9b0e2b3a5107",
                "code": "DNIAP",
                "name": "DNI Apoderado",
                "year": 2026,
                "model_id": "prebuilt-idDocument",
                "version": 1,
                "preview_image_url": "https://drive.google.com/uc?export=view&id=1RYgPwW31D4Y3Tb4tT2Yr1gTLyvZw_m5m",
                "is_active": True,
                "created_at": "2026-06-22 03:02:35.385964"
            },
            {
                "id": "6d5ce9df-2674-4837-92a1-4f9220f0920b",
                "code": "DNIBE",
                "name": "DNI Beneficiario",
                "year": 2026,
                "model_id": "prebuilt-idDocument",
                "version": 1,
                "preview_image_url": "https://drive.google.com/uc?export=view&id=1q2EAsFniC9jG8KgqCjqVLDL7l3C39cYb",
                "is_active": True,
                "created_at": "2026-06-22 03:02:48.650726"
            }
        ]

        for dc in doc_configs:
            await conn.execute(text("""
                INSERT INTO document_type_configs (id, code, name, year, model_id, version, preview_image_url, is_active, created_at)
                VALUES (:id, :code, :name, :year, :model_id, :version, :preview_image_url, :is_active, :created_at)
                ON CONFLICT (id) DO UPDATE SET
                    code = EXCLUDED.code,
                    name = EXCLUDED.name,
                    year = EXCLUDED.year,
                    model_id = EXCLUDED.model_id,
                    version = EXCLUDED.version,
                    preview_image_url = EXCLUDED.preview_image_url,
                    is_active = EXCLUDED.is_active;
            """), dc)
        print("4 document_type_configs verified/inserted.")

        # 3. Activity
        await conn.execute(text("""
            INSERT INTO activities (id, program_id, name, is_active, created_at)
            VALUES (
                '05194c0c-9ff7-4b4d-97f6-af51d62521c3',
                'e561e788-f053-40cc-a4a3-5040627f27de',
                'INSCRIPCIÓN A EDUCA 2026 - I',
                TRUE,
                '2026-06-22 03:05:11.385586'
            )
            ON CONFLICT (id) DO UPDATE SET
                program_id = EXCLUDED.program_id,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active;
        """))
        print("Activity 'INSCRIPCIÓN A EDUCA 2026 - I' verified/inserted.")

        # 4. Activity Requirements
        requirements = [
            {
                "id": "13fd56b8-3cdc-437d-8b09-6c258255cbb9",
                "activity_id": "05194c0c-9ff7-4b4d-97f6-af51d62521c3",
                "document_type_config_id": "544b6c36-3aeb-4291-96d8-9b0e2b3a5107",
                "is_required": True,
                "confidence_threshold": 0.85
            },
            {
                "id": "6a64f4b3-2a9a-460c-8805-f7f3d1a83885",
                "activity_id": "05194c0c-9ff7-4b4d-97f6-af51d62521c3",
                "document_type_config_id": "270072c7-39ee-45b3-b8d6-462e64af6dfc",
                "is_required": True,
                "confidence_threshold": 0.85
            },
            {
                "id": "b23c35ca-d667-49a5-a953-d3acb19272b2",
                "activity_id": "05194c0c-9ff7-4b4d-97f6-af51d62521c3",
                "document_type_config_id": "6d5ce9df-2674-4837-92a1-4f9220f0920b",
                "is_required": True,
                "confidence_threshold": 0.85
            },
            {
                "id": "d6146e88-7f08-428a-9b0e-760e9364749c",
                "activity_id": "05194c0c-9ff7-4b4d-97f6-af51d62521c3",
                "document_type_config_id": "459da05e-1cb9-4f1f-b70e-abc0251f09b3",
                "is_required": True,
                "confidence_threshold": 0.85
            }
        ]

        for req in requirements:
            await conn.execute(text("""
                INSERT INTO activity_requirements (id, activity_id, document_type_config_id, is_required, confidence_threshold)
                VALUES (:id, :activity_id, :document_type_config_id, :is_required, :confidence_threshold)
                ON CONFLICT (id) DO UPDATE SET
                    activity_id = EXCLUDED.activity_id,
                    document_type_config_id = EXCLUDED.document_type_config_id,
                    is_required = EXCLUDED.is_required,
                    confidence_threshold = EXCLUDED.confidence_threshold;
            """), req)
        print("4 activity_requirements verified/inserted.")

        # 5. User role update to admin
        await conn.execute(text("""
            UPDATE users SET role = 'admin' WHERE email = 'enzo.trujillo@cruz-blanca.org';
        """))
        print("User enzo.trujillo@cruz-blanca.org updated to role 'admin'.")

asyncio.run(seed())
