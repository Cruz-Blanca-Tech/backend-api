#!/usr/bin/env python3
"""
Script de exportación para tesis: auditoría completa de expedientes.

Uso:
    python export_thesis.py --batch-id <BATCH_UUID> --output formato [json|excel] --file archivo_salida
    python export_thesis.py --all --output excel --file tesis_data.xlsx

Exporta por expediente:
  - created_at          : cuándo se creó el expediente (1er procesamiento IA)
  - completed_at        : cuándo terminó el procesamiento (auto o manual)
  - errores_iniciales   : errores del primer procesamiento (del evento CREATED de la
                          auditoría; NO del snapshot, que los guarda sin severidad)
  - warnings_iniciales  : warnings del primer procesamiento (ídem)
  - issues_en_snapshot   : issues anotados por la IA en el snapshot, sin severidad
  - errores_finales     : errores al cerrar el expediente (de `discrepancies`)
  - correcciones_usuario: cuántas correcciones manuales hizo el usuario (audit_log action=CORRECTED)
  - correcciones_auto   : cuántas correcciones automáticas (audit_log action=AUTO_CORRECTION)
  - usuario_final       : quién aprobó/rechazó (resolved_by)
  - status, verdict     : estado y veredicto final
  - sync_status, sync_error : qué pasó con la carga al maestro

Exporta por lote (hoja "Lotes"):
  - created_at          : cuándo se creó el lote
  - procesamiento_fin   : cuándo terminó de leer el último documento
    (ATENCIÓN: es DERIVADO = max(document_items.processed_at). La tabla
     extraction_batches no tiene columna de fin; ver README de la exportación)
  - triage_fin          : cuándo se decidió el último expediente

Exporta la traza completa de auditoría (hoja "Auditoria"): una fila por
evento de triage_audit_log.

Salida: por defecto en una carpeta FUERA del repo (contiene datos
personales reales: DNI, nombres, fechas de nacimiento).
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent))

# La exportación NO va al repo: contiene DNI, nombres y fechas de nacimiento
# de personas reales, y .gitignore no es una garantía suficiente.
DEFAULT_OUT_DIR = Path.home() / "Documents" / "tesis" / "CruzBlanca"

from src.core.database import async_session_maker
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel


# Campos internos/calculados que el formulario del frontend no envía al guardar,
# por lo que compararlos contra original_dossier_data genera falsos positivos.
_IGNORED_DIFF_FIELDS = {
    "validation_issues",
    "age",
    "dj_signer_dni",
    "fins_guardian_dni",
    "has_complete_vaccines",
}

SYSTEM_UUID_STR = "00000000-0000-0000-0000-000000000000"


def _format_user_name(user_id_str: str | None, user_name: str | None, user_email: str | None = None) -> str | None:
    if not user_id_str:
        return None
    if user_id_str == SYSTEM_UUID_STR:
        return "SISTEMA (Automático)"
    return user_name or user_email or user_id_str


def _extract_beneficiary_info(dossier: dict | None, fallback_dni: str | None = None) -> tuple[str | None, str | None]:
    """Devuelve (dni, nombre_completo) del beneficiario."""
    ben = (dossier or {}).get("beneficiary") or {}
    dni = ben.get("dni") or fallback_dni
    first_name = (ben.get("first_name") or "").strip()
    last_name = (ben.get("last_name") or "").strip()
    full_name = f"{first_name} {last_name}".strip() or None
    return dni, full_name


def _diff_dossier(orig: dict | None, final: dict | None) -> list[dict]:
    """Calcula únicamente los campos de negocio que cambiaron entre dos estados del dossier."""
    orig = orig or {}
    final = final or {}
    changes: list[dict] = []

    sections = ["beneficiary", "related_adults", "education", "medical", "permissions", "religion"]
    for section in sections:
        orig_sec = orig.get(section) or {}
        final_sec = final.get(section) or {}
        if not isinstance(orig_sec, dict) or not isinstance(final_sec, dict):
            continue

        all_keys = sorted(set(orig_sec.keys()) | set(final_sec.keys()))
        for key in all_keys:
            if key in _IGNORED_DIFF_FIELDS:
                continue

            ov = orig_sec.get(key)
            fv = final_sec.get(key)

            # Desglosar lista de adultos (related_adults.adults) campo por campo
            if section == "related_adults" and key == "adults" and (isinstance(ov, list) or isinstance(fv, list)):
                o_list = ov if isinstance(ov, list) else []
                f_list = fv if isinstance(fv, list) else []
                max_len = max(len(o_list), len(f_list))
                for idx in range(max_len):
                    o_ad = o_list[idx] if idx < len(o_list) and isinstance(o_list[idx], dict) else {}
                    f_ad = f_list[idx] if idx < len(f_list) and isinstance(f_list[idx], dict) else {}
                    ad_keys = sorted(set(o_ad.keys()) | set(f_ad.keys()))
                    for ad_k in ad_keys:
                        if ad_k in _IGNORED_DIFF_FIELDS:
                            continue
                        if o_ad.get(ad_k) != f_ad.get(ad_k):
                            changes.append({
                                "section": section,
                                "field": f"adults[{idx}].{ad_k}",
                                "original": o_ad.get(ad_k),
                                "final": f_ad.get(ad_k),
                            })
                continue

            if ov != fv:
                changes.append({
                    "section": section,
                    "field": key,
                    "original": ov,
                    "final": fv,
                })

    return changes


async def export_thesis_data(
    batch_id: UUID | None = None,
    limit: int | None = None,
    offset: int = 0
) -> list[dict]:
    """Exporta datos de auditoría para tesis."""
    
    async with async_session_maker() as session:
        if batch_id:
            where_clause = f"WHERE tc.batch_id = '{str(batch_id)}'::uuid"
        else:
            where_clause = ""
        
        query = text(f"""
            SELECT 
                tc.id,
                tc.batch_id,
                tc.dni_reference,
                tc.created_at,
                tc.completed_at,
                tc.resolved_at,
                tc.resolved_by,
                u_res.full_name AS resolved_by_name,
                u_res.email AS resolved_by_email,
                tc.status,
                tc.verdict,
                tc.sync_status,
                tc.sync_error,
                tc.dossier_data,
                tc.original_dossier_data,
                tc.discrepancies,
                COALESCE((
                    SELECT (al.details->>'error_count')::int
                    FROM triage_audit_log al
                    WHERE al.triage_case_id = tc.id AND al.action = 'CREATED'
                    ORDER BY al.created_at ASC
                    LIMIT 1
                ), 0) AS errores_iniciales,
                COALESCE((
                    SELECT (al.details->>'warning_count')::int
                    FROM triage_audit_log al
                    WHERE al.triage_case_id = tc.id AND al.action = 'CREATED'
                    ORDER BY al.created_at ASC
                    LIMIT 1
                ), 0) AS warnings_iniciales,
                COALESCE((
                    SELECT count(*)
                    FROM jsonb_each(COALESCE(tc.original_dossier_data, '{{}}'::jsonb)) sec,
                         LATERAL jsonb_array_elements(
                             CASE WHEN jsonb_typeof(sec.value->'validation_issues') = 'array'
                                  THEN sec.value->'validation_issues'
                                  ELSE '[]'::jsonb END) v
                ), 0) AS issues_en_snapshot,
                COALESCE((
                    SELECT count(*) 
                    FROM jsonb_array_elements(tc.discrepancies) d
                    WHERE d->>'severity' = 'ERROR'
                ), 0) AS errores_finales,
                COALESCE((
                    SELECT count(*) 
                    FROM jsonb_array_elements(tc.discrepancies) d
                    WHERE d->>'severity' = 'WARNING'
                ), 0) AS warnings_finales,
                COALESCE((
                    SELECT count(*) 
                    FROM jsonb_array_elements(tc.discrepancies) d
                    WHERE d->>'severity' = 'AI_INSIGHT'
                ), 0) AS ai_insights_finales,
                COALESCE((
                    SELECT count(*) 
                    FROM triage_audit_log al 
                    WHERE al.triage_case_id = tc.id AND al.action = 'CORRECTED'
                ), 0) AS correcciones_usuario,
                COALESCE((
                    SELECT count(*) 
                    FROM triage_audit_log al 
                    WHERE al.triage_case_id = tc.id AND al.action = 'AUTO_CORRECTION'
                ), 0) AS correcciones_auto,
                (
                    SELECT jsonb_agg(jsonb_build_object(
                        'type', al.details->'correction_type',
                        'fields', al.details->'fields_changed',
                        'trigger', al.details->>'trigger',
                        'master_match', al.details->'master_match',
                        'timestamp', al.created_at
                    ) ORDER BY al.created_at ASC) 
                    FROM triage_audit_log al 
                    WHERE al.triage_case_id = tc.id AND al.action = 'AUTO_CORRECTION'
                ) AS auto_corrections_detail,
                (
                    SELECT jsonb_agg(jsonb_build_object(
                        'fields', al.details->'corrected_fields',
                        'timestamp', al.created_at,
                        'user_id', al.performed_by,
                        'user_name', u_al.full_name,
                        'user_email', u_al.email
                    ) ORDER BY al.created_at ASC) 
                    FROM triage_audit_log al
                    LEFT JOIN users u_al ON u_al.id = al.performed_by
                    WHERE al.triage_case_id = tc.id AND al.action = 'CORRECTED'
                ) AS manual_corrections_detail
            FROM triage_cases tc
            LEFT JOIN users u_res ON u_res.id = tc.resolved_by
            {where_clause}
            ORDER BY tc.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await session.execute(
            query, 
            {"limit": limit or 10000, "offset": offset}
        )
        
        rows = []
        for row in result:
            orig = row.original_dossier_data or {}
            final = row.dossier_data or {}
            dni, beneficiary_name = _extract_beneficiary_info(final or orig, row.dni_reference)

            # Diff global (original vs final)
            fields_changed = _diff_dossier(orig, final)

            # Diff paso a paso para cada corrección manual del usuario
            prev_snapshot = orig
            processed_manual_corrections = []
            for corr in (row.manual_corrections_detail or []):
                curr_snapshot = corr.get("fields")
                if isinstance(curr_snapshot, str):
                    try:
                        curr_snapshot = json.loads(curr_snapshot)
                    except Exception:
                        curr_snapshot = {}

                if isinstance(curr_snapshot, dict):
                    step_changes = _diff_dossier(prev_snapshot, curr_snapshot)
                    prev_snapshot = curr_snapshot
                else:
                    step_changes = []

                uid_str = str(corr.get("user_id")) if corr.get("user_id") else None
                uname = _format_user_name(uid_str, corr.get("user_name"), corr.get("user_email"))

                processed_manual_corrections.append({
                    "triage_case_id": str(row.id),
                    "dni_reference": dni,
                    "beneficiary_name": beneficiary_name,
                    "timestamp": corr.get("timestamp"),
                    "user_id": uid_str,
                    "user_name": uname,
                    "changes": step_changes,
                })

            resolved_by_str = str(row.resolved_by) if row.resolved_by else None
            resolved_by_name = _format_user_name(resolved_by_str, row.resolved_by_name, row.resolved_by_email)
            if not resolved_by_name and row.verdict == "AUTO_APPROVED":
                resolved_by_name = "SISTEMA (Automático)"

            duracion_segundos = None
            duracion_minutos = None
            if row.created_at and row.completed_at:
                try:
                    c_ini = row.created_at
                    c_fin = _aware(row.completed_at, c_ini)
                    secs = (c_fin - c_ini).total_seconds()
                    duracion_segundos = round(secs, 1)
                    duracion_minutos = round(secs / 60, 1)
                except Exception:
                    pass

            # Mapear notas reales de SurnameAutoCorrector desde discrepancies
            surname_notes = {}
            for d in (row.discrepancies or []):
                if (
                    isinstance(d, dict)
                    and d.get("severity") == "INFO"
                    and str(d.get("rule_description") or "").startswith("Corrección automática:")
                    and d.get("field_name")
                ):
                    surname_notes[d["field_name"]] = d.get("actual_value")

            # Filtrar entradas fantasma de AUTO_CORRECTION (p. ej. ApoderadoNameReconciler
            # previo al fix que emitía INFO sin mutar el dossier)
            valid_auto_details = []
            for ac in (row.auto_corrections_detail or []):
                ac_fields = ac.get("fields") or {}
                if isinstance(ac_fields, dict):
                    clean_fields = {}
                    for fk, fv in ac_fields.items():
                        if fk.startswith("related_adults.adults[") and fk.endswith("].full_name"):
                            try:
                                idx = int(fk.split("[")[1].split("]")[0])
                                orig_adults = (orig.get("related_adults") or {}).get("adults") or []
                                actual_adult_name = (
                                    orig_adults[idx].get("full_name")
                                    if idx < len(orig_adults) and isinstance(orig_adults[idx], dict)
                                    else None
                                )
                                target_val = fv.get("despues") if isinstance(fv, dict) else fv
                                if (
                                    isinstance(target_val, str)
                                    and isinstance(actual_adult_name, str)
                                    and target_val != actual_adult_name
                                ):
                                    if fk in surname_notes and surname_notes[fk] != actual_adult_name:
                                        fv = {"antes": surname_notes[fk], "despues": actual_adult_name}
                                    else:
                                        continue
                                elif fk in surname_notes and not isinstance(fv, dict):
                                    fv = {"antes": surname_notes[fk], "despues": actual_adult_name}
                            except Exception:
                                pass
                        clean_fields[fk] = fv
                    if clean_fields:
                        valid_auto_details.append({**ac, "fields": clean_fields})
                else:
                    valid_auto_details.append(ac)

            # Incluir cambios de SurnameAutoCorrector en campos_cambiados si aún no figuran
            existing_change_keys = {(c["section"], c["field"]) for c in fields_changed}
            for fk, before_val in surname_notes.items():
                if fk.startswith("related_adults."):
                    sub_field = fk.split("related_adults.", 1)[1]
                    try:
                        idx = int(sub_field.split("[")[1].split("]")[0])
                        final_adults = (final.get("related_adults") or {}).get("adults") or []
                        after_val = (
                            final_adults[idx].get("full_name")
                            if idx < len(final_adults) and isinstance(final_adults[idx], dict)
                            else None
                        )
                        if before_val and after_val and before_val != after_val and ("related_adults", sub_field) not in existing_change_keys:
                            fields_changed.append({
                                "section": "related_adults",
                                "field": sub_field,
                                "original": before_val,
                                "final": after_val,
                            })
                    except Exception:
                        pass

            rows.append({
                "id": str(row.id),
                "batch_id": str(row.batch_id),
                "dni_reference": dni,
                "beneficiary_name": beneficiary_name,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
                "resolved_by": resolved_by_str,
                "resolved_by_name": resolved_by_name,
                "status": row.status,
                "verdict": row.verdict,
                "sync_status": row.sync_status,
                "sync_error": row.sync_error,
                "errores_iniciales": row.errores_iniciales,
                "warnings_iniciales": row.warnings_iniciales,
                "issues_en_snapshot": row.issues_en_snapshot,
                "errores_finales": row.errores_finales,
                "warnings_finales": row.warnings_finales,
                "ai_insights_finales": row.ai_insights_finales,
                "correcciones_usuario": row.correcciones_usuario,
                "correcciones_auto": len(valid_auto_details),
                "duracion_segundos": duracion_segundos,
                "duracion_minutos": duracion_minutos,
                "campos_cambiados": fields_changed,
                "auto_corrections_detail": valid_auto_details or None,
                "manual_corrections_detail": processed_manual_corrections,
            })
        
        return rows


def _aware(dt, ref):
    """processed_at es timestamp SIN timezone; created_at es CON timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None and ref is not None:
        return dt.replace(tzinfo=ref.tzinfo)
    return dt


async def export_batch_data(batch_id: UUID | None = None) -> list[dict]:
    """Tiempos a nivel lote."""
    async with async_session_maker() as session:
        if batch_id:
            where = "WHERE b.id = CAST(:batch_id AS uuid)"
            params = {"batch_id": str(batch_id)}
        else:
            where = ""
            params = {}

        query = text(f"""
            SELECT
                b.id,
                b.activity_id,
                b.status,
                b.created_at,
                b.created_by,
                u.full_name AS created_by_name,
                u.email AS created_by_email,
                b.description,
                b.failure_reason,
                (SELECT count(*) FROM document_items di
                   WHERE di.batch_id = b.id) AS documentos,
                (SELECT count(*) FROM document_items di
                   WHERE di.batch_id = b.id AND di.processed_at IS NOT NULL) AS documentos_procesados,
                (SELECT max(di.processed_at) FROM document_items di
                   WHERE di.batch_id = b.id) AS procesamiento_fin,
                (SELECT count(*) FROM triage_cases tc
                   WHERE tc.batch_id = b.id) AS expedientes,
                (SELECT count(*) FROM triage_cases tc
                   WHERE tc.batch_id = b.id AND tc.completed_at IS NOT NULL) AS expedientes_terminados,
                (SELECT count(*) FROM triage_cases tc
                   WHERE tc.batch_id = b.id AND tc.resolved_at IS NOT NULL) AS expedientes_resueltos,
                (SELECT count(*) FROM triage_cases tc
                   WHERE tc.batch_id = b.id AND tc.status = 'REJECTED') AS expedientes_rechazados,
                (SELECT count(*) FROM triage_cases tc
                   WHERE tc.batch_id = b.id AND tc.sync_status = 'SYNCED') AS expedientes_sincronizados,
                (SELECT max(tc.completed_at) FROM triage_cases tc
                   WHERE tc.batch_id = b.id) AS triage_fin
            FROM extraction_batches b
            LEFT JOIN users u ON u.id = b.created_by
            {where}
            ORDER BY b.created_at DESC
        """)

        result = await session.execute(query, params)
        rows = []
        for row in result:
            creado = row.created_at
            proc_fin = _aware(row.procesamiento_fin, creado)
            triage_fin = _aware(row.triage_fin, creado)

            def segundos(a, b):
                if a is None or b is None:
                    return None
                return round((b - a).total_seconds(), 1)

            def minutos(a, b):
                if a is None or b is None:
                    return None
                return round((b - a).total_seconds() / 60, 1)

            created_by_str = str(row.created_by) if row.created_by else None
            created_by_name = _format_user_name(created_by_str, row.created_by_name, row.created_by_email)

            rows.append({
                "id": str(row.id),
                "activity_id": str(row.activity_id) if row.activity_id else None,
                "status": row.status,
                "created_at": creado.isoformat() if creado else None,
                "created_by": created_by_str,
                "created_by_name": created_by_name,
                "description": row.description,
                "failure_reason": row.failure_reason,
                "documentos": row.documentos,
                "documentos_procesados": row.documentos_procesados,
                "procesamiento_fin": proc_fin.isoformat() if proc_fin else None,
                "expedientes": row.expedientes,
                "expedientes_terminados": row.expedientes_terminados,
                "expedientes_resueltos": row.expedientes_resueltos,
                "expedientes_rechazados": row.expedientes_rechazados,
                "expedientes_sincronizados": row.expedientes_sincronizados,
                "triage_fin": triage_fin.isoformat() if triage_fin else None,
                "segundos_lectura": segundos(creado, proc_fin),
                "segundos_triage": segundos(proc_fin, triage_fin),
                "segundos_total": segundos(creado, triage_fin),
                "minutos_lectura": minutos(creado, proc_fin),
                "minutos_triage": minutos(proc_fin, triage_fin),
                "minutos_total": minutos(creado, triage_fin),
            })
        return rows


async def export_audit_data(batch_id: UUID | None = None) -> list[dict]:
    """Traza completa de auditoría: una fila por evento, en orden cronológico,
    reemplazando el volcado completo de corrected_fields por solo los campos modificados."""
    async with async_session_maker() as session:
        if batch_id:
            where = "WHERE tc.batch_id = CAST(:batch_id AS uuid)"
            params = {"batch_id": str(batch_id)}
        else:
            where = ""
            params = {}

        query = text(f"""
            SELECT
                al.created_at,
                tc.dni_reference,
                tc.id AS triage_case_id,
                tc.original_dossier_data,
                tc.dossier_data,
                tc.discrepancies,
                al.action,
                al.previous_status,
                al.new_status,
                al.performed_by,
                u.full_name AS performed_by_name,
                u.email AS performed_by_email,
                al.details
            FROM triage_audit_log al
            JOIN triage_cases tc ON tc.id = al.triage_case_id
            LEFT JOIN users u ON u.id = al.performed_by
            {where}
            ORDER BY al.created_at ASC
        """)

        result = await session.execute(query, params)
        prev_snapshots: dict[str, dict] = {}
        audit_rows = []

        for row in result:
            case_id_str = str(row.triage_case_id)
            orig = row.original_dossier_data or {}
            final = row.dossier_data or {}
            dni, ben_name = _extract_beneficiary_info(final or orig, row.dni_reference)

            if case_id_str not in prev_snapshots:
                prev_snapshots[case_id_str] = orig

            details = dict(row.details) if isinstance(row.details, dict) else row.details
            action_name = row.action
            if action_name == "AUTO_APPROVED" and isinstance(details, dict) and details.get("verdict") == "MANUALLY_APPROVED":
                action_name = "MANUALLY_APPROVED"

            if action_name == "AUTO_CORRECTION" and isinstance(details, dict):
                surname_notes = {}
                for d in (row.discrepancies or []):
                    if (
                        isinstance(d, dict)
                        and d.get("severity") == "INFO"
                        and str(d.get("rule_description") or "").startswith("Corrección automática:")
                        and d.get("field_name")
                    ):
                        surname_notes[d["field_name"]] = d.get("actual_value")

                ac_fields = details.get("fields_changed") or {}
                if isinstance(ac_fields, dict):
                    clean_fields = {}
                    for fk, fv in ac_fields.items():
                        if fk.startswith("related_adults.adults[") and fk.endswith("].full_name"):
                            try:
                                idx = int(fk.split("[")[1].split("]")[0])
                                orig_adults = (orig.get("related_adults") or {}).get("adults") or []
                                actual_adult_name = (
                                    orig_adults[idx].get("full_name")
                                    if idx < len(orig_adults) and isinstance(orig_adults[idx], dict)
                                    else None
                                )
                                target_val = fv.get("despues") if isinstance(fv, dict) else fv
                                if (
                                    isinstance(target_val, str)
                                    and isinstance(actual_adult_name, str)
                                    and target_val != actual_adult_name
                                ):
                                    if fk in surname_notes and surname_notes[fk] != actual_adult_name:
                                        fv = {"antes": surname_notes[fk], "despues": actual_adult_name}
                                    else:
                                        continue
                                elif fk in surname_notes and not isinstance(fv, dict):
                                    fv = {"antes": surname_notes[fk], "despues": actual_adult_name}
                            except Exception:
                                pass
                        clean_fields[fk] = fv
                    if not clean_fields:
                        continue
                    details = {**details, "fields_changed": clean_fields, "count": len(clean_fields)}

            if action_name == "CORRECTED" and isinstance(details, dict) and "corrected_fields" in details:
                curr_snap = details.get("corrected_fields")
                if isinstance(curr_snap, dict):
                    step_changes = _diff_dossier(prev_snapshots[case_id_str], curr_snap)
                    prev_snapshots[case_id_str] = curr_snap
                    details = {
                        k: v for k, v in details.items() if k != "corrected_fields"
                    }
                    details["changed_fields"] = {
                        f"{c['section']}.{c['field']}": {"antes": c["original"], "despues": c["final"]}
                        for c in step_changes
                    }

            uid_str = str(row.performed_by) if row.performed_by else None
            uname = _format_user_name(uid_str, row.performed_by_name, row.performed_by_email)

            audit_rows.append({
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "triage_case_id": case_id_str,
                "dni_reference": dni,
                "beneficiary_name": ben_name,
                "action": action_name,
                "previous_status": row.previous_status,
                "new_status": row.new_status,
                "performed_by": uid_str,
                "performed_by_name": uname,
                "details": details,
            })

        return audit_rows


def _style_header(ws, headers: list[str], fill_color: str = "2F5496"):
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)


def _autosize(ws, max_width: int = 50):
    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, max_width)


def write_json(data: list[dict], filepath: Path, batches: list[dict] | None = None,
               audits: list[dict] | None = None):
    """Escribe JSON con formato legible."""
    payload = {
        "lotes": batches or [],
        "expedientes": data,
        "auditoria": audits or [],
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    print(f"OK JSON guardado en: {filepath} ({len(data)} expedientes, "
          f"{len(payload['lotes'])} lotes, {len(payload['auditoria'])} eventos)")


def write_excel(data: list[dict], filepath: Path, batches: list[dict] | None = None,
                audits: list[dict] | None = None):
    """Escribe Excel con múltiples hojas."""
    batches = batches or []
    audits = audits or []
    wb = openpyxl.Workbook()

    # Hoja 0: Lotes (tiempos a nivel lote)
    ws0 = wb.active
    ws0.title = "Lotes"
    headers0 = [
        "Lote ID", "Estado", "Creado en", "Creado por (ID)", "Creado por (Nombre)",
        "Descripción", "Motivo de fallo",
        "Documentos", "Documentos leídos", "Terminó de leer (DERIVADO)",
        "Expedientes", "Terminados", "Resueltos", "Rechazados", "Cargados al maestro",
        "Terminó el triaje (DERIVADO)",
        "Segundos lectura", "Segundos triaje", "Segundos total",
        "Minutos lectura", "Minutos triaje", "Minutos total",
    ]
    _style_header(ws0, headers0, "1F6F43")
    for row_idx, b in enumerate(batches, 2):
        for col, key in enumerate([
            "id", "status", "created_at", "created_by", "created_by_name",
            "description", "failure_reason",
            "documentos", "documentos_procesados", "procesamiento_fin",
            "expedientes", "expedientes_terminados", "expedientes_resueltos",
            "expedientes_rechazados", "expedientes_sincronizados", "triage_fin",
            "segundos_lectura", "segundos_triage", "segundos_total",
            "minutos_lectura", "minutos_triage", "minutos_total",
        ], 1):
            ws0.cell(row=row_idx, column=col, value=b.get(key))
    _autosize(ws0)

    # Hoja 1: Resumen por expediente
    ws1 = wb.create_sheet("Resumen Expedientes")

    headers = [
        "ID Expediente", "DNI", "Beneficiario", "Batch ID",
        "Creado en", "Terminado en", "Resuelto en",
        "Resuelto por (ID)", "Resuelto por (Nombre)",
        "Estado", "Veredicto", "Carga al maestro", "Error de carga",
        "Errores Iniciales", "Warnings Iniciales", "Issues en Snapshot",
        "Errores Finales", "Warnings Finales", "AI Insights Finales",
        "Errores Resueltos", "Correcciones Usuario", "Correcciones Auto",
        "Duración (segundos)", "Duración (minutos)"
    ]
    _style_header(ws1, headers)

    for row_idx, item in enumerate(data, 2):
        values = [
            item["id"],
            item["dni_reference"],
            item.get("beneficiary_name"),
            item["batch_id"],
            item["created_at"],
            item["completed_at"],
            item["resolved_at"],
            item["resolved_by"],
            item.get("resolved_by_name"),
            item["status"],
            item["verdict"],
            item.get("sync_status"),
            item.get("sync_error"),
            item["errores_iniciales"],
            item["warnings_iniciales"],
            item["issues_en_snapshot"],
            item["errores_finales"],
            item["warnings_finales"],
            item["ai_insights_finales"],
            (item["errores_iniciales"] - item["errores_finales"]),
            item["correcciones_usuario"],
            item["correcciones_auto"],
            item.get("duracion_segundos"),
            item.get("duracion_minutos"),
        ]

        for col, val in enumerate(values, 1):
            ws1.cell(row=row_idx, column=col, value=val)

    _autosize(ws1)

    # Hoja 2: Detalle de correcciones automáticas
    ws2 = wb.create_sheet("Correcciones Auto")
    headers2 = ["Expediente ID", "DNI", "Beneficiario", "Timestamp", "Tipo", "Campos", "Trigger", "Detalle Maestro"]
    _style_header(ws2, headers2)

    row_idx = 2
    for item in data:
        if item["auto_corrections_detail"]:
            for corr in item["auto_corrections_detail"]:
                ws2.cell(row=row_idx, column=1, value=item["id"])
                ws2.cell(row=row_idx, column=2, value=item["dni_reference"])
                ws2.cell(row=row_idx, column=3, value=item.get("beneficiary_name"))
                ws2.cell(row=row_idx, column=4, value=corr.get("timestamp"))
                ws2.cell(row=row_idx, column=5, value=json.dumps(corr.get("type"), ensure_ascii=False) if isinstance(corr.get("type"), (list, dict)) else corr.get("type"))
                ws2.cell(row=row_idx, column=6, value=json.dumps(corr.get("fields"), ensure_ascii=False) if isinstance(corr.get("fields"), (list, dict)) else corr.get("fields"))
                ws2.cell(row=row_idx, column=7, value=corr.get("trigger"))
                ws2.cell(row=row_idx, column=8, value=json.dumps(corr.get("master_match"), ensure_ascii=False) if corr.get("master_match") else "")
                row_idx += 1
    _autosize(ws2)

    # Hoja 3: Detalle de correcciones manuales (solo lo que se cambió)
    ws3 = wb.create_sheet("Correcciones Usuario")
    headers3 = [
        "Expediente ID", "DNI", "Beneficiario", "Timestamp",
        "Usuario ID", "Nombre Usuario",
        "Sección", "Campo Corregido", "Valor Anterior", "Valor Nuevo"
    ]
    _style_header(ws3, headers3)

    row_idx = 2
    for item in data:
        for corr in (item["manual_corrections_detail"] or []):
            changes = corr.get("changes") or []
            if changes:
                for ch in changes:
                    ws3.cell(row=row_idx, column=1, value=item["id"])
                    ws3.cell(row=row_idx, column=2, value=item["dni_reference"])
                    ws3.cell(row=row_idx, column=3, value=item.get("beneficiary_name"))
                    ws3.cell(row=row_idx, column=4, value=corr.get("timestamp"))
                    ws3.cell(row=row_idx, column=5, value=corr.get("user_id"))
                    ws3.cell(row=row_idx, column=6, value=corr.get("user_name"))
                    ws3.cell(row=row_idx, column=7, value=ch["section"])
                    ws3.cell(row=row_idx, column=8, value=ch["field"])
                    ws3.cell(row=row_idx, column=9, value=str(ch["original"]) if ch["original"] is not None else "")
                    ws3.cell(row=row_idx, column=10, value=str(ch["final"]) if ch["final"] is not None else "")
                    row_idx += 1
            else:
                ws3.cell(row=row_idx, column=1, value=item["id"])
                ws3.cell(row=row_idx, column=2, value=item["dni_reference"])
                ws3.cell(row=row_idx, column=3, value=item.get("beneficiary_name"))
                ws3.cell(row=row_idx, column=4, value=corr.get("timestamp"))
                ws3.cell(row=row_idx, column=5, value=corr.get("user_id"))
                ws3.cell(row=row_idx, column=6, value=corr.get("user_name"))
                ws3.cell(row=row_idx, column=7, value="-")
                ws3.cell(row=row_idx, column=8, value="(Guardado sin cambios adicionales)")
                ws3.cell(row=row_idx, column=9, value="")
                ws3.cell(row=row_idx, column=10, value="")
                row_idx += 1
    _autosize(ws3)

    # Hoja 4: Campos cambiados (diff original vs final)
    ws4 = wb.create_sheet("Campos Cambiados")
    headers4 = ["Expediente ID", "DNI", "Beneficiario", "Sección", "Campo", "Original", "Final"]
    _style_header(ws4, headers4)

    row_idx = 2
    for item in data:
        for change in item["campos_cambiados"]:
            ws4.cell(row=row_idx, column=1, value=item["id"])
            ws4.cell(row=row_idx, column=2, value=item["dni_reference"])
            ws4.cell(row=row_idx, column=3, value=item.get("beneficiary_name"))
            ws4.cell(row=row_idx, column=4, value=change["section"])
            ws4.cell(row=row_idx, column=5, value=change["field"])
            ws4.cell(row=row_idx, column=6, value=str(change["original"]) if change["original"] is not None else "")
            ws4.cell(row=row_idx, column=7, value=str(change["final"]) if change["final"] is not None else "")
            row_idx += 1
    _autosize(ws4)

    # Hoja 5: Traza completa de auditoría
    ws5 = wb.create_sheet("Auditoria")
    headers5 = [
        "Timestamp", "Expediente ID", "DNI", "Beneficiario",
        "Acción", "Estado anterior", "Estado nuevo",
        "Usuario ID", "Nombre Usuario", "Detalle"
    ]
    _style_header(ws5, headers5, "7A3E9D")

    for row_idx, ev in enumerate(audits, 2):
        for col, key in enumerate([
            "created_at", "triage_case_id", "dni_reference", "beneficiary_name",
            "action", "previous_status", "new_status",
            "performed_by", "performed_by_name", "details",
        ], 1):
            val = ev.get(key)
            ws5.cell(row=row_idx, column=col,
                     value=json.dumps(val, ensure_ascii=False) if key == "details" and val else val)
    _autosize(ws5)

    wb.save(filepath)
    print(f"OK Excel guardado en: {filepath} "
          f"({len(data)} expedientes, {len(batches)} lotes, {len(audits)} eventos, 6 hojas)")


async def main():
    parser = argparse.ArgumentParser(description="Exportar datos de auditoría para tesis")
    parser.add_argument("--batch-id", type=str, help="UUID del lote (opcional)")
    parser.add_argument("--all", action="store_true", help="Exportar todos los lotes")
    parser.add_argument("--output", choices=["json", "excel", "both"], default="both", help="Formato de salida")
    parser.add_argument(
        "--out-dir", type=str, default=str(DEFAULT_OUT_DIR),
        help="Carpeta de salida. Por defecto FUERA del repo (datos personales reales)"
    )
    parser.add_argument("--file", type=str, help="Nombre base del archivo (sin extensión)")
    parser.add_argument("--limit", type=int, help="Límite de expedientes")
    parser.add_argument("--offset", type=int, default=0, help="Offset para paginación")

    args = parser.parse_args()

    if not args.batch_id and not args.all:
        parser.error("Debe especificar --batch-id o --all")

    batch_id = UUID(args.batch_id) if args.batch_id else None

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    nombre = args.file or f"tesis_{batch_id or 'todos'}_{stamp}"
    base_path = out_dir / nombre

    print(f"Exportando datos... (batch_id={batch_id or 'TODOS'}, limit={args.limit or 'sin límite'})")
    print(f"Carpeta de salida: {out_dir}")

    data = await export_thesis_data(batch_id=batch_id, limit=args.limit, offset=args.offset)
    batches = await export_batch_data(batch_id=batch_id)
    audits = await export_audit_data(batch_id=batch_id)

    if not data and not batches:
        print("No se encontraron datos")
        return

    if args.output in ("json", "both"):
        write_json(data, base_path.with_suffix(".json"), batches, audits)

    if args.output in ("excel", "both"):
        write_excel(data, base_path.with_suffix(".xlsx"), batches, audits)

    # Stats resumen
    total = len(data)
    con_errores_iniciales = sum(1 for d in data if d["errores_iniciales"] > 0)
    con_correcciones_usuario = sum(1 for d in data if d["correcciones_usuario"] > 0)
    con_correcciones_auto = sum(1 for d in data if d["correcciones_auto"] > 0)
    auto_aprobados = sum(1 for d in data if d["verdict"] == "AUTO_APPROVED")
    manual_aprobados = sum(1 for d in data if d["verdict"] == "MANUALLY_APPROVED")

    print(f"\n=== RESUMEN ===")
    print(f"Lotes: {len(batches)}")
    for b in batches:
        print(f"  {b['id']} | {b['status']} | creado {b['created_at']} "
              f"| terminó de leer {b['procesamiento_fin']} "
              f"| fin del triaje {b['triage_fin']}")
    print(f"Total expedientes: {total}")
    print(f"Eventos de auditoría: {len(audits)}")
    print(f"Errores iniciales (suma): {sum(d['errores_iniciales'] for d in data)}")
    print(f"Errores finales (suma): {sum(d['errores_finales'] for d in data)}")
    print(f"Con errores iniciales: {con_errores_iniciales}")
    print(f"Corregidos por usuario: {con_correcciones_usuario}")
    print(f"Con correcciones automáticas: {con_correcciones_auto}")
    print(f"AUTO_APPROVED: {auto_aprobados}")
    print(f"MANUALLY_APPROVED: {manual_aprobados}")


if __name__ == "__main__":
    asyncio.run(main())