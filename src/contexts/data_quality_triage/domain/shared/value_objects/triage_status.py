from enum import Enum

class TriageStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    CORRECTED = "CORRECTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    # --- LEGADO (solo lectura) ---
    # La columna `triage_cases.status` es un VARCHAR: guarda el string crudo, no
    # un ENUM de Postgres, así que la BD conserva valores escritos por versiones
    # anteriores del dominio. `TriageCaseMapper.to_domain` hace `TriageStatus(...)`
    # sobre ese string, y un valor ausente aquí revienta con ValueError toda
    # lectura de triaje (incluido el listado de lotes). Ningún flujo actual
    # ESCRIBE estos estados; existen para poder releer las filas históricas.
    INCOMPLETE = "INCOMPLETE"

class TriageVerdict(str, Enum):
    AUTO_APPROVED = "AUTO_APPROVED"
    REQUIRES_TRIAGE = "REQUIRES_TRIAGE"
    MANUALLY_APPROVED = "MANUALLY_APPROVED"
    MANUALLY_REJECTED = "MANUALLY_REJECTED"

    # --- LEGADO (solo lectura) ---
    # Mismo motivo que en TriageStatus: veredictos retirados del dominio que
    # siguen presentes en `triage_cases.verdict`. El frontend ya ignora las
    # claves desconocidas de `triage_summary.verdicts` (ver
    # `triage-verdict-config.ts`), así que aparecer en el resumen no rompe la UI.
    MISSING_DOCUMENTS = "MISSING_DOCUMENTS"
    DOCUMENT_ERROR = "DOCUMENT_ERROR"
    DATA_DISCREPANCY = "DATA_DISCREPANCY"

class BatchVerificationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    NOT_FOUND = "NOT_FOUND"
