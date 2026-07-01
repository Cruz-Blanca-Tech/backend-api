from typing import Optional
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.beneficiary_model import BeneficiaryModel

from .medical_record_mapper import MedicalRecordMapper
from .education_record_mapper import EducationRecordMapper
from .adult_mapper import AdultMapper
from .historical_document_mapper import HistoricalDocumentMapper
from .enrollment_mapper import EnrollmentMapper

from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender
from src.contexts.core_beneficiary_management.domain.value_objects.religion_record import ReligionRecord
from src.contexts.core_beneficiary_management.domain.value_objects.permissions_record import PermissionsRecord

class BeneficiaryMapper:
    @staticmethod
    def to_domain(model: Optional[BeneficiaryModel]) -> Optional[Beneficiary]:
        if not model:
            return None

        relatives = []
        if model.relatives:
            for r in model.relatives:
                adult = AdultMapper.to_domain(r)
                if adult:
                    relatives.append(adult)

        historical_documents = []
        if model.historical_documents:
            for doc in model.historical_documents:
                h_doc = HistoricalDocumentMapper.to_domain(doc)
                if h_doc:
                    historical_documents.append(h_doc)
            
        enrollments = []
        if model.enrollments:
            for e in model.enrollments:
                enr = EnrollmentMapper.to_domain(e)
                if enr:
                    enrollments.append(enr)

        gender = None
        if model.gender:
            try:
                gender = Gender(model.gender)
            except ValueError:
                pass
                
        try:
            dni = DNI(model.dni)
        except ValueError:
            dni = DNI("00000000") # fallback

        return Beneficiary(
            id=model.id,
            dni=dni,
            first_name=model.first_name,
            last_name=model.last_name,
            birth_date=model.birth_date,
            gender=gender,
            address=model.address,
            religion_record=ReligionRecord(
                baptized=model.baptized,
                first_communion=model.first_communion
            ),
            permissions_record=PermissionsRecord(
                haircut_permission=model.haircut_permission,
                medical_exams_permission=model.medical_exams_permission
            ),
            medical_record=MedicalRecordMapper.to_domain(model.medical_record),
            education_record=EducationRecordMapper.to_domain(model.education_record),
            relatives=relatives,
            historical_documents=historical_documents,
            enrollments=enrollments
        )

    @staticmethod
    def to_persistence(entity: Optional[Beneficiary]) -> Optional[BeneficiaryModel]:
        if not entity:
            return None

        model = BeneficiaryModel(
            id=entity.id,
            dni=entity.dni.value if entity.dni else "",
            first_name=entity.first_name,
            last_name=entity.last_name,
            birth_date=entity.birth_date,
            gender=entity.gender.value if entity.gender else None,
            address=entity.address,
            baptized=entity.religion_record.baptized if entity.religion_record else None,
            first_communion=entity.religion_record.first_communion if entity.religion_record else None,
            haircut_permission=entity.permissions_record.haircut_permission if entity.permissions_record else None,
            medical_exams_permission=entity.permissions_record.medical_exams_permission if entity.permissions_record else None
        )

        model.medical_record = MedicalRecordMapper.to_persistence(entity.medical_record, entity.id)
        model.education_record = EducationRecordMapper.to_persistence(entity.education_record, entity.id)

        model.relatives = []
        for r in entity.relatives:
            ad_model = AdultMapper.to_persistence(r, entity.id)
            if ad_model:
                model.relatives.append(ad_model)

        model.historical_documents = []
        for doc in entity.historical_documents:
            doc_model = HistoricalDocumentMapper.to_persistence(doc, entity.id)
            if doc_model:
                model.historical_documents.append(doc_model)
            
        model.enrollments = []
        for e in entity.enrollments:
            enr_model = EnrollmentMapper.to_persistence(e, entity.id)
            if enr_model:
                model.enrollments.append(enr_model)

        return model
