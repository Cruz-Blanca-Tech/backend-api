from pydantic import BaseModel, Field, field_validator

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp'}

class FileItemSchema(BaseModel):
    source_id: str = Field(..., description="Enlace temporal o ruta universal para descargar el archivo")
    file_name: str = Field(..., description="El nombre completo del archivo, ej: 71223344_FINS.pdf")

    @field_validator('file_name')
    @classmethod
    def validate_extension(cls, v: str) -> str:
        import os
        ext = os.path.splitext(v)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Formato no soportado ({ext}). Solo se permite: PDF, JPG, PNG, TIFF, BMP")
        return v
