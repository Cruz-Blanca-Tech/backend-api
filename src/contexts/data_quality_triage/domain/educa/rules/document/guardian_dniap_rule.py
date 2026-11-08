"""D3: el apoderado elegido por el revisor debe coincidir con la copia de su DNI (DNIAP).

Al ingresar el expediente, el DNI del apoderado se cruza con la DJ y el DNIAP
(`GuardianDniCrosscheckRule`). Pero en la corrección el revisor elige al
apoderado de una lista de adultos y, sin esta regla, el guardado no volvía a
mirar el DNIAP: si elegía al padre y la copia era de la madre, el expediente se
aprobaba sin aviso.
"""
from typing import Optional

from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy


def guardian_vs_dniap_issue(guardian_dni: Optional[str], dniap_number: Optional[str]) -> Optional[FieldDiscrepancy]:
    """Devuelve un ERROR si el apoderado elegido no es la persona del DNIAP.

    Solo compara cuando ambos DNIs son válidos (8 dígitos): si el DNIAP no se
    pudo leer, no hay contra qué comparar, y la falta de apoderado ya la reporta
    `GuardianPresenceRule`.
    """
    g = (guardian_dni or "").strip()
    d = (dniap_number or "").strip()
    if not (g.isdigit() and len(g) == 8 and d.isdigit() and len(d) == 8):
        return None
    if g == d:
        return None
    return FieldDiscrepancy(
        field_name="related_adults.guardian",
        expected_pattern=f"DNI de la copia del apoderado: {d}",
        actual_value=g,
        rule_description=(
            f"El apoderado elegido (DNI {g}) no coincide con la copia del DNI del apoderado "
            f"(DNI {d}). Elegí como apoderado al adulto con DNI {d}, corregí su DNI o "
            "reemplazá la copia del DNI si corresponde a otra persona."
        ),
        severity="ERROR",
        document_code="DNIAP",
    )
