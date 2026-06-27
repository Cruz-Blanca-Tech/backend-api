import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple

from src.contexts.data_quality_triage.domain.utils.string_utils import calculate_similarity
from src.contexts.data_quality_triage.domain.value_objects.dossier_data import DossierData
from src.contexts.data_quality_triage.domain.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.value_objects.parents_data import ParentsData
from src.contexts.data_quality_triage.domain.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.value_objects.medical_data import MedicalData


@dataclass
class DeclarationData:
    day: Optional[str] = None
    month: Optional[str] = None
    year: Optional[str] = None
    child_dni: Optional[str] = None
    child_name: Optional[str] = None
    father_dni: Optional[str] = None
    mother_dni: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "child_dni": self.child_dni,
            "child_name": self.child_name,
            "father_dni": self.father_dni,
            "mother_dni": self.mother_dni,
            "father_name": self.father_name,
            "mother_name": self.mother_name
        }


@dataclass
class EducaInscription(DossierData):
    beneficiary: BeneficiaryData
    parents: ParentsData
    education: EducationData
    medical: MedicalData

    def to_dict(self) -> dict:
        return {
            "beneficiary": self.beneficiary.to_dict(),
            "parents": self.parents.to_dict(),
            "education": self.education.to_dict(),
            "medical": self.medical.to_dict()
        }

    def validate_completeness(self) -> Tuple[bool, List[str]]:
        """Valida que el dossier esté completo según las reglas de negocio finales."""
        is_valid = True
        issues = []

        # 1. Beneficiary name presence
        if not self.beneficiary.first_name or not self.beneficiary.last_name:
            issues.append("El nombre y apellido del beneficiario son obligatorios.")
            is_valid = False

        # 2. Emergency number presence
        phones = []
        if self.parents.father and self.parents.father.phone:
            phones.append(self.parents.father.phone)
        if self.parents.mother and self.parents.mother.phone:
            phones.append(self.parents.mother.phone)
        if self.parents.guardian and self.parents.guardian.phone:
            phones.append(self.parents.guardian.phone)
        
        if not phones:
            issues.append("Debe existir al menos un número de emergencia (teléfono) registrado para los padres o tutor.")
            is_valid = False

        # 3. Apoderado Validation
        if not self.parents.apoderado_type:
            issues.append("No se ha asignado un Apoderado al dossier.")
            is_valid = False
        else:
            apoderado = getattr(self.parents, self.parents.apoderado_type, None)
            if not apoderado or not apoderado.dni or not apoderado.full_name:
                issues.append(f"El apoderado asignado ({self.parents.apoderado_type}) debe tener DNI y Nombre Completo.")
                is_valid = False

        self.beneficiary.validation_issues = [i for i in issues if "beneficiario" in i.lower()]
        self.parents.validation_issues = [i for i in issues if "beneficiario" not in i.lower()]

        return is_valid, issues
