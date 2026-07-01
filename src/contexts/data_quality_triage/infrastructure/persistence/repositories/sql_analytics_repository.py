from typing import Dict, Any, List
from sqlalchemy import select, func, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus

class SqlAnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_summary_metrics(self) -> Dict[str, Any]:
        """
        Returns aggregate metrics for triage cases:
        - total_cases
        - by_status (AUTO_APPROVED, PENDING_REVIEW, etc)
        - average_confidence
        """
        # 1. Total and average confidence
        # Average confidence is tricky because confidence_scores is a dict in JSONB.
        # But we can calculate a simple average in memory for now, or just return basic counts.
        # To get the average, we can fetch all cases and calculate it.
        stmt = select(TriageCaseModel.status, TriageCaseModel.confidence_scores)
        result = await self.session.execute(stmt)
        
        total_cases = 0
        status_counts = {
            TriageStatus.AUTO_APPROVED.value: 0,
            TriageStatus.PENDING_REVIEW.value: 0,
            TriageStatus.MANUALLY_APPROVED.value: 0,
            TriageStatus.MANUALLY_REJECTED.value: 0,
            TriageStatus.REJECTED.value: 0,
            "OTHER": 0
        }
        
        all_confidences = []
        
        for row in result:
            status = row.status
            confidence_scores = row.confidence_scores
            
            total_cases += 1
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts["OTHER"] += 1
                
            if confidence_scores and isinstance(confidence_scores, dict):
                # Calcular promedio global del documento basado en sus scores
                doc_scores = [v for v in confidence_scores.values() if v is not None]
                if doc_scores:
                    doc_avg = sum(doc_scores) / len(doc_scores)
                    all_confidences.append(doc_avg)
                    
        global_avg_confidence = 0.0
        if all_confidences:
            global_avg_confidence = sum(all_confidences) / len(all_confidences)
            
        return {
            "total_cases": total_cases,
            "status_counts": status_counts,
            "global_average_confidence": round(global_avg_confidence, 4)
        }

    async def get_top_issues(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Returns the most common discrepancies.
        """
        stmt = select(TriageCaseModel.discrepancies)
        result = await self.session.execute(stmt)
        
        issue_counter = {}
        
        for row in result:
            discrepancies = row.discrepancies
            if not discrepancies:
                continue
                
            for d in discrepancies:
                field_name = d.get("field_name", "Unknown")
                rule_desc = d.get("rule_description", "Unknown Error")
                
                key = f"{field_name} - {rule_desc}"
                if key not in issue_counter:
                    issue_counter[key] = {
                        "field_name": field_name,
                        "description": rule_desc,
                        "count": 0
                    }
                issue_counter[key]["count"] += 1
                
        # Sort and limit
        sorted_issues = sorted(issue_counter.values(), key=lambda x: x["count"], reverse=True)
        return sorted_issues[:limit]
