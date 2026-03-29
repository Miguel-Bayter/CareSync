"""Seed script: creates a sample caregiver and elderly patient for development."""

import sys
from datetime import date
from pathlib import Path

# Allow running from project root: python scripts/seed.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.database import SessionLocal, engine, Base
from app.models.caregiver import ResponsibleCaregiverModel
from app.models.patient import ElderlyPatientModel

CAREGIVER_EMAIL = "cuidador@mimedicacion.com"
CAREGIVER_PASSWORD = "MiMedicacion2025!"


def seed() -> None:
    """Create all tables and insert seed data."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Idempotent: skip if caregiver already exists
        from sqlalchemy import select
        existing = db.scalar(
            select(ResponsibleCaregiverModel).where(
                ResponsibleCaregiverModel.email == CAREGIVER_EMAIL
            )
        )
        if existing is not None:
            print("Seed data already present — skipping.")
            return

        caregiver = ResponsibleCaregiverModel(
            email=CAREGIVER_EMAIL,
            full_name="Carlos Rodríguez",
            hashed_password=hash_password(CAREGIVER_PASSWORD),
        )
        db.add(caregiver)
        db.flush()

        patient = ElderlyPatientModel(
            full_name="Rosa González Torres",
            date_of_birth=date(1952, 6, 15),  # 74 years old (approx)
            room_number="101",
            caregiver_id=caregiver.id,
            chronic_conditions=["hypertension", "diabetes_type2"],
            emergency_contact_name="Lucía González",
            emergency_contact_phone="+57 300 123 4567",
            notes=(
                "Paciente de la región de Antioquia, Colombia. "
                "Requiere medicación con alimentos. "
                "Habla español únicamente."
            ),
        )
        db.add(patient)
        db.commit()

        print("Seed completed successfully.")
        print(f"  Caregiver : {CAREGIVER_EMAIL}  /  {CAREGIVER_PASSWORD}")
        print(f"  Patient   : {patient.full_name}  (id={patient.id})")
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
