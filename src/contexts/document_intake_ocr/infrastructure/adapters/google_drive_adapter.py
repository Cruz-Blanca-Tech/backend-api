import io
from typing import Iterator, List
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from src.contexts.document_intake_ocr.domain.value_objects.file_item import FileItem
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import FileStream
from src.contexts.document_intake_ocr.domain.ports.file_provider import FileProvider
from src.contexts.document_intake_ocr.domain.value_objects.supported_mime_type import SupportedMimeType

class GoogleDriveProvider(FileProvider):
    def __init__(self, credentials):
        self.service = build('drive', 'v3', credentials=credentials)

    def list_files_in_folder(self, folder_id: str) -> List[FileItem]:
        """
        Lista los archivos de una carpeta en Google Drive manejando paginación.
        Retorna una lista plana de Value Objects FileItem.
        """
        all_files = []
        page_token = None

        while True:
            # Consultamos los metadatos de la carpeta
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                pageSize=100,
                pageToken=page_token,
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()

            items = results.get('files', [])
            
            # Transformamos los objetos de Drive en tus Value Objects
            for item in items:
                file_meta = FileItem(
                    file_id=item['id'],
                    filename=item['name']
                )
                all_files.append(file_meta)

            # Verificamos si hay más páginas
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
        return all_files


    def get_file(self, file_id: str) -> FileStream:
        file_metadata = self.service.files().get(
            fileId=file_id, 
            fields="name, mimeType"
        ).execute()

        name = file_metadata.get('name')
        raw_mime_type = file_metadata.get('mimeType')

        # 1. Validamos (Fail-Fast en la frontera)
        SupportedMimeType.validate(raw_mime_type)
        
        # 2. Instanciamos el Value Object con el string que nos llegó
        # y le pedimos SU extensión (¡Tu idea aplicada!)
        domain_mime = SupportedMimeType(raw_mime_type)
        extension = domain_mime.extension 

        request = self.service.files().get_media(fileId=file_id)
        
        def chunk_generator(req) -> Iterator[bytes]:
            downloader = MediaIoBaseDownload(io.BytesIO(), req)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                yield downloader._file.getvalue()
                downloader._file.seek(0)
                downloader._file.truncate(0)

        return FileStream(
            original_name=name,
            content_stream=chunk_generator(request),
            extension=extension,
            mime_type=domain_mime.value # Pasamos el valor validado
        )