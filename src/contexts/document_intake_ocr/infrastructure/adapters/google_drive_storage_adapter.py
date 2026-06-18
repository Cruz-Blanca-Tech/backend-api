# src/contexts/document_intake_ocr/infrastructure/adapters/google_drive_storage_adapter.py

import asyncio
from typing import Dict, Any, List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
        Lógica síncrona que orquesta el apretón de manos de permisos entre
        el voluntario y el sistema central para escribir en Unidades Compartidas.
        """
        # 1. Credenciales Base (El Robot actuando como sí mismo)
        base_credentials = service_account.Credentials.from_service_account_info(
            self._credentials_info, scopes=self._scopes
        )
        service_robot = build('drive', 'v3', credentials=base_credentials, cache_discovery=False)
        
        # 2. Credenciales Delegadas (El Robot usando la identidad del Voluntario)
        delegated_credentials = base_credentials.with_subject(user_email)
        service_volunteer = build('drive', 'v3', credentials=delegated_credentials, cache_discovery=False)
        
        # 3. PUENTE DE PERMISOS: El voluntario le da acceso de lectura temporal al Robot
        user_permission = {
            'type': 'user',
            'role': 'reader',
            'emailAddress': self._robot_email
        }
        
        permission = service_volunteer.permissions().create(
            fileId=file_item.file_id,
            body=user_permission,
            fields='id'
        ).execute()
        
        try:
            # 4. COPIA: El Robot realiza la copia nativa hacia la subcarpeta del Lote
            body = {
                'parents': [target_folder_id],
                'name': file_item.file_name
            }
            new_file = service_robot.files().copy(
                fileId=file_item.file_id,
                body=body,
                supportsAllDrives=True, # Obligatorio para escribir en Shared Drives
                fields='id, webViewLink'
            ).execute()
            
            # Devolvemos el enlace seguro del archivo recién custodiado
            return new_file.get('webViewLink', f"https://drive.google.com/open?id={new_file.get('id')}")
        
        except HttpError as e:
            # ESTO ES LO QUE DEBES MIRAR EN TUS LOGS
            print(f"ERROR CRÍTICO EN DRIVE: {e.content}")
            raise ExternalServiceException(...)
        finally:
            # 5. LIMPIEZA GARANTIZADA: El voluntario revoca el acceso del Robot
            # Este bloque se ejecuta incluso si el paso 4 falla por cualquier motivo
            service_volunteer.permissions().delete(
                fileId=file_item.file_id,
                permissionId=permission['id']
            ).execute()

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