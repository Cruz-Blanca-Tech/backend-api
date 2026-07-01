from typing import Optional
from pydantic import BaseModel, Field

class FinsRaw(BaseModel):
    """Representa el payload crudo extraído de FINS"""
    # Beneficiary
    child_first_name: Optional[str] = Field(default=None, alias="child_first_name", title="Nombres", json_schema_extra={"group": "datos_nino"})
    child_last_name: Optional[str] = Field(default=None, alias="child_last_name", title="Apellidos", json_schema_extra={"group": "datos_nino"})
    child_age: Optional[str] = Field(default=None, alias="child_age", title="Edad", json_schema_extra={"group": "datos_nino"})
    child_gender: Optional[str] = Field(default=None, alias="child_gender", title="Sexo", json_schema_extra={"group": "datos_nino", "options": ["M", "F"]})
    child_birth_date: Optional[str] = Field(default=None, alias="child_birth_date", title="Fecha de Nacimiento", json_schema_extra={"group": "datos_nino"})
    child_dni: Optional[str] = Field(default=None, alias="child_dni", title="DNI del Niño/a", json_schema_extra={"group": "datos_nino"})

    # Address
    address_lot: Optional[str] = Field(default=None, alias="address_lot", title="Lote", json_schema_extra={"group": "direccion"})
    address_block: Optional[str] = Field(default=None, alias="address_block", title="Manzana", json_schema_extra={"group": "direccion"})
    address_city: Optional[str] = Field(default=None, alias="address_city", title="Ciudad", json_schema_extra={"group": "direccion"})
    address_district: Optional[str] = Field(default=None, alias="address_district", title="Distrito", json_schema_extra={"group": "direccion"})
    address_neighborhood: Optional[str] = Field(default=None, alias="address_neighborhood", title="Urbanización", json_schema_extra={"group": "direccion"})

    # Parents
    parents_father_full_name: Optional[str] = Field(default=None, alias="parents_father_full_name", title="Padre", json_schema_extra={"group": "padres"})
    parents_father_phone: Optional[str] = Field(default=None, alias="parents_father_phone", title="Teléfono Padre", json_schema_extra={"group": "padres"})
    parents_father_dni: Optional[str] = Field(default=None, alias="parents_father_dni", title="DNI Padre", json_schema_extra={"group": "padres"})
    parents_mother_full_name: Optional[str] = Field(default=None, alias="parents_mother_full_name", title="Madre", json_schema_extra={"group": "padres"})
    parents_mother_phone: Optional[str] = Field(default=None, alias="parents_mother_phone", title="Teléfono Madre", json_schema_extra={"group": "padres"})
    parents_mother_dni: Optional[str] = Field(default=None, alias="parents_mother_dni", title="DNI Madre", json_schema_extra={"group": "padres"})
    parents_guardian_full_name: Optional[str] = Field(default=None, alias="parents_guardian_full_name", title="Apoderado", json_schema_extra={"group": "padres"})
    parents_guardian_phone: Optional[str] = Field(default=None, alias="parents_guardian_phone", title="Teléfono Apoderado", json_schema_extra={"group": "padres"})
    parents_guardian_dni: Optional[str] = Field(default=None, alias="parents_guardian_dni", title="DNI Apoderado", json_schema_extra={"group": "padres"})

    # Education
    child_school: Optional[str] = Field(default=None, alias="child_school", title="Colegio", json_schema_extra={"group": "educacion"})
    child_grade: Optional[str] = Field(default=None, alias="child_grade", title="Grado", json_schema_extra={"group": "educacion"})
    educational_knows_how_to_read_yes: Optional[str] = Field(default=None, alias="educational_knows_how_to_read_yes")
    educational_knows_how_to_write_yes: Optional[str] = Field(default=None, alias="educational_knows_how_to_write_yes")
    educational_has_repeated_grade_yes: Optional[str] = Field(default=None, alias="educational_has_repeated_grade_yes")
    educational_has_learning_difficulties_yes: Optional[str] = Field(default=None, alias="educational_has_learning_difficulties_yes")

    # Medical
    allergy_milk: Optional[str] = Field(default=None, alias="allergy_milk")
    allergy_citrus: Optional[str] = Field(default=None, alias="allergy_citrus")
    allergy_penicillin: Optional[str] = Field(default=None, alias="allergy_penicillin")
    allergy_sulfa_drugs: Optional[str] = Field(default=None, alias="allergy_sulfa_drugs")
    allergy_fish_shellfish: Optional[str] = Field(default=None, alias="allergy_fish_shellfish")
    allergy_nsaid_analgesics: Optional[str] = Field(default=None, alias="allergy_nsaid_analgesics")
    allergy_others: Optional[str] = Field(default=None, alias="allergy_others")
    allergy_other_details: Optional[str] = Field(default=None, alias="allergy_other_details")
    disease_cancer: Optional[str] = Field(default=None, alias="disease_cancer")
    disease_seizures: Optional[str] = Field(default=None, alias="disease_seizures")
    disease_parasites: Optional[str] = Field(default=None, alias="disease_parasites")
    disease_chickenpox: Optional[str] = Field(default=None, alias="disease_chickenpox")
    disease_tuberculosis: Optional[str] = Field(default=None, alias="disease_tuberculosis")
    medical_insurance_sis: Optional[str] = Field(default=None, alias="medical_insurance_sis")
    medical_insurance_essalud: Optional[str] = Field(default=None, alias="medical_insurance_essalud")
    medical_insurance_fospoli: Optional[str] = Field(default=None, alias="medical_insurance_fospoli")
    medical_insurance_other: Optional[str] = Field(default=None, alias="medical_insurance_other")
    medical_has_been_hospitalized: Optional[str] = Field(default=None, alias="medical_has_been_hospitalized")
    medical_hospitalization_reason: Optional[str] = Field(default=None, alias="medical_hospitalization_reason")
    medical_has_been_operated: Optional[str] = Field(default=None, alias="medical_has_been_operated")
    medical_operation_reason: Optional[str] = Field(default=None, alias="medical_operation_reason")
    medical_has_complete_vaccines: Optional[str] = Field(default=None, alias="medical_has_complete_vaccines")
    medical_received_tetanus_vaccine: Optional[str] = Field(default=None, alias="medical_received_tetanus_vaccine")
    medical_is_taking_medication: Optional[str] = Field(default=None, alias="medical_is_taking_medication")
    medical_medication_name: Optional[str] = Field(default=None, alias="medical_medication_name")

    # Religion
    religion_baptized: Optional[str] = Field(default=None, alias="religion_baptized", title="¿Fue bautizado?", json_schema_extra={"group": "religion"})
    religion_first_communion: Optional[str] = Field(default=None, alias="religion_first_communion", title="¿Hizo la 1ra Comunión?", json_schema_extra={"group": "religion"})

    # Permissions
    permission_haircut: Optional[str] = Field(default=None, alias="permission_haircut", title="¿Podemos cortarle el pelo?", json_schema_extra={"group": "permisos"})
    permission_medical_exams: Optional[str] = Field(default=None, alias="permission_medical_exams", title="¿Podemos hacerle exámenes médicos?", json_schema_extra={"group": "permisos"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
