"""Repository for MedicationAlertModel — persistence operations."""

from sqlalchemy.orm import Session

from app.models.alert import MedicationAlertModel
from app.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[MedicationAlertModel]):
    """Data access layer for medication alerts."""

    model_class = MedicationAlertModel

    def __init__(self, db: Session) -> None:
        super().__init__(db)
