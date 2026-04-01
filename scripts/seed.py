"""Seed script: Colombian family caring for elderly patient.

Demo story:
    Caregiver : Ana Milena Torres Restrepo — nurse at Hogar San José, Medellín
    Patient   : Rosa González Torres, 74 years old
                Diabetes type 2 + hypertension + arthritis
    Medications: Metformin, Losartan, Atorvastatin, Aspirin, Omeprazole

Run:
    python scripts/seed.py
"""

import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.domain.enums import DoseStatus
from app.models.caregiver import ResponsibleCaregiverModel
from app.models.dose import ScheduledDoseModel
from app.models.medication import MedicationModel
from app.models.patient import ElderlyPatientModel

CAREGIVER_EMAIL = "ana.torres@caresync.com"
CAREGIVER_PASSWORD = "Demo1234!"

MEDICATIONS = [
    {
        "generic_name": "metformin",
        "brand_name": "Glucophage",
        "dose_mg": 850.0,
        "frequency_hours": 8,
        "with_food": True,
        "current_stock_units": 28,
        "minimum_stock_units": 10,
        "days_until_expiry": 180,
    },
    {
        "generic_name": "losartan",
        "brand_name": "Cozaar",
        "dose_mg": 50.0,
        "frequency_hours": 24,
        "with_food": False,
        "current_stock_units": 18,
        "minimum_stock_units": 7,
        "days_until_expiry": 210,
    },
    {
        "generic_name": "atorvastatin",
        "brand_name": "Lipitor",
        "dose_mg": 20.0,
        "frequency_hours": 24,
        "with_food": False,
        "current_stock_units": 22,
        "minimum_stock_units": 7,
        "days_until_expiry": 365,
    },
    {
        "generic_name": "aspirin",
        "brand_name": "Aspirina",
        "dose_mg": 100.0,
        "frequency_hours": 24,
        "with_food": True,
        "current_stock_units": 5,   # critical stock — demonstrates alert
        "minimum_stock_units": 5,
        "days_until_expiry": 90,
    },
    {
        "generic_name": "omeprazole",
        "brand_name": "Losec",
        "dose_mg": 20.0,
        "frequency_hours": 24,
        "with_food": False,
        "current_stock_units": 30,
        "minimum_stock_units": 7,
        "days_until_expiry": 8,   # expiring soon — demonstrates alert
    },
]


def seed() -> None:
    """Create all tables and insert realistic Colombian seed data."""
    import app.models  # noqa: F401 — register all models with mapper
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.scalar(
            select(ResponsibleCaregiverModel).where(
                ResponsibleCaregiverModel.email == CAREGIVER_EMAIL
            )
        )
        if existing is not None:
            print("Seed data already present — skipping.")
            print(f"  Login with: {CAREGIVER_EMAIL} / {CAREGIVER_PASSWORD}")
            return

        # ── Caregiver ─────────────────────────────────────────────────
        caregiver = ResponsibleCaregiverModel(
            email=CAREGIVER_EMAIL,
            full_name="Ana Milena Torres Restrepo",
            hashed_password=hash_password(CAREGIVER_PASSWORD),
            is_active=True,
        )
        db.add(caregiver)
        db.flush()

        # ── Patient ───────────────────────────────────────────────────
        patient = ElderlyPatientModel(
            full_name="Rosa Gonzalez Torres",
            date_of_birth=date(1952, 6, 15),
            room_number="101-A",
            caregiver_id=caregiver.id,
            chronic_conditions=["diabetes_type2", "hypertension", "arthritis"],
            emergency_contact_name="Carlos Gonzalez",
            emergency_contact_phone="+57 300 123 4567",
            notes=(
                "Patient from Antioquia, Colombia. "
                "Requires meals before medication. "
                "Spanish speaker only. Mild cognitive impairment."
            ),
        )
        db.add(patient)
        db.flush()

        # ── Medications + historical doses (85% adherence simulation) ─
        now = datetime.now(UTC)
        total_doses_created = 0

        for med_data in MEDICATIONS:
            medication = MedicationModel(
                patient_id=patient.id,
                generic_name=med_data["generic_name"],
                brand_name=med_data["brand_name"],
                dose_mg=med_data["dose_mg"],
                frequency_hours=med_data["frequency_hours"],
                with_food=med_data["with_food"],
                current_stock_units=med_data["current_stock_units"],
                minimum_stock_units=med_data["minimum_stock_units"],
                expiration_date=date.today() + timedelta(days=med_data["days_until_expiry"]),
                is_active=True,
            )
            db.add(medication)
            db.flush()

            # Schedule 30 days of doses
            freq = med_data["frequency_hours"]
            total = (30 * 24) // freq
            doses = []
            for i in range(total):
                scheduled = now + timedelta(hours=i * freq - (30 * 24))  # start 30 days ago
                if scheduled < now:
                    # Past dose: 85% confirmed, 15% missed
                    status = DoseStatus.CONFIRMED.value if (i % 7 != 0) else DoseStatus.MISSED.value
                    taken_at = scheduled + timedelta(minutes=10) if status == DoseStatus.CONFIRMED.value else None
                else:
                    status = DoseStatus.PENDING.value
                    taken_at = None

                doses.append(ScheduledDoseModel(
                    medication_id=medication.id,
                    scheduled_for=scheduled,
                    status=status,
                    taken_at=taken_at,
                ))

            db.add_all(doses)
            total_doses_created += len(doses)

        db.commit()

        print("\nSeed completed successfully.")
        print("=" * 50)
        print(f"  Caregiver : {CAREGIVER_EMAIL}")
        print(f"  Password  : {CAREGIVER_PASSWORD}")
        print(f"  Patient   : {patient.full_name} (born {patient.date_of_birth})")
        print(f"  Medications: {len(MEDICATIONS)} enrolled")
        print(f"  Doses      : {total_doses_created} scheduled (30-day history)")
        print(f"  Adherence  : ~85% (1 in 7 doses missed)")
        print("=" * 50)

    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
