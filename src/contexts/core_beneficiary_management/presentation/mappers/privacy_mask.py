"""Enmascarado de datos personales para el rol Visualizador (RF-11, ISO/IEC 27001 A.8.11).

Replica en el servidor el criterio del frontend (beneficiario-format.ts):
  - DNI: solo los últimos 4 dígitos visibles ("****5678").
  - Nombre: inicial de la primera palabra; el resto, inicial + hasta 4 asteriscos.
"""
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import BeneficiarySummaryResponse


def mask_dni(dni: str) -> str:
    dni = (dni or "").strip()
    return "****" + dni[-4:] if dni else ""


def _mask_word(word: str, first: bool) -> str:
    if not word:
        return ""
    if first:
        return word[0].upper()
    return word[0].upper() + "*" * min(max(len(word) - 1, 1), 4)


def mask_first_name(first_name: str) -> str:
    words = (first_name or "").split()
    return " ".join(_mask_word(w, i == 0) for i, w in enumerate(words))


def mask_last_name(last_name: str) -> str:
    return " ".join(_mask_word(w, False) for w in (last_name or "").split())


def mask_summary(item: BeneficiarySummaryResponse) -> BeneficiarySummaryResponse:
    return item.model_copy(update={
        "dni": mask_dni(item.dni),
        "first_name": mask_first_name(item.first_name),
        "last_name": mask_last_name(item.last_name),
        "birth_date": None,
    })
