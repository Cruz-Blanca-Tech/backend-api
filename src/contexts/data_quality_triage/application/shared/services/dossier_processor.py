import logging
import re
import unicodedata
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.strategies.triage_strategy_factory import TriageStrategyFactory
from src.contexts.data_quality_triage.domain.shared.repositories.document_read_repository import DocumentReadRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import _is_valid_phone
from src.contexts.data_quality_triage.application.shared.services.beneficiary_fuzzy_matcher import score_candidate
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import EntityNotFoundException, DomainValidationError

logger = logging.getLogger(__name__)
SYSTEM_UUID = UUID("00000000-0000-0000-0000-000000000000")

# Umbral de ambigüedad para sugerencias de adultos: si el mejor candidato no
# supera por este margen al segundo (o hay demasiados candidatos) la
# coincidencia NO es confiable para sugerir un vínculo a ciegas y se eleva a
# WARNING ("verifique si este adulto ya existe").
_AMBIGUITY_GAP = 0.10


def _adult_match_is_ambiguous(suggestions) -> bool:
    """¿La coincidencia fuzzy de un adulto es ambigua?

    Una sugerencia de vínculo ("Quizá este adulto es → …") solo es segura cuando
    hay UN candidato claramente dominante. Si no se puede decidir con confianza,
    el procesador eleva el hallazgo a WARNING para que el revisor verifique:

      - 3+ candidatos (el top-3 del matcher completo) → demasiadas coincidencias.
      - 2 candidatos con score casi empatado (gap < _AMBIGUITY_GAP) → no hay un
        ganador claro.
    """
    if len(suggestions) >= 3:
        return True
    return (
        len(suggestions) >= 2
        and (suggestions[0].score - suggestions[1].score) < _AMBIGUITY_GAP
    )


# DNI peruano: 8 dígitos.
_DNI_RE = re.compile(r"^\d{8}$")


def _normalize_name(value) -> str:
    """Nombre sin acentos, en mayúsculas y con espacios colapsados.

    Sirve para indexar adultos entre fichas del mismo lote: resiste tildes y
    espaciado irregular del OCR ("Rosa Luz Mamani Cóndor" → "ROSA LUZ MAMANI CONDOR").
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip().upper()


def _dni_valid(value) -> bool:
    return bool(value and _DNI_RE.match(str(value).strip()))


# Puntaje mínimo de nombre para que el maestro corrobore el DNI de agrupación del
# lote como la identidad del expediente (mismo umbral que el matcher de sugerencias).
_GROUP_DNI_SCORE = 0.50

# Consulta del maestro para un adulto de la ficha. OJO con el join: `adults` es
# single-table inheritance (AdultModel<PersonModel>), o sea que `adults.id` ES
# `persons.id`. No existe una columna `person_id`: con ese join la query explotaba
# en TODA ficha con un adulto que tuviera DNI y el `except` del bloque se comía la
# excepción (sin touchless, sin sugerencias, sin N1, sin hermanos). El test
# `test_sql_de_adulto_une_por_la_pk_compartida` lo fija.
_ADULT_MASTER_SQL = """
    SELECT p.dni, p.first_name, p.last_name, a.phone
    FROM persons p
    LEFT JOIN adults a ON a.id = p.id
    WHERE p.type = 'adult' AND p.dni = :dni
"""


def _build_group_dni_suggestion(group_dni, dossier_dni, b_first, b_last, master_person):
    """Sugerencia del DNI DE AGRUPACIÓN del lote cuando el maestro lo corrobora.

    El intake agrupa los documentos de este expediente bajo `group_dni` (la clave de
    agrupación del lote). Si el maestro registra a una persona con ESE dni cuyo
    nombre coincide con el del expediente, la agrupación es la evidencia más fuerte
    de que el DNI del campo es una lectura OCR equivocada → se sugiere usar el DNI
    de agrupación (AI_INSIGHT no-bloqueante: lo resuelve el botón "Vincular" de la
    tarjeta del beneficiario, sin suggestions duplicadas del fuzzy).

    Si el maestro no conoce ese DNI, o la persona registrada con él tiene otro
    nombre, NO se sugiere: es justo el caso ambiguo que el revisor debe verificar a
    mano (el aviso inline "verifica la agrupación del lote").
    """
    if not _dni_valid(group_dni) or str(group_dni) == str(dossier_dni or ""):
        return None
    if not master_person:
        return None
    m_first = str(master_person[0] or "")
    m_last = str(master_person[1] or "")
    score = score_candidate(
        b_first, b_last, dossier_dni or None, m_first, m_last, str(group_dni)
    )
    if score < _GROUP_DNI_SCORE:
        return None
    return FieldDiscrepancy(
        field_name="beneficiary.dni",
        expected_pattern=str(group_dni),
        actual_value=dossier_dni or "(vacío)",
        rule_description=(
            f"El lote agrupó este expediente con el DNI {group_dni} y el maestro registra "
            f"a {m_first} {m_last} con ese DNI (nombre coincide {score:.0%}). El expediente "
            f"registra {dossier_dni or 'el DNI vacío'}: verifica el documento y usa el DNI "
            f"de agrupación si corresponde."
        ),
        severity="AI_INSIGHT",
    )


def _build_emergency_phone_suggestion(adult_index, is_emergency, dossier_phone, master_row):
    """Sugerencia de teléfono para el CONTACTO DE EMERGENCIA con DNI matcheado.

    La regla de contactos emite un ERROR cuando el teléfono del contacto de
    emergencia es vacío/inválido. Si ese adulto coincide con el maestro (identidad
    confirmada por DNI) y el maestro SÍ tiene teléfono válido, se sugiere (AI_INSIGHT,
    no-bloqueante) aplicarlo para destrabar el caso en un clic. El ERROR de la regla
    sigue siendo la fuente de verdad del bloqueo.
    """
    if not is_emergency or _is_valid_phone(dossier_phone) or not _is_valid_phone(master_row.phone):
        return None
    return FieldDiscrepancy(
        field_name=f"related_adults.adults[{adult_index}].phone",
        expected_pattern=master_row.phone,
        actual_value=dossier_phone or "(vacío)",
        rule_description=(
            f"El contacto de emergencia coincide con el adulto del maestro "
            f"{master_row.first_name} {master_row.last_name} (DNI: {master_row.dni}). "
            f"El maestro tiene registrado el teléfono {master_row.phone}: aplicar para "
            f"resolver el ERROR de la regla de contactos."
        ),
        severity="AI_INSIGHT",
    )


def _build_sibling_suggestions(adult_index, ad_name, ad_dni, ad_phone, sibling_index):
    """Sugerencias cross-dossier (misma familia, mismo lote) para un adulto.

    El OCR puede perder el DNI de un apoderado SOLO en una de las copias del
    lote. Si el mismo adulto (mismo nombre normalizado) aparece con DNI legible
    en la ficha de un hermano/a:
      - 1 solo DNI válido → AI_INSIGHT para completar el DNI (y el teléfono si la
        ficha actual no trae teléfono válido y la del hermano sí).
      - Varios DNIs distintos entre hermanos → WARNING de verificación (coherente
        con N1: una coincidencia ambigua no se sugiere a ciegas).
    """
    if not ad_name:
        return []
    out = []
    matches = sibling_index.get(_normalize_name(ad_name)) or []
    valid_dnis = sorted({m["dni"] for m in matches if _dni_valid(m["dni"])})
    if len(valid_dnis) == 1:
        sib_dni = valid_dnis[0]
        sib = next(m for m in matches if m["dni"] == sib_dni)
        source = f"la ficha de {sib['child_name']} (DNI {sib['child_dni']})"
        if not sib["child_name"]:
            source = f"DNI {sib['child_dni']}"
        out.append(FieldDiscrepancy(
            field_name=f"related_adults.adults[{adult_index}].dni",
            expected_pattern=sib_dni,
            actual_value=ad_dni or "(vacío)",
            rule_description=(
                f"En {source} del mismo lote aparece el adulto '{ad_name}' con DNI "
                f"{sib_dni}: se sugiere completar este DNI (lectura OCR perdida en "
                f"esta ficha)."
            ),
            severity="AI_INSIGHT",
        ))
        if not _is_valid_phone(ad_phone) and _is_valid_phone(sib["phone"]):
            out.append(FieldDiscrepancy(
                field_name=f"related_adults.adults[{adult_index}].phone",
                expected_pattern=sib["phone"],
                actual_value=ad_phone or "(vacío)",
                rule_description=(
                    f"En {source} del mismo lote el adulto '{ad_name}' registra el "
                    f"teléfono {sib['phone']}: aplicar para completar el dato."
                ),
                severity="AI_INSIGHT",
            ))
    elif len(valid_dnis) > 1:
        labels = ", ".join(f"DNI {d}" for d in valid_dnis)
        out.append(FieldDiscrepancy(
            field_name="related_adults.adults",
            expected_pattern=None,
            actual_value=ad_dni or "(vacío)",
            rule_description=(
                f"El adulto '{ad_name}' aparece con DNIs distintos en otras fichas "
                f"del mismo lote ({labels}). Verifique cuál corresponde antes de aprobar."
            ),
            severity="WARNING",
        ))
    return out


class ProcessDossierUseCase:
    def __init__(
        self, 
        triage_repo: SqlTriageRepository, 
        doc_repo: DocumentReadRepository,
        strategy_factory: TriageStrategyFactory,
        session: AsyncSession,
        llm_client: Optional[AsyncAzureOpenAI] = None
    ):
        self.triage_repo = triage_repo
        self.doc_repo = doc_repo
        self.strategy_factory = strategy_factory
        self.session = session
        self.llm_client = llm_client

    async def _load_sibling_adults(self, batch_id, exclude_dni: str) -> dict:
        """Índice de adultos vistos en OTRAS fichas del mismo lote (cross-dossier).

        Devuelve {nombre_normalizado: [{"dni", "phone", "child_dni", "child_name"}]}
        a partir de los triage_cases YA guardados del lote, excluyendo la ficha
        actual. Permite completar el DNI/teléfono de un apoderado que el OCR
        perdió solo en la ficha actual, tomándolo de la ficha de un hermano/a.
        """
        index = {}
        try:
            cases = await self.triage_repo.get_all_by_batch_id(batch_id)
        except Exception as e:
            logger.warning(f"No se pudieron cargar los casos del lote {batch_id}: {e}")
            return index
        for sibling in cases:
            if (sibling.dni_reference or "") == exclude_dni:
                continue
            dd = sibling.dossier_data or {}
            if not isinstance(dd, dict):
                continue
            ben = dd.get("beneficiary") or {}
            child_dni = ben.get("dni") or sibling.dni_reference
            child_name = " ".join(
                part for part in (ben.get("first_name"), ben.get("last_name")) if part
            ).strip()
            adults = (dd.get("related_adults") or {}).get("adults") or []
            for ad in adults:
                ad_name = str(ad.get("full_name") or "").strip()
                if not ad_name:
                    continue
                key = _normalize_name(ad_name)
                index.setdefault(key, []).append({
                    "dni": str(ad.get("dni") or "").strip(),
                    "phone": str(ad.get("phone") or "").strip(),
                    "child_dni": child_dni,
                    "child_name": child_name,
                })
        return index

    async def execute(self, dni: str, batch_id: UUID, activity_type_str: str) -> TriageCase:
        # 1. Recuperar los documentos enriquecidos
        docs = await self.doc_repo.get_by_dni(dni, batch_id)
        if not docs:
            logger.warning(f"No se encontraron documentos para el DNI {dni} en el lote {batch_id}")
            raise Exception("No documents found")

        # 2. La Factory decide la estrategia basandose en el contexto
        strategy = self.strategy_factory.get_strategy(
            document_codes={doc.document_code for doc in docs if doc.document_code}, 
            activity_type_str=activity_type_str
        )
        
        from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
        activity_type = ActivityType(activity_type_str)
        
        context = {}
        if activity_type == ActivityType.EDUCA_INSCRIPTION:
            try:
                res = await self.session.execute(text("SELECT name, is_active FROM schools WHERE is_active = true"))
                schools = [{"name": row[0], "is_active": row[1]} for row in res.fetchall()]
                context["schools"] = schools
            except Exception as e:
                logger.error(f"Error fetching schools: {e}")

        # Umbrales mínimos de confianza OCR por tipo de documento (calibración).
        # Se leen de activity_requirements de la actividad del lote: cada documento
        # requerido por la actividad tiene su propio confidence_threshold. Si la
        # actividad no tiene requisitos/umbral, la estrategia aplica el default 0.80.
        try:
            res_thr = await self.session.execute(
                text("""
                    SELECT dtc.code, ar.confidence_threshold
                    FROM extraction_batches eb
                    JOIN activity_requirements ar ON ar.activity_id = eb.activity_id
                    JOIN document_type_configs dtc ON dtc.id = ar.document_type_config_id
                    WHERE eb.id = :bid
                """),
                {"bid": str(batch_id)}
            )
            thresholds = {
                row[0]: float(row[1])
                for row in res_thr.fetchall()
                if row[0] and row[1] is not None
            }
            if thresholds:
                context["confidence_thresholds"] = thresholds
        except Exception as e:
            logger.error(f"Error fetching confidence thresholds: {e}")

        # Pasar cliente LLM al contexto para LLMNameReconciler
        context["llm_client"] = self.llm_client

        # 3. Ejecutar la validacion cruzada y construir el caso
        existing_case = await self.triage_repo.get_by_dossier(batch_id, dni)
        case = await strategy.execute(
            batch_id=batch_id, 
            activity_type=activity_type, 
            dni_reference=dni, 
            documents=docs,
            context=context
        )
        if existing_case:
            case.id = existing_case.id
            case.created_at = existing_case.created_at
            # El "primer JSON" es la foto del backend (post-LLM) que nunca debe
            # sobrescribirse: si el caso ya tenía snapshot (creado tras el
            # rollout), se preserva aunque el expediente se reprocese; si el caso
            # es previo al rollout (sin snapshot), se toma el dossier_data actual.
            if existing_case.original_dossier_data is not None:
                case.original_dossier_data = existing_case.original_dossier_data

        # --- DUPLICATE / FUZZY MATCH CHECK ---
        # La sugerencia fuzzy SOLO dispara cuando el posible duplicado DIFIERE del
        # expediente en DNI y/o nombre. Si el candidato coincide en ambos (mismo
        # DNI Y mismo nombre), no es una sugerencia: es el match MDM de identidad
        # (exact_match), que la UI ya resuelve rellenando/bloqueando los campos
        # protegidos. Regla de negocio acordada:
        #   - DNI idéntico + nombre distinto   → NO (es match MDM por DNI).
        #   - DNI idéntico + nombre idéntico   → NO (misma persona, match MDM).
        #   - DNI distinto + nombre idéntico   → SÍ (OCR leyó mal el DNI) — caso
        #     ANDRE: el lote se agrupó con un DNI mal leído, el maestro confirma.
        #   - DNI distinto + nombre distinto   → SÍ (homónimo/apellidos cercanos,
        #     posible DNI mal leído).
        b_data = case.dossier_data.get("beneficiary", {})
        b_dni = b_data.get("dni", dni)
        b_first = b_data.get("first_name", "") or ""
        b_last = b_data.get("last_name", "") or ""
        
        try:
            # Check exact match (beneficiario YA registrado con ese DNI)
            res_exact = await self.session.execute(
                text("SELECT dni FROM persons WHERE dni = :dni"),
                {"dni": b_dni}
            )
            exact_match = res_exact.fetchone()

            # El DNI de AGRUPACIÓN del lote (la clave con la que el intake agrupó los
            # documentos de este expediente) es evidencia documental. Si el maestro
            # corrobora a esa persona con el mismo nombre, se sugiere ese DNI: el
            # botón "Vincular" de la tarjeta del beneficiario lo resuelve en un clic
            # (y destraba el aviso inline de agrupación + el ERROR de DNI vacío).
            group_suggestion = None
            if not exact_match and (b_first or b_last):
                res_group = await self.session.execute(
                    text("SELECT first_name, last_name FROM persons WHERE dni = :dni"),
                    {"dni": str(dni)},
                )
                group_suggestion = _build_group_dni_suggestion(
                    dni, b_dni, b_first, b_last, res_group.fetchone()
                )

            if group_suggestion:
                case.discrepancies.append(group_suggestion)
            elif not exact_match and (b_first or b_last):
                # Sugerencia fuzzy robusta: busca candidatos por nombre/apellido
                # normalizados (sin acentos), resiste intercambios OCR de
                # columnas, nombres incompletos y devuelve los más cercanos
                # ordenados por puntaje compuesto (nombre + apellidos + DNI).
                from src.contexts.data_quality_triage.application.shared.services.beneficiary_fuzzy_matcher import BeneficiaryFuzzyMatcher
                suggestions = await BeneficiaryFuzzyMatcher(self.session).find_suggestions(
                    first_name=b_first,
                    last_name=b_last,
                    dni=b_dni,
                    limit=3,
                )

                if suggestions:
                    primary = suggestions[0]
                    primary_label = f"{primary.first_name} {primary.last_name} · DNI {primary.dni}"
                    suggested_dni = primary.dni
                    extras = suggestions[1:]
                    if extras:
                        extra_labels = ", ".join(
                            f"{c.first_name} {c.last_name} (DNI: {c.dni})" for c in extras
                        )
                        description = (
                            f"Quizá este beneficiario es → {primary_label}. "
                            f"También podría ser: {extra_labels}. Valide si es la misma "
                            f"persona con un DNI o nombre mal escaneado."
                        )
                    else:
                        description = (
                            f"Quizá este beneficiario es → {primary_label}. "
                            f"Valide si es la misma persona con un DNI o nombre mal escaneado."
                        )

                    from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
                    case.discrepancies.append(FieldDiscrepancy(
                        field_name="beneficiary.dni",
                        expected_pattern=suggested_dni,
                        actual_value=b_dni,
                        rule_description=description,
                        severity="AI_INSIGHT"
                    ))
        except Exception as e:
            logger.error(f"Error in fuzzy matching: {e}", exc_info=True)

        # --- ADULT / APODERADO FUZZY SUGGESTIONS ---
        # Regla de touchless para adultos (padre/madre/apoderado) contra el
        # maestro type='adult':
        #   - DNI idéntico al de un adulto existente → match MDM: NO se emite NADA
        #     (ni warning ni sugerencia). La identidad la dicta el maestro.
        #   - DNI distinto + nombre/contexto similar → AI_INSIGHT no-bloqueante:
        #     "Quizá este adulto es → {nombre} · DNI {dni}".
        # Las únicas advertencias que pueden bloquear a un adulto ya registrado son
        # las reglas de dominio existentes (apellidos de padre/madre, teléfono del
        # contacto de emergencia).
        try:
            from src.contexts.data_quality_triage.application.shared.services.beneficiary_fuzzy_matcher import BeneficiaryFuzzyMatcher

            related_data = (case.dossier_data or {}).get("related_adults") or {}
            adults_data = related_data.get("adults") or []
            emergency_dni = str(related_data.get("emergency_contact_dni") or "").strip()
            matcher = BeneficiaryFuzzyMatcher(self.session)
            # Índice cross-dossier: adultos vistos en OTRAS fichas del mismo lote
            # (para completar DNI/teléfono de un apoderado desde la ficha de un hermano).
            sibling_index = await self._load_sibling_adults(batch_id, exclude_dni=str(dni))
            for idx, ad in enumerate(adults_data):
                ad_name = str(ad.get("full_name") or "").strip()
                ad_dni = str(ad.get("dni") or "").strip()
                ad_phone = str(ad.get("phone") or "").strip()
                if not ad_name:
                    continue

                # 1) Match MDM por DNI → touchless: nunca sugerir. Solo interesa
                #    el maestro de ADULTOS (un apoderado no se vincula a un
                #    beneficiario). Excepción productiva: contacto de emergencia
                #    con teléfono vacío/inválido → se SUGIERE el teléfono del
                #    maestro (AI_INSIGHT) para destrabar el ERROR de la regla de
                #    contactos en un clic.
                if ad_dni:
                    res_master = await self.session.execute(
                        text(_ADULT_MASTER_SQL),
                        {"dni": ad_dni},
                    )
                    master_row = res_master.fetchone()
                    if master_row:
                        phone_suggestion = _build_emergency_phone_suggestion(
                            idx, emergency_dni == ad_dni, ad_phone, master_row
                        )
                        if phone_suggestion:
                            case.discrepancies.append(phone_suggestion)
                        continue

                # 2) Sugerencia entre HERMANOS del mismo lote (cross-dossier):
                #    el OCR perdió el DNI de este apoderado solo en la ficha
                #    actual; la ficha de otro/a hermano/a del lote lo trae legible
                #    con el mismo nombre → completar DNI (y teléfono si aplica).
                #    Coherente con N1: si los hermanos traen DNIs distintos →
                #    WARNING de verificación (no se sugiere a ciegas).
                if not _dni_valid(ad_dni):
                    case.discrepancies.extend(
                        _build_sibling_suggestions(idx, ad_name, ad_dni, ad_phone, sibling_index)
                    )

                adult_suggestions = await matcher.find_adult_suggestions(
                    full_name=ad_name,
                    dni=ad_dni or None,
                    limit=3,
                )
                if not adult_suggestions:
                    continue

                # Decisión N1 (business): si la coincidencia es AMBIGUA — 3+
                # candidatos o dos con score casi empatado — no se sugiere un
                # vínculo a ciegas: se advierte para que el revisor verifique si
                # el adulto ya está registrado (WARNING, bloquea autovalidación).
                if _adult_match_is_ambiguous(adult_suggestions):
                    labels = ", ".join(
                        f"{c.first_name} {c.last_name} (DNI: {c.dni})" for c in adult_suggestions
                    )
                    case.discrepancies.append(FieldDiscrepancy(
                        field_name="related_adults.adults",
                        expected_pattern=None,
                        actual_value=ad_dni or "(vacío)",
                        rule_description=(
                            f"El nombre '{ad_name}' coincide con {len(adult_suggestions)} "
                            f"adultos ya registrados ({labels}). Verifique si este adulto "
                            f"ya existe y corrija el DNI si corresponde."
                        ),
                        severity="WARNING",
                    ))
                    continue

                primary = adult_suggestions[0]
                primary_label = f"{primary.first_name} {primary.last_name} · DNI {primary.dni}"
                extras = adult_suggestions[1:]
                if extras:
                    extra_labels = ", ".join(
                        f"{c.first_name} {c.last_name} (DNI: {c.dni})" for c in extras
                    )
                    description = (
                        f"Quizá este adulto es → {primary_label}. "
                        f"También podría ser: {extra_labels}. Valide si es la misma "
                        f"persona con un DNI o nombre mal escaneado."
                    )
                else:
                    description = (
                        f"Quizá este adulto es → {primary_label}. "
                        f"Valide si es la misma persona con un DNI o nombre mal escaneado."
                    )
                case.discrepancies.append(FieldDiscrepancy(
                    field_name=f"related_adults.adults[{idx}].dni",
                    expected_pattern=primary.dni,
                    actual_value=ad_dni or "(vacío)",
                    rule_description=description,
                    severity="AI_INSIGHT",
                ))
        except Exception as e:
            logger.error(f"Error in adult fuzzy matching: {e}", exc_info=True)

        # --- DUPLICATE REGISTRATION CHECK ---
        # Detecta dos situaciones para el MISMO DNI y la MISMA actividad:
        #   1) Ya matriculado (beneficiary_enrollments): caso aprobado persistido.
        #   2) Expediente en trámite (triage_cases no rechazado): pendiente de
        #      revisión/corrección o aprobado sin matrícula aún.
        # En ambos casos el caso se rechaza automáticamente: no se puede registrar
        # dos veces el mismo beneficiario en una actividad.
        try:
            res_batch = await self.session.execute(
                # FIX: la tabla real es `extraction_batches` (modelo ExtractionBatchModel).
                # Antes se consultaba `document_batches` (tabla inexistente), la query
                # lanzaba excepción y el `except` la tragaba: el check NUNCA disparaba y
                # los DNI ya matriculados pasaban como duplicados.
                text("SELECT activity_id FROM extraction_batches WHERE id = :bid"),
                {"bid": str(batch_id)}
            )
            batch_row = res_batch.fetchone()
            if batch_row and batch_row[0]:
                activity_id_str = str(batch_row[0])
                duplicate_reason = None

                # 1) Matrícula existente en la actividad
                res_enroll = await self.session.execute(
                    text("""
                        SELECT 1 FROM beneficiary_enrollments e
                        JOIN persons p ON p.id = e.beneficiary_id
                        WHERE p.dni = :dni AND e.activity_code = :act
                    """),
                    {"dni": b_dni, "act": activity_id_str}
                )
                if res_enroll.fetchone():
                    duplicate_reason = f"El DNI {b_dni} ya se encuentra inscrito en esta actividad. No se pueden procesar inscripciones duplicadas."

                # 2) Expediente en trámite para el mismo DNI y actividad (se excluye
                #    el propio caso que se está procesando y los rechazados)
                if not duplicate_reason:
                    res_pending = await self.session.execute(
                        text("""
                            SELECT 1 FROM triage_cases tc
                            JOIN extraction_batches eb ON eb.id = tc.batch_id
                            WHERE eb.activity_id = :act
                              AND tc.dossier_data->'beneficiary'->>'dni' = :dni
                              AND tc.status <> 'REJECTED'
                              AND tc.id <> :current_case_id
                            LIMIT 1
                        """),
                        {"act": activity_id_str, "dni": b_dni, "current_case_id": str(case.id)}
                    )
                    if res_pending.fetchone():
                        duplicate_reason = f"El DNI {b_dni} ya tiene un expediente en trámite (pendiente de revisión o aprobación) para esta actividad. No se pueden procesar inscripciones duplicadas."

                if duplicate_reason:
                    from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
                    from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
                    from src.contexts.data_quality_triage.domain.shared.value_objects.triage_verdict import TriageVerdict
                    
                    case.discrepancies.append(FieldDiscrepancy(
                        field_name="beneficiary.dni",
                        expected_pattern="DNI no inscrito en esta actividad",
                        actual_value=b_dni,
                        rule_description=duplicate_reason,
                        severity="ERROR",
                        document_code="DOMINIO"
                    ))
                    
                    case.status = TriageStatus.REJECTED
                    case.verdict = TriageVerdict.AUTOMATICALLY_REJECTED
        except Exception as e:
            logger.error(f"Error checking duplicate registration: {e}", exc_info=True)
        # -------------------------------------

        # 4. Persistencia y Eventos
        await self.triage_repo.save(case)
        await self._audit_and_dispatch(case, is_new=(existing_case is None))
        await self.session.commit()
        return case

    async def _audit_and_dispatch(self, case: TriageCase, is_new: bool = True) -> None:
        self.session.add(TriageAuditLogModel(
            id=uuid4(), triage_case_id=case.id,
            action="CREATED" if is_new else "EVALUATED", performed_by=SYSTEM_UUID,
            previous_status=None, new_status=case.status.value,
            details={
                "verdict":       case.verdict.value,
                "error_count":   sum(1 for d in case.discrepancies if d.severity == "ERROR"),
                "warning_count": sum(1 for d in case.discrepancies if d.severity == "WARNING"),
            },
        ))
        for event in case.pending_events:
            await EventDispatcher.dispatch(event)
        case.clear_events()
