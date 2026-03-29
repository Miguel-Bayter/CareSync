"""Factory for ElderlyPatientModel test fixtures."""

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.patient import ElderlyPatientModel
from tests.factories.caregiver_factory import CaregiverFactory


class PatientFactory(SQLAlchemyModelFactory):
    """Factory that produces ElderlyPatientModel instances for tests."""

    class Meta:
        model = ElderlyPatientModel
        sqlalchemy_session_persistence = "flush"

    full_name = factory.Faker("name")
    date_of_birth = factory.Faker("date_of_birth", minimum_age=65, maximum_age=100)
    room_number = factory.Faker("bothify", text="##?")
    caregiver = factory.SubFactory(CaregiverFactory)
    # caregiver_id is derived from the SubFactory; set explicitly if needed
    chronic_conditions: list[str] = []
    emergency_contact_name = factory.Faker("name")
    emergency_contact_phone = factory.Faker("phone_number")
    notes = None

    @factory.lazy_attribute
    def caregiver_id(self) -> object:  # type: ignore[override]
        return self.caregiver.id
