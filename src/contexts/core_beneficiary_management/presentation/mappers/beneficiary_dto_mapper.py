import uuid
from datetime import date
from typing import Optional
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.domain.value_objects.religion_record import ReligionRecord
from src.contexts.core_beneficiary_management.domain.value_objects.permissions_record import PermissionsRecord
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import (
    BeneficiaryResponse, BeneficiaryPatchRequest, BeneficiarySummaryResponse, BeneficiaryCreateRequest,
    MdmBeneficiarySnapshot, MdmRelativeSnapshot
)

from .medical_dto_mapper import MedicalDtoMapper
from .education_dto_mapper import EducationDtoMapper
from .adult_dto_mapper import AdultDtoMapper
from .historical_document_dto_mapper import HistoricalDocumentDtoMapper

def calculate_age(birth_date: Optional[date]) -> Optional[int]:
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

class BeneficiaryDtoMapper:
    @staticmethod
    def to_response(domain_entity: Optional[Beneficiary], active_activity_ids: Optional[set] = None) -> Optional[BeneficiaryResponse]:
        if not domain_entity:
            return None
            
        return BeneficiaryResponse(
            id=domain_entity.id,
            dni=domain_entity.dni.value if domain_entity.dni else "",
            first_name=domain_entity.first_name,
            last_name=domain_entity.last_name,
            birth_date=domain_entity.birth_date,
            gender=domain_entity.gender.value if domain_entity.gender else None,
            address=domain_entity.address,
            baptized=domain_entity.religion_record.baptized if domain_entity.religion_record else None,
            first_communion=domain_entity.religion_record.first_communion if domain_entity.religion_record else None,
            haircut_permission=domain_entity.permissions_record.haircut_permission if domain_entity.permissions_record else None,
            medical_exams_permission=domain_entity.permissions_record.medical_exams_permission if domain_entity.permissions_record else None,
            is_active=any(e.activity_code in (active_activity_ids or set()) for e in domain_entity.enrollments) if active_activity_ids is not None else True,
            medical=MedicalDtoMapper.to_response(domain_entity.medical_record),
            education=EducationDtoMapper.to_response(domain_entity.education_record),
            related_adults=[AdultDtoMapper.to_response(adult) for adult in domain_entity.relatives],
            historical_documents=HistoricalDocumentDtoMapper.to_response_list(domain_entity.historical_documents)
        )

    @staticmethod
    def to_mdm_snapshot(domain_entity: Optional[Beneficiary]) -> Optional[MdmBeneficiarySnapshot]:
        """Snapshot de identidad + familiares para el triaje (maestro = la verdad).

        Es deliberadamente LIGERO (sin registros médico/educativo): la pantalla de
        corrección solo necesita identidad y familiares para bloquear/rellenar los
        campos protegidos cuando el expediente coincide con un beneficiario ya
        registrado en el dato máster.
        """
        if not domain_entity:
            return None
        return MdmBeneficiarySnapshot(
            dni=domain_entity.dni.value if domain_entity.dni else "",
            first_name=domain_entity.first_name,
            last_name=domain_entity.last_name,
            birth_date=domain_entity.birth_date,
            gender=domain_entity.gender.value if domain_entity.gender else None,
            address=domain_entity.address,
            relatives=[
                MdmRelativeSnapshot(
                    relationship=adult.role.value if adult.role else "OTHER",
                    dni=adult.dni.value if adult.dni else "",
                    full_name=f"{adult.first_name} {adult.last_name}".strip(),
                    phone=adult.phone.value if adult.phone else None,
                    is_emergency_contact=adult.is_emergency_contact,
                    is_guardian=adult.is_guardian,
                )
                for adult in domain_entity.relatives
            ],
        )

    @staticmethod
    def to_summary_response(domain_entity: Optional[Beneficiary], active_activity_ids: Optional[set] = None) -> Optional[BeneficiarySummaryResponse]:
        if not domain_entity:
            return None
            
        grade_str = None
        if domain_entity.education_record and domain_entity.education_record.grade:
            grade_str = domain_entity.education_record.grade.value

        return BeneficiarySummaryResponse(
            id=domain_entity.id,
            dni=domain_entity.dni.value if domain_entity.dni else "",
            first_name=domain_entity.first_name,
            last_name=domain_entity.last_name,
            birth_date=domain_entity.birth_date,
            age=calculate_age(domain_entity.birth_date),
            gender=domain_entity.gender.value if domain_entity.gender else None,
            is_active=any(e.activity_code in (active_activity_ids or set()) for e in domain_entity.enrollments) if active_activity_ids is not None else True,
            grade=grade_str
        )

    @staticmethod
    def patch_domain(domain_entity: Beneficiary, patch_request: BeneficiaryPatchRequest) -> Beneficiary:
        update_data = patch_request.dict(exclude_unset=True, exclude={"medical", "education", "related_adults"})
        
        for field, value in update_data.items():
            if field == "gender" and value is not None:
                setattr(domain_entity, field, Gender(value))
            else:
                setattr(domain_entity, field, value)
                
        # Handle sub-entities
        if patch_request.medical is not None:
            domain_entity.medical_record = MedicalDtoMapper.patch_domain(
                domain_entity.medical_record, patch_request.medical, domain_entity.id
            )
            
        if patch_request.education is not None:
            domain_entity.education_record = EducationDtoMapper.patch_domain(
                domain_entity.education_record, patch_request.education, domain_entity.id
            )
            
        if patch_request.related_adults is not None:
            domain_entity.relatives = AdultDtoMapper.patch_domain_list(
                domain_entity.relatives, patch_request.related_adults
            )
            
        return domain_entity

    @staticmethod
    def from_create_request(request: BeneficiaryCreateRequest, explicit_id: Optional[uuid.UUID] = None) -> Beneficiary:
        beneficiary_id = explicit_id or request.id or uuid.uuid4()
        
        try:
            dni = DNI(request.dni)
        except ValueError as e:
            raise ValueError(f"DNI inválido: {str(e)}")

        gender = None
        if request.gender:
            try:
                g_str = request.gender.upper()
                if g_str == "F":
                    g_str = "FEMALE"
                elif g_str == "M":
                    g_str = "MALE"
                gender = Gender(g_str)
            except ValueError:
                gender = Gender.UNKNOWN

        relatives = AdultDtoMapper.from_create_request_list(beneficiary_id, request.related_adults)
        medical_record = MedicalDtoMapper.from_create_request(request.medical, beneficiary_id)
        education_record = EducationDtoMapper.from_create_request(request.education, beneficiary_id)

        religion_record = ReligionRecord(
            baptized=request.baptized,
            first_communion=request.first_communion
        ) if (request.baptized is not None or request.first_communion is not None) else None

        permissions_record = PermissionsRecord(
            haircut_permission=request.haircut_permission,
            medical_exams_permission=request.medical_exams_permission
        ) if (request.haircut_permission is not None or request.medical_exams_permission is not None) else None

        return Beneficiary(
            id=beneficiary_id,
            dni=dni,
            first_name=request.first_name,
            last_name=request.last_name,
            birth_date=request.birth_date,
            gender=gender,
            address=request.address,
            religion_record=religion_record,
            permissions_record=permissions_record,
            medical_record=medical_record,
            education_record=education_record,
            relatives=relatives,
            historical_documents=[],
            enrollments=[]
        )

