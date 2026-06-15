# src/contexts/document_intake/infrastructure/storage/google_drive_vault.py

import datetime
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from src.contexts.document_intake_ocr.domain.ports.vault_file_service import VaultFileService

class GoogleDriveVaultService(VaultFileService):
    def __init__(self, credentials, vault_folder_id: str):
        self.service = build('drive', 'v3', credentials=credentials)
        self.vault_folder_id = vault_folder_id

    def archive(self, file_id: str, content: bytes) -> str:
        """
        Copia el contenido hacia la carpeta de custodia (Vault).
        """
        # 1. Definimos los metadatos: nombre y carpeta padre
        file_metadata = {
            'name': f"custodia_{file_id}_{datetime.utcnow().isoformat()}.pdf",
            'parents': [self.vault_folder_id]
        }
        
        # 2. Preparamos el contenido en memoria
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype='application/pdf')
        
        # 3. Creamos el archivo en Drive
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        # 4. Retornamos el nuevo ID en el Vault
        return file.get('id')