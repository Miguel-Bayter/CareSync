"""Factory for MedicationModel test fixtures."""

from datetime import date, timedelta

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.medication import MedicationModel


class MedicationFactory(SQLAlchemyModelFactory):
    """Factory that produces MedicationModel instances for tests.

    patient_id must be provided explicitly because it is a required FK:
        MedicationFactory(patient_id=patient.id, _session=db_session)
    """

    class Meta:
        model = MedicationModel
        sqlalchemy_session_persistence = "flush"

    generic_name = factory.Sequence(lambda n: f"metformin_{n}")
    brand_name = factory.Sequence(lambda n: f"Glucophage_{n}")
    dose_mg = 500.0
    frequency_hours = 8
    with_food = True
    current_stock_units = 30
    minimum_stock_units = 5
    expiration_date = factory.LazyFunction(lambda: date.today() + timedelta(days=180))
    is_active = True
