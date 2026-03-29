"""Domain value objects — immutable, equality-by-value.

Pure Python: no FastAPI, SQLAlchemy, or Pydantic dependencies.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AdherenceRate:
    """Value object: medication adherence percentage for one medication.

    Attributes:
        medication_id: UUID string of the medication.
        generic_name: Generic drug name.
        confirmed_count: Number of doses taken on time.
        missed_count: Number of missed doses.
        total_scheduled: Total doses scheduled in the period.
    """

    medication_id: str
    generic_name: str
    confirmed_count: int
    missed_count: int
    total_scheduled: int

    @property
    def adherence_percentage(self) -> float:
        """Compute adherence as a percentage rounded to two decimal places."""
        if self.total_scheduled == 0:
            return 0.0
        return round((self.confirmed_count / self.total_scheduled) * 100, 2)


@dataclass(frozen=True)
class CriticalStockReport:
    """Value object: medications with low stock or near expiration.

    Attributes:
        medication_id: UUID string of the medication.
        generic_name: Generic drug name.
        current_stock_units: Current number of units on hand.
        minimum_stock_units: Threshold below which stock is considered critical.
        days_until_expiration: Days remaining until the expiration date.
        is_expired: True if the medication is already past its expiration date.
    """

    medication_id: str
    generic_name: str
    current_stock_units: int
    minimum_stock_units: int
    days_until_expiration: int
    is_expired: bool
