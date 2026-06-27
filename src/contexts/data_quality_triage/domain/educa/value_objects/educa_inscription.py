import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple

from src.contexts.data_quality_triage.domain.shared.utils.string_utils import calculate_similarity
from src.contexts.data_quality_triage.domain.shared.value_objects.dossier_data import DossierData
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData

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
    related_adults: FamilyData
    education: EducationData
    medical: MedicalData

    def to_dict(self) -> dict:
        return {
            "beneficiary": self.beneficiary.to_dict(),
            "related_adults": self.related_adults.to_dict(),
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

        # 1.1 Beneficiary Age vs Birth Date
        if self.beneficiary.birth_date and self.beneficiary.age is not None:
            try:
                from datetime import datetime
                # Asumimos formato AAAA-MM-DD
                birth_date = datetime.strptime(self.beneficiary.birth_date.split("T")[0], "%Y-%m-%d")
                current_year = datetime.now().year
                calculated_age = current_year - birth_date.year
                # Permitimos un margen de 1 año (por si aún no cumple meses)
                if abs(calculated_age - int(self.beneficiary.age)) > 1:
                    issues.append(f"La edad proporcionada ({self.beneficiary.age}) no coincide lógicamente con la fecha de nacimiento ({self.beneficiary.birth_date}).")
                    is_valid = False
            except Exception:
                # Si el formato falla, lo atrapamos pero no lo validamos matemáticamente
                pass

        # 2. Emergency number presence (at least one adult must have a phone)
        phones = [adult.phone for adult in self.related_adults.adults if adult.phone]
        if not phones:
            issues.append("Debe existir al menos un número de emergencia (teléfono) registrado para los adultos relacionados.")
            is_valid = False

        # 3. Apoderado Validation
        if not self.related_adults.guardian_dni:
            issues.append("No se ha asignado un Apoderado (guardian) al dossier por su DNI.")
            is_valid = False
        else:
            guardian = next((a for a in self.related_adults.adults if a.dni == self.related_adults.guardian_dni), None)
            if not guardian or not guardian.full_name:
                issues.append(f"El apoderado asignado (DNI: {self.related_adults.guardian_dni}) debe estar registrado en la lista de adultos y tener Nombre Completo.")
                is_valid = False

        self.beneficiary.validation_issues = [i for i in issues if "beneficiario" in i.lower() or "edad" in i.lower()]
        self.related_adults.validation_issues = [i for i in issues if "beneficiario" not in i.lower() and "edad" not in i.lower()]

        return is_valid, issues
