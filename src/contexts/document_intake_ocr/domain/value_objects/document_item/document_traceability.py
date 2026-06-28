from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DocumentTraceability:
    source_id: str
    file_name: str
    custody_id: Optional[str] = None

    def with_custody(self, custody_id: str):
        return DocumentTraceability(
            source_id=self.source_id,
            file_name=self.file_name,
            custody_id=custody_id
        )