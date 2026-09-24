from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class DniRaw(BaseModel):
    """Representa el payload crudo extraído de un DNI (Aplica para DNIAP y DNIBE)"""
    document_number: Optional[str] = Field(default=None, alias="DocumentNumber", title="Número de Documento")
    first_name: Optional[str] = Field(default=None, alias="FirstName", title="Nombres")
    last_name: Optional[str] = Field(default=None, alias="LastName", title="Apellidos")
    date_of_birth: Optional[str] = Field(default=None, alias="DateOfBirth", title="Fecha de Nacimiento")
    date_of_expiration: Optional[str] = Field(default=None, alias="DateOfExpiration", title="Fecha de Expiración")
    gender: Optional[str] = Field(default=None, alias="Gender", title="Sexo")
    address: Optional[Any] = Field(default=None, alias="Address", title="Dirección")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    @model_validator(mode='before')
    @classmethod
    def flatten_confidence_objects(cls, data: Any) -> Any:
        if isinstance(data, dict):
            flattened = {}
            for key, val in data.items():
                if isinstance(val, dict) and "value" in val:
                    extracted_val = val["value"]
                else:
                    extracted_val = val
                
                # address is often a dict in DNI, so we don't cast dicts to string
                if extracted_val is not None and not isinstance(extracted_val, (list, dict)):
                    flattened[key] = str(extracted_val)
                else:
                    flattened[key] = extracted_val
                    
            # Auto-limpiar el DNI (quitar guiones, espacios y dígito verificador)
            for dni_key in ["DocumentNumber", "document_number"]:
                if dni_key in flattened and flattened[dni_key]:
                    import re
                    val_clean = str(flattened[dni_key]).replace(" ", "").replace("-", "")
                    match = re.search(r'\d{8}', val_clean)
                    if match:
                        flattened[dni_key] = match.group(0)

            # Auto-limpiar fechas a YYYY-MM-DD (soporta "02 10 2009", "02/10/2009")
            for date_key in ["DateOfBirth", "date_of_birth", "DateOfExpiration", "date_of_expiration"]:
                if date_key in flattened and flattened[date_key]:
                    import re
                    val_date = str(flattened[date_key])
                    match = re.search(r'(\d{2})[\s\-/]+(\d{2})[\s\-/]+(\d{2,4})', val_date)
                    if match:
                        dd, mm, yyyy = match.groups()
                        if len(yyyy) == 2:
                            yyyy = "20" + yyyy if int(yyyy) < 50 else "19" + yyyy
                        flattened[date_key] = f"{yyyy}-{mm}-{dd}"
            
            # Normalizar género a M o F
            for gender_key in ["Gender", "gender"]:
                if gender_key in flattened and flattened[gender_key]:
                    val_g = str(flattened[gender_key]).strip().upper()
                    if val_g.startswith("M") or "MASC" in val_g:
                        flattened[gender_key] = "M"
                    elif val_g.startswith("F") or "FEM" in val_g:
                        flattened[gender_key] = "F"

            return flattened
        return data
