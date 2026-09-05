import logging
from typing import List
from uuid import UUID
from fastapi import BackgroundTasks

from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.application.services.single_document_processor import SingleDocumentProcessor
from src.contexts.document_intake_ocr.application.event_publishers.dossier_event_publisher import DossierEventPublisher
from src.contexts.document_intake_ocr.application.mappers.raw_file_mapper import RawFileMapper
from src.contexts.document_intake_ocr.application.schemas.batch_schema import (
    AppendDocumentsRequest,
    AppendDocumentsResponse,
    FailedDocumentDetail,
)
from src.contexts.document_intake_ocr.domain.services.document_filter_service import DocumentFilterService
from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem, DocumentStatus
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.document_intake_ocr.domain.value_objects.dni import DNI
from src.core.validators.exceptions import EntityNotFoundException, DomainValidationError, ExternalServiceException

logger = logging.getLogger(__name__)

class AppendDocumentsUseCase:
    """
    Caso de uso para anexar o reintentar documentos en un expediente (Dossier) existente dentro de un lote.
    Ejecuta el filtrado de nomenclatura, actualiza el agregado del lote y dispara el OCR en segundo plano.
    """
    def __init__(
        self,
        activity_repo: ActivityRepository,
        batch_repo: BatchRepository,
        storage_adapter: DocumentStorage,
        single_doc_processor: SingleDocumentProcessor,
        event_publisher: DossierEventPublisher,
    ):
        self.activity_repo = activity_repo
        self.batch_repo = batch_repo
        self.storage_adapter = storage_adapter
        self.single_doc_processor = single_doc_processor
        self.event_publisher = event_publisher

    async def execute(
        self,
        batch_id: UUID,
        dni_reference: str,
        request: AppendDocumentsRequest,
        user_id: UUID,
        user_email: str,
        background_tasks: BackgroundTasks,
    ) -> AppendDocumentsResponse:
        # 1. Recuperar Lote y Actividad
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            raise EntityNotFoundException(f"Lote {batch_id} no encontrado.")

        activity = await self.activity_repo.get_by_id(batch.activity_id)
        if not activity:
            raise EntityNotFoundException(f"Actividad {batch.activity_id} no encontrada.")

        # 2. Mapear y filtrar los archivos
        raw_files = [RawFileMapper.to_domain(f) for f in request.files]
        valid_files, rejected_files = DocumentFilterService.filter_batch(raw_files, activity)

        # 3. Filtrar que los archivos pertenezcan al DNI solicitado
        dni_matched_files = []
        for f in valid_files:
            file_dni = str(f.extracted_dni) if f.extracted_dni else ""
            if file_dni != dni_reference:
                from src.contexts.document_intake_ocr.domain.services.document_filter_service import RejectedFile
                rejected_files.append(
                    RejectedFile(
                        file=f,
                        reason=f"El archivo pertenece al DNI {file_dni}, pero se esperaba {dni_reference}."
                    )
                )
            else:
                dni_matched_files.append(f)

        if len(dni_matched_files) == 0:
            reasons = [f"{r.file.file_name}: {r.reason}" for r in rejected_files]
            raise DomainValidationError(
                f"Ninguno de los archivos proporcionados es válido para el DNI {dni_reference}. "
                f"Detalle: {'; '.join(reasons)}"
            )

        # 4. Buscar o crear el expediente para este DNI en el lote
        target_dossier = None
        for d in batch.dossiers:
            if str(d.dni) == dni_reference:
                target_dossier = d
                break

        if not target_dossier:
            target_dossier = Dossier(
                dni=DNI(dni_reference),
                activity_id=activity.id,
                batch_id=batch.id
            )
            batch.add_dossier(target_dossier)

        # 5. Agregar o actualizar documentos en el expediente
        added_docs: List[DocumentItem] = []
        for f in dni_matched_files:
            code_str = str(f.extracted_code)
            config_id = activity.get_config_id_by_code(code_str)

            # Si ya existía un documento con ese código en el dossier, lo reemplazamos
            existing_doc = next(
                (d for d in target_dossier.documents if str(d.document_code) == code_str),
                None
            )
            if existing_doc:
                existing_doc.source_id = f.source_id
                existing_doc.file_name = f.file_name
                existing_doc.status = DocumentStatus.PENDING
                existing_doc.extracted_data = {}
                existing_doc.failure_reason = None
                added_docs.append(existing_doc)
            else:
                new_doc = DocumentItem.create_valid(
                    source_id=f.source_id,
                    document_code=f.extracted_code,
                    file_name=f.file_name,
                    dni_ref=DNI(dni_reference),
                    config_id=config_id
                )
                target_dossier.add_document(new_doc)
                added_docs.append(new_doc)

        # Registrar también cualquier archivo rechazado para auditoría
        for r in rejected_files:
            rejected_doc = DocumentItem.create_failed(
                source_id=r.file.source_id,
                file_name=r.file.file_name,
                dni_ref=r.file.extracted_dni,
                reason=r.reason
            )
            batch.add_rejected_document(rejected_doc)

        # 6. Guardar lote
        target_dossier.update_status(activity.required_documents)
        await self.batch_repo.save(batch)

        # 7. Disparar OCR en segundo plano para los nuevos documentos
        background_tasks.add_task(
            self._process_appended_documents,
            batch_id=batch.id,
            dni_reference=dni_reference,
            user_email=user_email,
        )

        failed_details = [
            FailedDocumentDetail(file_name=r.file.file_name, reason=r.reason)
            for r in rejected_files
        ]

        return AppendDocumentsResponse(
            batch_id=batch.id,
            dni_reference=dni_reference,
            dossier_status=target_dossier.status.value,
            added_documents_count=len(added_docs),
            rejected_documents_count=len(rejected_files),
            failed_files=failed_details,
            message=(
                f"Se anexaron {len(added_docs)} documento(s) al expediente {dni_reference}. "
                f"El procesamiento OCR se está ejecutando en segundo plano."
            ),
        )

    async def _process_appended_documents(
        self,
        batch_id: UUID,
        dni_reference: str,
        user_email: str,
    ) -> None:
        logger.info(f"[APPEND OCR] Iniciando OCR para expediente {dni_reference} en lote {batch_id}")
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            return

        activity = await self.activity_repo.get_by_id(batch.activity_id)
        if not activity:
            return

        target_dossier = next(
            (d for d in batch.dossiers if str(d.dni) == dni_reference),
            None
        )
        if not target_dossier:
            return

        try:
            target_folder_id = await self.storage_adapter.ensure_batch_directory(
                activity_name=activity.name,
                batch_id=str(batch.id),
            )

            for doc in target_dossier.documents:
                # Procesamos únicamente los que están pendientes (recién anexados o reintentados)
                if doc.status == DocumentStatus.PENDING:
                    try:
                        model_id = activity.get_model_id_for_document(str(doc.document_code))
                        await self.single_doc_processor.execute(
                            doc=doc,
                            model_id=model_id,
                            target_folder_id=target_folder_id,
                            user_email=user_email,
                        )
                    except Exception as doc_err:
                        logger.error(f"[APPEND OCR] Error procesando doc {doc.file_name}: {doc_err}")
                        doc.mark_as_failed(reason=str(doc_err))

            # Actualizamos el estado de completitud del expediente
            target_dossier.update_status(activity.required_documents)

            # Si el lote estaba en FAILED pero ahora tiene documentos procesados, lo pasamos a COMPLETED
            if batch.status.value == "FAILED":
                all_docs = batch.get_all_documents()
                if any(d.status.value != "FAILED" for d in all_docs):
                    batch.mark_as_completed()

            await self.batch_repo.save(batch)

            # Publicamos el evento para que Triaje re-evalúe el caso automáticamente
            if any(doc.status.value != "FAILED" for doc in target_dossier.documents):
                await self.event_publisher.publish_created(target_dossier, activity)
                await self.event_publisher.publish_batch_ocr_completed(batch.id)

            logger.info(f"[APPEND OCR] Expediente {dni_reference} procesado exitosamente.")

        except ExternalServiceException as ext_err:
            logger.critical(f"[APPEND OCR CRITICAL] Fallo en bóveda: {ext_err.message}")
        except Exception as e:
            logger.critical(f"[APPEND OCR CRITICAL] Error fatal inesperado: {str(e)}")
