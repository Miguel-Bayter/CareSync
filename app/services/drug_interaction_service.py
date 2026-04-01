"""DrugInteractionService — OpenFDA integration with in-memory cache."""

import functools
from uuid import UUID

import httpx

from app.repositories.medication_repo import MedicationRepository
from app.schemas.medication import DrugInteractionReport

_FDA_URL = "https://api.fda.gov/drug/label.json"


@functools.lru_cache(maxsize=100)
def _fetch_interactions_from_fda(generic_name: str) -> str | None:
    """Fetch drug interaction text from OpenFDA. Result is cached in memory.

    Module-level function (not instance method) so lru_cache works correctly —
    instance methods hold a reference to self and prevent garbage collection.

    Args:
        generic_name: Lowercase generic drug name to search.

    Returns:
        First interaction text found, or None if not available.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _FDA_URL,
                params={
                    "search": f'openfda.generic_name:"{generic_name}"',
                    "limit": 1,
                },
            )
            if response.status_code == 200:
                results = response.json().get("results", [])
                if results:
                    interactions = results[0].get("drug_interactions", [])
                    return interactions[0] if interactions else None
    except (httpx.HTTPError, KeyError, IndexError):
        return None
    return None


class DrugInteractionService:
    """Checks all of a patient's medications against the OpenFDA drug label database.

    Results are cached in memory via functools.lru_cache — first call per drug
    hits the network (~2-3s), subsequent calls are instant. Cache lives for the
    duration of the process (resets on redeploy).
    """

    def __init__(self, medication_repo: MedicationRepository) -> None:
        self.medication_repo = medication_repo

    def check_patient_drug_interactions(self, patient_id: UUID) -> list[DrugInteractionReport]:
        """Return interaction reports for all active medications of a patient.

        Args:
            patient_id: UUID of the patient.

        Returns:
            List of DrugInteractionReport — only medications with known
            interactions are included (medications with no FDA data are skipped).
        """
        medications = self.medication_repo.find_all_by_patient(patient_id)
        reports = []
        for medication in medications:
            text = _fetch_interactions_from_fda(medication.generic_name.lower())
            if text:
                reports.append(
                    DrugInteractionReport(
                        medication_name=medication.generic_name,
                        interaction_text=text,
                    )
                )
        return reports
