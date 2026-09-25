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
            # ALTA: el beneficiario aún no existe en el MDM. Se crea completo con
            # los datos del expediente aprobado (identidad + familiares + registros).
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
            # CASO DE USO — ACTUALIZACIÓN PARCIAL (nueva actividad, mismo DNI):
            # el beneficiario YA existe registrado en el MDM. Su identidad
            # (nombres, fecha de nacimiento, sexo, dirección) y sus familiares
            # NO se tocan: son gestionados por el maestro (PATCH /beneficiaries
            # desde la pantalla MDM). De este expediente solo se actualizan los
            # datos operativos de abajo (religión, permisos, ficha médica y
            # educación) y la nueva matrícula se añade en
            # EducaDossierProcessor.process (una por actividad).
            beneficiary = existing_beneficiary

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
        if not existing_beneficiary:
            # ALTA: los familiares se reconstruyen desde el expediente (dedup por DNI).
            beneficiary.relatives = []
            seen_dnis = set()

            for ad_dto in dto.related_adults.adults:
                ad_dni_raw = (ad_dto.dni or "").strip()
                if not ad_dni_raw or not (ad_dni_raw.isdigit() and len(ad_dni_raw) == 8):
                    continue
                if ad_dni_raw in seen_dnis:
                    continue
                seen_dnis.add(ad_dni_raw)
                adult = _build_adult(ad_dto, dto, ad_dni_raw)
                if adult:
                    beneficiary.relatives.append(adult)
        else:
            # CASO DE USO — tutor adicional sobre un beneficiario YA registrado:
            # los familiares del maestro se PRESERVAN (la pantalla MDM los gestiona,
            # PATCH /beneficiaries). De este expediente solo se AÑADEN tutores nuevos
            # (rol distinto de padre/madre) que NO sean la misma persona de un
            # familiar existente — mismo DNI o nombre muy similar — para no
            # duplicar al papá/mamá/apoderado ya registrado en el MDM.
            _append_new_tutors(beneficiary, dto)
            # El apoderado y el contacto de emergencia SÍ se pueden cambiar aunque
            # el beneficiario ya esté en el MDM: los flags operativos se
            # sincronizan con guardian_dni/emergency_contact_dni del expediente
            # (exista o se agregue el adulto). La identidad y el rol (padre/madre)
            # NO se tocan, solo estos dos flags.
            _sync_guardian_emergency_flags(beneficiary, dto)

        return beneficiary


def _build_adult(ad_dto, dto, ad_dni_raw: str):
    """Construye un Adult a partir de un EducaAdultDTO (lógica compartida entre
    la alta y el append de tutores). Devuelve None si el adulto no es válido."""
    parts = ad_dto.full_name.split(" ", 1)
    ad_first_name = parts[0] if parts else ""
    ad_last_name = parts[1] if len(parts) > 1 else ""

    raw_rel = (ad_dto.relationship or "").upper()
    if raw_rel == "APODERADO":
        role_enum = RelationshipRole.TUTOR
    else:
        try:
            role_enum = RelationshipRole(raw_rel)
        except ValueError:
            role_enum = RelationshipRole.OTHER

    try:
        ad_dni = DNI(ad_dni_raw)
    except ValueError:
        return None

    ad_phone = None
    if ad_dto.phone:
        try:
            ad_phone = Phone(ad_dto.phone)
        except ValueError:
            pass

    is_emergency = False
    if dto.related_adults.emergency_contact_dni and ad_dto.dni == dto.related_adults.emergency_contact_dni:
        is_emergency = True

    is_guardian = False
    if getattr(dto.related_adults, 'guardian_dni', None) and ad_dto.dni == dto.related_adults.guardian_dni:
        is_guardian = True

    return Adult(
        id=uuid.uuid4(),
        dni=ad_dni,
        first_name=ad_first_name,
        last_name=ad_last_name,
        birth_date=None,  # We usually don't get the adult's birth date in Educa
        gender=None,
        role=role_enum,
        phone=ad_phone,
        is_emergency_contact=is_emergency,
        is_guardian=is_guardian
    )


def _append_new_tutors(beneficiary, dto) -> None:
    """Añade al beneficiario EXISTENTE los tutores nuevos del expediente.

    Reglas anti-duplicado (el maestro no debe contaminarse):
      1. Nunca se toca a padre/madre (FATHER/MOTHER): son del maestro.
      2. Sin DNI válido de 8 dígitos → se ignora (igual que en la alta).
      3. DNI ya presente entre los familiares → misma persona, no se agrega.
      4. Nombre (normalizado) muy similar al de un familiar existente → se
         considera la misma persona (p. ej. el papá con DNI mal escaneado) y no
         se agrega como nuevo.
    """
    existing_dnis = {r.dni.value for r in beneficiary.relatives if r.dni}
    existing_full_names = [
        f"{r.first_name} {r.last_name}".strip() for r in beneficiary.relatives
    ]

    for ad_dto in dto.related_adults.adults:
        raw_rel = (ad_dto.relationship or "").upper()
        if raw_rel in ("FATHER", "MOTHER"):
            continue

        ad_dni_raw = (ad_dto.dni or "").strip()
        if not ad_dni_raw or not (ad_dni_raw.isdigit() and len(ad_dni_raw) == 8):
            continue
        if ad_dni_raw in existing_dnis:
            continue

        full_name = (ad_dto.full_name or "").strip()
        if _names_look_same(full_name, existing_full_names):
            continue

        adult = _build_adult(ad_dto, dto, ad_dni_raw)
        if adult:
            beneficiary.relatives.append(adult)


def _normalize_name(value: str) -> str:
    import unicodedata
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _names_look_same(name: str, existing_names: list) -> bool:
    """¿El nombre coincide (fuzzy) con algún familiar existente?

    Tres heurísticas, cualquiera dispara:
      1. Igualdad exacta tras normalizar (acentos/mayúsculas/espacios).
      2. Ratio de `difflib.SequenceMatcher` >= 0.90 (pequeñas variaciones OCR).
      3. Un conjunto de tokens contiene al otro con >= 2 tokens en común
         (nombres reordenados o con un nombre/sufijo extra).
    """
    import difflib

    norm = _normalize_name(name)
    if not norm:
        return False
    norm_tokens = set(norm.split())

    for existing in existing_names:
        ex = _normalize_name(existing)
        if not ex:
            continue
        if norm == ex:
            return True
        if difflib.SequenceMatcher(None, norm, ex).ratio() >= 0.90:
            return True
        ex_tokens = set(ex.split())
        if norm_tokens and ex_tokens and len(norm_tokens & ex_tokens) >= 2:
            if norm_tokens <= ex_tokens or ex_tokens <= norm_tokens:
                return True

    return False


def _sync_guardian_emergency_flags(beneficiary, dto) -> None:
    """Sincroniza los flags operativos `is_guardian` / `is_emergency_contact` de
    los familiares EXISTENTES del beneficiario con el expediente corregido.

    Antes este caso (beneficiario YA en el MDM) congelaba esos flags con los
    valores del maestro: cambiar el apoderado o el contacto de emergencia en la
    corrección no tenía efecto. Ahora, para cada adulto (existente o recién
    agregado), el flag refleja SIEMPRE al adulto al que apuntan
    `guardian_dni` / `emergency_contact_dni` del DTO:
      - El adulto cuyo DNI coincide → flag `True`; el resto → `False`.
      - DNI no consignado (None/vacío) → los flags se limpian (no hay apoderado
        ni contacto de emergencia designado en esta actividad).
    La identidad, el rol (padre/madre) y la deduplicación por DNI/nombre se
    mantienen intactos: esta función solo toca estos dos flags.
    """
    related = dto.related_adults
    guardian_dni = (getattr(related, "guardian_dni", None) or "").strip()
    emergency_dni = (getattr(related, "emergency_contact_dni", None) or "").strip()

    for adult in beneficiary.relatives:
        if not adult.dni:
            continue
        ad_dni = str(adult.dni.value).strip().upper()
        adult.is_guardian = bool(guardian_dni) and ad_dni == guardian_dni.upper()
        adult.is_emergency_contact = bool(emergency_dni) and ad_dni == emergency_dni.upper()