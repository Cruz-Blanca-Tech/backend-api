# src/contexts/document_intake_ocr/domain/value_objects/group_key.py
from dataclasses import dataclass
import re

_STANDARD_DNI = re.compile(r"^\d{8}$")


@dataclass(frozen=True)
class GroupKey:
    """Clave con la que el intake agrupa los documentos de un expediente.

    Es el token que aparece antes del primer `_` del nombre del archivo
    (`12345678_FINS.pdf` -> `12345678`). **No es un DNI validado** y a
    propósito no lo es: el operador escribe ese token a mano al renombrar el
    escaneo, así que un dígito de más o de menos es un hecho habitual. Antes
    ese token se validaba con el VO `DNI` y el archivo entero se descartaba,
    perdiéndose la única copia de un documento obligatorio sin más rastro que
    un `"SIN_DNI"` en la base.

    Por eso la agrupación acepta cualquier token numérico. El DNI real del
    beneficiario lo aporta el OCR del documento y lo contrasta el maestro
    (ver `data_quality_triage/.../dossier_processor.py`); esta clave es solo
    una etiqueta de archivado y nunca se escribe en el maestro de
    beneficiarios.

    Deliberadamente NO expone un `dni` derivado: la tentación de castear la
    clave a `DNI` para guardarla en el maestro es justo el error que esta clase
    existe para evitar. Para el DNI del beneficiario hay que leer el dossier.
    """

    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("La clave de agrupación no puede estar vacía.")
        if not self.value.isdigit():
            raise ValueError(
                f"La clave de agrupación '{self.value}' no es numérica: "
                "el nombre del archivo debe seguir la convención {DNI}_{CODIGO}.ext"
            )

    @property
    def is_standard_dni(self) -> bool:
        """True solo si el token es un DNI de 8 dígitos.

        Sirve para preguntar si la clave además sirve como DNI, nunca para
        suponer que lo es: la forma canónica de esa pregunta en el dominio de
        triaje es `_dni_valid` (`dossier_processor.py`).
        """
        return bool(_STANDARD_DNI.match(self.value))

    def __str__(self) -> str:
        return self.value
