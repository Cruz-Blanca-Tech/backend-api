import sys

with open('src/contexts/data_quality_triage/application/shared/services/dossier_processor.py', 'r', encoding='utf-8') as f:
    c = f.read()

injection = '''
        # --- DUPLICATE ENROLLMENT CHECK ---
        try:
            res_batch = await self.session.execute(
                text("SELECT activity_id FROM document_batches WHERE id = :bid"),
                {"bid": str(batch_id)}
            )
            batch_row = res_batch.fetchone()
            if batch_row and batch_row[0]:
                activity_id_str = str(batch_row[0])
                res_enroll = await self.session.execute(
                    text("""
                        SELECT 1 FROM beneficiary_enrollments e
                        JOIN persons p ON p.id = e.beneficiary_id
                        WHERE p.dni = :dni AND e.activity_code = :act
                    """),
                    {"dni": b_dni, "act": activity_id_str}
                )
                if res_enroll.fetchone():
                    from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
                    from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
                    from src.contexts.data_quality_triage.domain.shared.value_objects.triage_verdict import TriageVerdict
                    
                    case.discrepancies.append(FieldDiscrepancy(
                        field_name="beneficiary.dni",
                        expected_pattern="DNI no inscrito en esta actividad",
                        actual_value=b_dni,
                        rule_description=f"El DNI {b_dni} ya se encuentra inscrito en esta actividad. No se pueden procesar inscripciones duplicadas.",
                        severity="ERROR",
                        document_code="DOMINIO"
                    ))
                    
                    case.status = TriageStatus.REJECTED
                    case.verdict = TriageVerdict.AUTOMATICALLY_REJECTED
        except Exception as e:
            logger.error(f"Error checking duplicate enrollment: {e}", exc_info=True)
'''

# Find the end of fuzzy match block
idx = c.find('        # -------------------------------------')
if idx != -1:
    c = c[:idx] + injection + c[idx:]
    with open('src/contexts/data_quality_triage/application/shared/services/dossier_processor.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Injected successfully!")
else:
    print("Could not find insertion point!")
