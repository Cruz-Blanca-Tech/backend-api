import asyncio
import logging
from uuid import uuid4
from src.core.database import engine, Base
from src.core.bootstrap import bootstrap_event_subscribers
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.dossier_pdf_generated_event import DossierPdfGeneratedEvent

logging.basicConfig(level=logging.INFO)

async def test_flow():
    print("Inicializando base de datos para prueba...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Registrando suscriptores de eventos...")
    bootstrap_event_subscribers()

    batch_id = uuid4()
    triage_case_id = uuid4()
    
    # 1. Simular Evento de Aprobación de Triaje
    # (Este evento es atrapado por el MDM para crear al beneficiario)
    print("\n--- PASO 1: SIMULANDO APROBACIÓN DE TRIAJE ---")
    dossier_data = {
        "beneficiary": {
            "dni": "88888888",
            "first_name": "PRUEBA",
            "last_name": "EVENTOS",
            "birth_date": "2015-01-01",
            "gender": "MALE"
        },
        "education": {
            "school": "Colegio Mayor",
            "grade": "1ro Secundaria"
        }
    }
    
    event_approved = DossierApprovedEvent(
        triage_case_id=triage_case_id,
        batch_id=batch_id,
        activity_type="EDUCA_DOSSIER",
        dni_reference="1111", # DNI original subido (erróneo)
        dossier_data=dossier_data,
        approved_by=uuid4()
    )
    
    await EventDispatcher.dispatch(event_approved)
    
    # Damos un momento para que los eventos asíncronos terminen
    await asyncio.sleep(1)

    # 2. Simular Evento de Generación de PDF desde OCR
    # (El OCR usó el DNI corregido '88888888' y ahora avisa al MDM)
    print("\n--- PASO 2: SIMULANDO GENERACIÓN DE PDF DEL OCR ---")
    event_pdf = DossierPdfGeneratedEvent(
        batch_id=batch_id,
        dni="88888888",  # El DNI real corregido
        document_type="EDUCA_DOSSIER",
        file_url="s3://cruzblanca-docs/88888888_educa_final.pdf",
        year=2026
    )
    
    await EventDispatcher.dispatch(event_pdf)
    await asyncio.sleep(1)

    print("\n¡Prueba finalizada! Puedes verificar en la base de datos si el Beneficiario 88888888 fue creado y si tiene el documento histórico adjunto.")

if __name__ == "__main__":
    asyncio.run(test_flow())
