# src/contexts/data_quality_triage/application/shared/services/llm_name_reconciler.py

import json
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from openai import AsyncAzureOpenAI

from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedDj, EnrichedAdult
from src.contexts.data_quality_triage.application.educa.mappers.enriched.dni_enriched_mapper import EnrichedDni
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult

logger = logging.getLogger(__name__)


@dataclass
class LLMDecision:
    """Decisión del LLM para un campo específico."""
    person: str          # "mother", "father", "child", "apoderado"
    field: str           # "paternal_surname", "maternal_surname", "first_name"
    chosen_value: str
    confidence: float    # 0.0 - 1.0
    reasoning: str


class LLMNameReconciler:
    """
    Reconciliador semántico de nombres usando LLM (Azure OpenAI).
    Se ejecuta COMO ÚLTIMO RECURSO tras los reconcilers determinísticos.
    Solo resuelve discrepancias NO resueltas (WARNINGs de coherencia).
    """

    def __init__(
        self,
        llm_client: AsyncAzureOpenAI,
        deployment_name: str,
        dniap: EnrichedDni,
        fins: EnrichedFins,
        dnibe: EnrichedDni,
        dj: Optional[EnrichedDj],
        dossier_adults: List[RelatedAdult],
    ):
        self.client = llm_client
        self.deployment = deployment_name
        self.dniap = dniap
        self.fins = fins
        self.dnibe = dnibe
        self.dj = dj
        self.dossier_adults = dossier_adults

    async def reconcile(self, unresolved_discrepancies: List[FieldDiscrepancy]) -> List[FieldDiscrepancy]:
        """
        Intenta resolver las discrepancias WARNING de coherencia que no pudieron
        ser resueltas por reglas determinísticas.
        
        Returns:
            Lista de FieldDiscrepancy (INFO) con las correcciones propuestas por el LLM.
        """
        if not unresolved_discrepancies:
            return []

        # Filtrar solo las que son de coherencia de apellidos
        coherence_issues = [
            d for d in unresolved_discrepancies
            if d.severity == "WARNING" and ("coherencia" in d.field_name.lower() or "apellido" in d.rule_description.lower())
        ]
        
        if not coherence_issues:
            return []

        # Construir prompt
        prompt = self._build_prompt(coherence_issues)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            if not content:
                logger.warning("LLMNameReconciler: respuesta vacía del LLM")
                return []
            
            result = json.loads(content)
            return self._parse_llm_result(result, coherence_issues)
            
        except json.JSONDecodeError as e:
            logger.error(f"LLMNameReconciler: error parseando JSON del LLM: {e}")
            return []
        except Exception as e:
            logger.error(f"LLMNameReconciler: error llamando al LLM: {e}")
            return []

    def _system_prompt(self) -> str:
        return """Eres un experto en reconciliación de nombres peruanos para validación de documentos oficiales.
Tu tarea: resolver discrepancias de apellidos/nombres que no pudieron ser resueltas por reglas determinísticas.

FUENTES DE DATOS (orden de confiabilidad):
1. DNIAP / DNIBE (documentos oficiales RENIEC) - CONFIABILIDAD ALTA
2. DJ (Declaración Jurada firmada ante notario) - CONFIABILIDAD MEDIA-ALTA
3. FINS (Ficha de Inscripción, declarada por apoderado) - CONFIABILIDAD BAJA

REGLAS DE NEGOCIO PERUANAS (estrictas):
- Apellido paterno del hijo = apellido paterno del padre
- Apellido materno del hijo = apellido paterno de la madre
- DNI único por persona (8 dígitos)
- Apellidos compuestos existen: "DE LA CRUZ", "SANCHEZ PEREZ", "DEL AGUILA"
- Errores OCR comunes en DNI/FINS: 
  * Vocales: a↔e, o↔u, i↔e (ej: BIR ↔ RIVERA, TAFOR ↔ TAFUR)
  * Consonantes: b↔v, c↔s, r↔n, l↔i, m↔n
  * Tildes perdidas: JULIA ↔ JULÍA
  * Espacios/guiones: "DELAROSA" vs "DE LA ROSA"

CONTEXTO FAMILIAR:
- Si un adulto tiene DNI que coincide con madre/padre/apoderado en FINS/DJ → es esa persona
- El apoderado en DNIAP debe coincidir con madre/padre/apoderado en FINS/DJ
- Apellido paterno del hijo = apellido paterno del padre (biología/ley)
- Apellido materno del hijo = apellido paterno de la madre (biología/ley)

TAREA: Resuelve ÚNICAMENTE las discrepancias que se te pasan. No inventes nuevas.
Para cada una, decide: valor correcto, confianza (0.0-1.0), razonamiento breve.
Si confianza < 0.75 → marcar como "unresolved" (no propones corrección).

FORMATO DE RESPUESTA (JSON estricto):
{
  "decisions": [
    {
      "person": "mother|father|child|apoderado",
      "field": "paternal_surname|maternal_surname|first_name",
      "chosen_value": "RIVERA",
      "confidence": 0.95,
      "reasoning": "Apellido materno del niño en DNIBE es RIVERA; FINS madre tiene RIVERA como paterno; BIR en FINS es error OCR vocálico (i↔e, r↔v)."
    }
  ],
  "unresolved": [
    {"person": "father", "field": "paternal_surname", "reason": "Sin DNI padre en ningún documento; FINS dice CONDORI pero DNIBE hijo dice CONDORI RIVERA; ambiguo."}
  ]
}"""

    def _build_prompt(self, coherence_issues: List[FieldDiscrepancy]) -> str:
        # Extraer datos normalizados
        def gn(f):  # get normalized
            if f is None: return None
            v = getattr(f, "normalized_value", None)
            if v is None: v = getattr(f, "value", None)
            return v.strip() if isinstance(v, str) and v.strip() else None

        def gn_last(f):
            v = gn(f)
            if not v: return None
            parts = v.split()
            return parts[-1] if parts else None

        # DNIAP (apoderado)
        dniap_dni = gn(self.dniap.document_number)
        dniap_fn = gn(self.dniap.first_name)
        dniap_ln = gn(self.dniap.last_name)

        # DNIBE (niño)
        dnibe_dni = gn(self.dnibe.document_number)
        dnibe_fn = gn(self.dnibe.first_name)
        dnibe_ln = gn(self.dnibe.last_name)  # completo paterno + materno

        # FINS
        fins_child_fn = gn(self.fins.child_first_name)
        fins_child_ln = gn(self.fins.child_last_name)
        
        # Adultos FINS
        fins_adults = []
        for a in self.fins.adults:
            role = getattr(a.role, "value", str(a.role)) if a.role else "UNKNOWN"
            fins_adults.append({
                "role": role,  # MOTHER, FATHER, OTHER
                "dni": gn(a.dni),
                "first": gn(a.first_name),
                "last": gn(a.last_name),
                "full": f"{gn(a.first_name) or ''} {gn(a.last_name) or ''}".strip(),
            })

        # DJ
        dj_data = {}
        if self.dj:
            dj_data = {
                "child_dni": gn(self.dj.child_dni),
                "father_dni": gn(self.dj.parents_father_dni),
                "father_name": gn(self.dj.parents_father_name),
                "mother_dni": gn(self.dj.parents_mother_dni),
                "mother_name": gn(self.dj.parents_mother_name),
                "guardian_dni": gn(self.dj.guardian_dni),
                "guardian_name": gn(self.dj.guardian_dni),  # guardian_dni es DNI, guardian_name no existe en EnrichedDj
            }

        # Discrepancias a resolver
        issues_desc = []
        for i, d in enumerate(coherence_issues):
            issues_desc.append(f"  {i+1}. {d.field_name} [{d.severity}]: {d.rule_description[:200]}")

        # Adultos en dossier (para mapear índices)
        adults_desc = []
        for i, a in enumerate(self.dossier_adults):
            adults_desc.append(f"  [{i}] {a.full_name.normalized_value if a.full_name else '?'} (DNI: {a.dni.normalized_value if a.dni else '?'}, rel: {a.relationship})")

        return f"""DATOS DEL EXPEDIENTE:

=== FUENTES OFICIALES (DNI) ===
DNIAP (apoderado):
  DNI: {gn(self.dniap.document_number) or 'N/A'}
  Nombres: {gn(self.dniap.first_name) or 'N/A'}
  Apellidos: {gn(self.dniap.last_name) or 'N/A'}

DNIBE (niño):
  DNI: {gn(self.dnibe.document_number) or 'N/A'}
  Nombres: {gn(self.dnibe.first_name) or 'N/A'}
  Apellidos (paterno+materno): {gn(self.dnibe.last_name) or 'N/A'}

=== DECLARACIONES ===
FINS (niño):
  Nombres: {gn(self.fins.child_first_name) or 'N/A'}
  Apellidos: {gn(self.fins.child_last_name) or 'N/A'}

FINS (adultos):
{self._format_adults(fins_adults)}

DJ:
{self._format_dj(dj_data)}

DISCREPANCIAS A RESOLVER (solo estas):
{chr(10).join(issues_desc)}

ADULTOS EN DOSSIER (índices para field_name):
{chr(10).join(adults_desc)}

TAREA: Resuelve SOLO las discrepancias listadas arriba. Devuelve JSON estricto."""

    def _format_adults(self, adults: list) -> str:
        if not adults:
            return "  (sin adultos)"
        return "\n".join(
            f"  - {a['role']}: {a['full']} (DNI: {a['dni'] or 'N/A'})" for a in adults
        )

    def _format_dj(self, dj: dict) -> str:
        if not dj:
            return "  (sin DJ)"
        parts = []
        if dj.get("father_name") or dj.get("father_dni"):
            parts.append(f"  Padre: {dj.get('father_name') or 'N/A'} (DNI: {dj.get('father_dni') or 'N/A'})")
        if dj.get("mother_name") or dj.get("mother_dni"):
            parts.append(f"  Madre: {dj.get('mother_name') or 'N/A'} (DNI: {dj.get('mother_dni') or 'N/A'})")
        if dj.get("guardian_dni"):
            parts.append(f"  Apoderado: (DNI: {dj.get('guardian_dni') or 'N/A'})")
        return "\n".join(parts) if parts else "  (sin datos)"

    def _parse_llm_result(self, result: dict, original_issues: List[FieldDiscrepancy]) -> List[FieldDiscrepancy]:
        corrections = []
        decisions = result.get("decisions", [])
        unresolved = result.get("unresolved", [])
        
        for dec in decisions:
            confidence = dec.get("confidence", 0)
            if confidence < 0.75:
                logger.info(f"LLMNameReconciler: decisión con baja confianza ({confidence}) ignorada: {dec}")
                continue
            
            person = dec.get("person")
            field = dec.get("field")
            chosen = dec.get("chosen_value")
            reasoning = dec.get("reasoning", "")
            
            if not all([person, field, chosen]):
                continue
            
            # Mapear person+field a field_name del dossier
            field_name = self._map_person_field_to_dossier(person, field)
            if not field_name:
                continue
            
            # Buscar el adulto en dossier_adults
            target_idx = self._find_adult_index(person)
            if target_idx is None:
                continue
            
            corrections.append(FieldDiscrepancy(
                field_name=f"related_adults.adults[{target_idx}].{field_name}",
                expected_pattern=chosen,
                actual_value="",  # se llenará en el llamador si hace falta
                rule_description=f"[LLM] {reasoning}",
                severity="INFO",
                document_code="DNIAP"  # genérico para nombre apoderado/padre/madre
            ))
        
        if unresolved:
            logger.info(f"LLMNameReconciler: {len(unresolved)} discrepancias no resueltas por LLM: {unresolved}")
        
        return corrections

    def _map_person_field_to_dossier(self, person: str, field: str) -> Optional[str]:
        """Mapea person+field a campo del dossier (related_adults)."""
        # En dossier, los adultos tienen full_name, first_name, last_name (paterno), maternal_surname
        if field == "first_name":
            return "first_name"
        elif field in ("paternal_surname", "last_name"):
            return "last_name"
        elif field == "maternal_surname":
            return "maternal_surname"
        return None

    def _find_adult_index(self, person: str) -> Optional[int]:
        """Encuentra el índice del adulto en dossier_adults según person."""
        # person: "mother", "father", "child", "apoderado"
        # Buscar por relationship en dossier_adults
        role_map = {"mother": "MOTHER", "father": "FATHER", "apoderado": "OTHER"}
        target_role = role_map.get(person.lower())
        if not target_role:
            return None
        
        for i, a in enumerate(self.dossier_adults):
            if getattr(a, "relationship", None) == target_role:
                return i
        return None