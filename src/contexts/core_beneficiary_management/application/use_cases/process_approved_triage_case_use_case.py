from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.beneficiary_models import (
    BeneficiaryModel, MedicalRecordModel, EducationRecordModel, RelativeModel, EnrollmentModel
)
from datetime import datetime
import uuid

class ProcessApprovedTriageCaseUseCase:
    def __init__(self, beneficiary_repo: SqlBeneficiaryRepository):
        self.beneficiary_repo = beneficiary_repo

    async def execute(self, event: DossierApprovedEvent):
        data = event.dossier_data
        ben_data = data.get("beneficiary", {})
        dni = ben_data.get("dni")
        if not dni:
            return  # No DNI, cannot process
            
        beneficiary = await self.beneficiary_repo.get_by_dni(dni)
        
        # Parse basic info
        first_name = ben_data.get("first_name", "")
        last_name = ben_data.get("last_name", "")
        birth_date_str = ben_data.get("birth_date")
        birth_date = datetime.strptime(birth_date_str.split("T")[0], "%Y-%m-%d").date() if birth_date_str else None
        gender = ben_data.get("gender", "UNKNOWN")

        if not beneficiary:
            beneficiary = BeneficiaryModel(
                id=uuid.uuid4(),
                dni=dni,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=gender
            )
        else:
            beneficiary.first_name = first_name
            beneficiary.last_name = last_name
            if birth_date:
                beneficiary.birth_date = birth_date
            beneficiary.gender = gender

        # Update Medical
        med_data = data.get("medical", {})
        if not beneficiary.medical_record:
            beneficiary.medical_record = MedicalRecordModel(id=uuid.uuid4())
            
        m = beneficiary.medical_record
        m.has_been_hospitalized = med_data.get("has_been_hospitalized", False)
        m.hospitalization_reason = med_data.get("hospitalization_reason")
        m.has_been_operated = med_data.get("has_been_operated", False)
        m.operation_reason = med_data.get("operation_reason")
        m.vaccines = med_data.get("vaccines", [])
        m.medications = med_data.get("medications", [])
        m.allergies = med_data.get("allergies", [])
        m.diseases = med_data.get("diseases", [])
        m.insurance = med_data.get("insurance", [])

        # Update Education
        edu_data = data.get("education", {})
        if not beneficiary.education_record:
            beneficiary.education_record = EducationRecordModel(id=uuid.uuid4())
            
        e = beneficiary.education_record
        e.school = edu_data.get("school")
        e.grade = edu_data.get("grade")
        e.knows_how_to_read = edu_data.get("knows_how_to_read", False)
        e.knows_how_to_write = edu_data.get("knows_how_to_write", False)
        e.has_repeated_grade = edu_data.get("has_repeated_grade", False)
        e.has_learning_difficulties = edu_data.get("has_learning_difficulties", False)

        # Update Relatives
        fam_data = data.get("related_adults", {})
        adults = fam_data.get("adults", [])
        
        # Simple replace for relatives
        if beneficiary.relatives:
            for r in list(beneficiary.relatives):
                beneficiary.relatives.remove(r)
                
        for ad in adults:
            beneficiary.relatives.append(RelativeModel(
                id=uuid.uuid4(),
                dni=ad.get("dni"),
                full_name=ad.get("full_name"),
                role=ad.get("role"),
                phone=ad.get("phone")
            ))

        # Add Enrollment if not exists for this activity
        has_enrollment = any(e.activity_code == event.activity_type for e in beneficiary.enrollments)
        if not has_enrollment and event.activity_type:
            beneficiary.enrollments.append(EnrollmentModel(
                id=uuid.uuid4(),
                activity_code=event.activity_type,
                enrollment_date=datetime.utcnow().date()
            ))

        await self.beneficiary_repo.save(beneficiary)
