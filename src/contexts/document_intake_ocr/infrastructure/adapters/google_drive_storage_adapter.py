# src/contexts/document_intake_ocr/infrastructure/adapters/google_drive_storage_adapter.py

import asyncio
from typing import Dict, Any, List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
import io

from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.domain.value_objects.file_item import FileItem
from src.core.validators.exceptions import ExternalServiceException

class GoogleDriveStorageAdapter(DocumentStorage):
    """
    Implementación en infraestructura del almacenamiento en la nube mediante Google Drive API.
    Diseñado para operar en Unidades Compartidas (Shared Drives) garantizando la inmutabilidad 
    y seguridad del Drive de origen mediante un patrón de doble cliente y permisos temporales.
    """
    
    def __init__(self, credentials_info: Dict[str, Any], scopes: List[str], base_folder_id: str):
        """
        Inicializa el adaptador con las credenciales de la Cuenta de Servicio.
        """
        self._credentials_info = credentials_info
        self._scopes = scopes
        self._robot_email = credentials_info.get("client_email")
        self._base_folder_id = base_folder_id
        
    async def ensure_batch_directory(self, activity_name: str, batch_id: str) -> str:
        """
        Wrapper asíncrono para la creación de la jerarquía de carpetas.
        """
        print(f"DEBUG: base_id recibido: '{ self._base_folder_id}'") # <--- AÑADE ESTO
        try:
            return await asyncio.to_thread(
                self._sync_ensure_batch_directory, 
                activity_name, 
                batch_id
            )
        except HttpError as e:
            raise ExternalServiceException("Google Drive", "Ensure Directory", e.reason)
        except Exception as e:
            raise ExternalServiceException("Google Drive", "Ensure Directory", str(e))
    
    def _sync_ensure_batch_directory(self, activity_name: str, batch_id: str) -> str:
        base_credentials = service_account.Credentials.from_service_account_info(
            self._credentials_info, scopes=self._scopes
        )
        service = build('drive', 'v3', credentials=base_credentials, cache_discovery=False)
        
        # 1. Buscar o Crear Carpeta de ACTIVIDAD dentro de la base_folder
        query = f"name = '{activity_name}' and '{self._base_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, spaces='drive', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        
        files = response.get('files', [])
        if files:
            activity_folder_id = files[0]['id']
        else:
            # Crear la carpeta de actividad
            folder_metadata = {
                'name': activity_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self._base_folder_id]
            }
            folder = service.files().create(body=folder_metadata, supportsAllDrives=True, fields='id').execute()
            activity_folder_id = folder.get('id')
            
        # 2. Crear Carpeta de LOTE dentro de la actividad
        batch_folder_metadata = {
            'name': f"Lote_{batch_id}",
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [activity_folder_id]
        }
        batch_folder = service.files().create(body=batch_folder_metadata, supportsAllDrives=True, fields='id').execute()
        
        return batch_folder.get('id')
    
    async def copy_to_custody(self, file_item: FileItem, target_folder_id: str, user_email: str) -> str:
        """
        Wrapper asíncrono para la copia segura Cloud-to-Cloud.
        """
        try:
            return await asyncio.to_thread(
                self._sync_copy_to_custody,
                file_item,
                target_folder_id,
                user_email
            )
        except HttpError as e:
            raise ExternalServiceException("Google Drive API", "Copy to Custody", e.reason)
        except Exception as e:
            raise ExternalServiceException("Google Drive Adapter", "Copy to Custody", str(e))

    def _sync_copy_to_custody(self, file_item: FileItem, target_folder_id: str, user_email: str) -> str:
        """
        Lógica síncrona que resuelve el acceso a archivos personales.
        En lugar de usar 'copy' (que falla por políticas de Workspace al intentar compartir),
        descargamos el archivo a memoria suplantando al voluntario, y lo subimos a la bóveda
        actuando como el Robot.
        """
        # 1. Descargar a RAM usando la identidad del Voluntario
        file_bytes = self._sync_download_file(file_item, user_email)
        
        # 2. Obtener el mimetype basándonos en la extensión
        mime_type = "application/pdf"
        if file_item.file_name.lower().endswith(".jpg") or file_item.file_name.lower().endswith(".jpeg"):
            mime_type = "image/jpeg"
        elif file_item.file_name.lower().endswith(".png"):
            mime_type = "image/png"
            
        # 3. Subir a la bóveda como el Robot
        webview_link = self._sync_upload_file_to_folder(
            folder_id=target_folder_id,
            file_bytes=file_bytes,
            filename=file_item.file_name,
            mime_type=mime_type
        )
        
        return webview_link

    # Agregar al final de src/contexts/document_intake_ocr/infrastructure/adapters/google_drive_storage_adapter.py

    async def download_file(self, file_item: FileItem, user_email: str) -> bytes:
        try:
            return await asyncio.to_thread(
                self._sync_download_file, file_item, user_email
            )
        except HttpError as e:
            raise ExternalServiceException("Google Drive API", "Download File", e.reason)
        except Exception as e:
            raise ExternalServiceException("Google Drive Adapter", "Download File", str(e))

    def _sync_download_file(self, file_item: FileItem, user_email: str) -> bytes:
        """
        Descarga los bytes del archivo suplantando al usuario que tiene acceso al origen.
        """
        base_credentials = service_account.Credentials.from_service_account_info(
            self._credentials_info, scopes=self._scopes
        )
        delegated_credentials = base_credentials.with_subject(user_email)
        service_volunteer = build('drive', 'v3', credentials=delegated_credentials, cache_discovery=False)
        
        # Solicitamos los bytes multimedia del archivo de forma nativa
        request = service_volunteer.files().get_media(fileId=file_item.file_id)
        return request.execute()

    async def ensure_beneficiary_directory(self, dni: str) -> str:
        """Crea o recupera la carpeta del beneficiario en el Drive de Custodia."""
        return await asyncio.to_thread(self._sync_ensure_beneficiary_directory, dni)

    def _sync_ensure_beneficiary_directory(self, dni: str) -> str:
        base_credentials = service_account.Credentials.from_service_account_info(
            self._credentials_info, scopes=self._scopes
        )
        service = build('drive', 'v3', credentials=base_credentials, cache_discovery=False)
        
        folder_name = f"Beneficiary_{dni}"
        query = f"name = '{folder_name}' and '{self._base_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, spaces='drive', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        
        files = response.get('files', [])
        if files:
            return files[0]['id']
            
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self._base_folder_id]
        }
        folder = service.files().create(body=folder_metadata, supportsAllDrives=True, fields='id').execute()
        return folder.get('id')

    async def upload_file_to_folder(self, folder_id: str, file_bytes: bytes, filename: str, mime_type: str = "application/pdf") -> str:
        return await asyncio.to_thread(self._sync_upload_file_to_folder, folder_id, file_bytes, filename, mime_type)

    def _sync_upload_file_to_folder(self, folder_id: str, file_bytes: bytes, filename: str, mime_type: str) -> str:
        base_credentials = service_account.Credentials.from_service_account_info(
            self._credentials_info, scopes=self._scopes
        )
        service = build('drive', 'v3', credentials=base_credentials, cache_discovery=False)
        # Check if file exists in the folder
        query = f"name = '{filename}' and '{folder_id}' in parents and trashed = false"
        response = service.files().list(q=query, spaces='drive', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = response.get('files', [])
        
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        
        if files:
            existing_file_id = files[0]['id']
            file_metadata = {'name': filename}
            file = service.files().update(
                fileId=existing_file_id, 
                body=file_metadata, 
                media_body=media, 
                supportsAllDrives=True, 
                fields='id, webViewLink'
            ).execute()
        else:
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            file = service.files().create(
                body=file_metadata, 
                media_body=media, 
                supportsAllDrives=True, 
                fields='id, webViewLink'
            ).execute()
            
        return file.get('id')

    def download_file_to_memory(self, file_id: str) -> bytes:
        """Descarga un archivo directamente usando las credenciales del Robot, asumiendo que ya está en Custodia."""
        # Si se guardó la URL completa de Drive, extraemos solo el ID del archivo
        if file_id.startswith("http"):
            import re
            match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', file_id)
            if match:
                file_id = match.group(1)
            else:
                raise ValueError(f"No se pudo extraer el file ID de la URL: {file_id}")

        base_credentials = service_account.Credentials.from_service_account_info(
            self._credentials_info, scopes=self._scopes
        )
        service = build('drive', 'v3', credentials=base_credentials, cache_discovery=False)
        request = service.files().get_media(fileId=file_id)
        return request.execute()