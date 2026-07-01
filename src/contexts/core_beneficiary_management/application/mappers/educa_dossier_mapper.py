import uuid
from datetime import datetime
from typing import Optional

from src.contexts.core_beneficiary_management.application.dtos.educa_dossier_dto import EducaDossierDTO
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
from src.contexts.core_beneficiary_management.domain.value_objects.medical_record import MedicalRecord
from src.contexts.core_beneficiary_management.domain.value_objects.education_record import EducationRecord
from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole
from src.contexts.core_beneficiary_management.domain.value_objects.religion_record import ReligionRecord
from src.contexts.core_beneficiary_management.domain.value_objects.permissions_record import PermissionsRecord
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone
from src.contexts.core_beneficiary_management.domain.value_objects.grade import Grade
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender

class EducaDossierMapper:
    @staticmethod
    def map_to_entity(dto: EducaDossierDTO, existing_beneficiary: Optional[Beneficiary] = None) -> Beneficiary:
        
        ben_dto = dto.beneficiary
        
        # Parse birth date
        birth_date = None
        if ben_dto.birth_date:
            try:
                birth_date = datetime.strptime(ben_dto.birth_date.split("T")[0], "%Y-%m-%d").date()
            except ValueError:
                pass

        try:
            gender_str = ben_dto.gender.upper() if ben_dto.gender else ""
            if gender_str == "F":
                gender_str = "FEMALE"
            elif gender_str == "M":
                gender_str = "MALE"
            gender = Gender(gender_str)
        except ValueError:
            gender = Gender.UNKNOWN
            
        try:
            dni = DNI(ben_dto.dni)
        except ValueError:
            dni = DNI("00000000")

        if not existing_beneficiary:
            beneficiary = Beneficiary(
                id=uuid.uuid4(),
                dni=dni,
                first_name=ben_dto.first_name,
                last_name=ben_dto.last_name,
                birth_date=birth_date,
                gender=gender,
                address=ben_dto.address
            )
        else:
            beneficiary = existing_beneficiary
            beneficiary.first_name = ben_dto.first_name
            beneficiary.last_name = ben_dto.last_name
            if birth_date:
                beneficiary.birth_date = birth_date
            beneficiary.gender = gender
            beneficiary.address = ben_dto.address

        rel_dto = dto.religion
        beneficiary.religion_record = ReligionRecord(
            baptized=rel_dto.baptized,
            first_communion=rel_dto.first_communion
        )

        perm_dto = dto.permissions
        beneficiary.permissions_record = PermissionsRecord(
            haircut_permission=perm_dto.haircut_permission,
            medical_exams_permission=perm_dto.medical_exams_permission
        )

        # Map Medical Record
        med_dto = dto.medical
        if not beneficiary.medical_record:
            beneficiary.medical_record = MedicalRecord(
                id=uuid.uuid4(),
                beneficiary_id=beneficiary.id,
                has_been_hospitalized=False,
                hospitalization_reason=None,
                has_been_operated=False,
                operation_reason=None,
                vaccines=[],
                medications=[],
                allergies=[],
                diseases=[],
                insurance=[]
            )
            
        m = beneficiary.medical_record
        m.has_been_hospitalized = med_dto.has_been_hospitalized
        m.hospitalization_reason = med_dto.hospitalization_reason
        m.has_been_operated = med_dto.has_been_operated
        m.operation_reason = med_dto.operation_reason
        m.vaccines = med_dto.vaccines
        m.medications = med_dto.medications
        m.allergies = med_dto.allergies
        m.diseases = med_dto.diseases
        m.insurance = med_dto.insurance

        # Map Education Record
        edu_dto = dto.education
        if not beneficiary.education_record:
            beneficiary.education_record = EducationRecord(
                id=uuid.uuid4(),
                beneficiary_id=beneficiary.id,
                school=None,
                grade=None,
                knows_how_to_read=False,
                knows_how_to_write=False,
                has_repeated_grade=False,
                has_learning_difficulties=False
            )
            
        e = beneficiary.education_record
        e.school = edu_dto.school
        
        try:
            e.grade = Grade(edu_dto.grade) if edu_dto.grade else None
        except ValueError:
            e.grade = None
            
        e.knows_how_to_read = edu_dto.knows_how_to_read
        e.knows_how_to_write = edu_dto.knows_how_to_write
        e.has_repeated_grade = edu_dto.has_repeated_grade
        e.has_learning_difficulties = edu_dto.has_learning_difficulties

        # Map Relatives (Adults)
        # We replace the current relatives with what comes in the DTO for this specific update
        beneficiary.relatives = []
        
        for ad_dto in dto.related_adults.adults:
            parts = ad_dto.full_name.split(" ", 1)
            ad_first_name = parts[0] if parts else ""
            ad_last_name = parts[1] if len(parts) > 1 else ""
            
            try:
                role_enum = RelationshipRole(ad_dto.role.upper())
            except ValueError:
                role_enum = RelationshipRole.OTHER
                
            try:
                ad_dni = DNI(ad_dto.dni)
            except ValueError:
                ad_dni = DNI("00000000")
                
            ad_phone = None
            if ad_dto.phone:
                try:
                    ad_phone = Phone(ad_dto.phone)
                except ValueError:
                    pass

            is_emergency = False
            if dto.related_adults.emergency_contact_dni and ad_dto.dni == dto.related_adults.emergency_contact_dni:
                is_emergency = True

            beneficiary.relatives.append(Adult(
                id=uuid.uuid4(),
                dni=ad_dni,
                first_name=ad_first_name,
                last_name=ad_last_name,
                birth_date=None,  # We usually don't get the adult's birth date in Educa
                gender=None,
                beneficiary_id=beneficiary.id,
                role=role_enum,
                phone=ad_phone,
                is_emergency_contact=is_emergency
            ))

        return beneficiary
