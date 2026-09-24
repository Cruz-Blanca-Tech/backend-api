import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

class PersonRelationshipModel(Base):
    """
    Generic many-to-many relationship table between two Person entities.
    Allows modeling graph structures like Parent-Child, Siblings, Spouses, etc.
    """
    __tablename__ = "person_relationships"

    from_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), primary_key=True)
    to_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), primary_key=True)
    
    # Example roles: 'MOTHER', 'FATHER', 'SIBLING', 'GUARDIAN'
    # From the perspective of 'from_person_id' -> 'to_person_id'
    # (e.g. Beneficiary A -> MOTHER -> Adult B)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=True)
