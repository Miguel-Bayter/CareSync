"""Factory for ResponsibleCaregiverModel test fixtures."""

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.core.security import hash_password
from app.models.caregiver import ResponsibleCaregiverModel


class CaregiverFactory(SQLAlchemyModelFactory):
    """Factory that produces ResponsibleCaregiverModel instances for tests."""

    class Meta:
        model = ResponsibleCaregiverModel
        sqlalchemy_session_persistence = "flush"

    full_name = factory.Faker("name")
    email = factory.Faker("email")
    hashed_password = factory.LazyFunction(lambda: hash_password("Password123"))
    is_active = True
