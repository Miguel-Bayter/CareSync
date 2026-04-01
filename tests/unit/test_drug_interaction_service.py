"""Unit tests for DrugInteractionService."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.services.drug_interaction_service import (
    DrugInteractionService,
    _fetch_interactions_from_fda,
)


def _make_medication(name: str = "metformin") -> MagicMock:
    med = MagicMock()
    med.id = uuid4()
    med.generic_name = name
    return med


class TestCheckPatientDrugInteractions:
    def test_returns_empty_list_when_patient_has_no_medications(self) -> None:
        repo = MagicMock()
        repo.find_all_by_patient.return_value = []
        service = DrugInteractionService(medication_repo=repo)

        result = service.check_patient_drug_interactions(uuid4())

        assert result == []

    def test_returns_interaction_report_when_fda_has_data(self) -> None:
        repo = MagicMock()
        repo.find_all_by_patient.return_value = [_make_medication("metformin")]
        service = DrugInteractionService(medication_repo=repo)

        with patch(
            "app.services.drug_interaction_service._fetch_interactions_from_fda",
            return_value="May cause lactic acidosis when combined with alcohol.",
        ):
            result = service.check_patient_drug_interactions(uuid4())

        assert len(result) == 1
        assert result[0].medication_name == "metformin"
        assert "lactic acidosis" in result[0].interaction_text

    def test_skips_medication_when_no_fda_interaction_data(self) -> None:
        repo = MagicMock()
        repo.find_all_by_patient.return_value = [
            _make_medication("metformin"),
            _make_medication("unknowndrug"),
        ]
        service = DrugInteractionService(medication_repo=repo)

        def _selective(name: str) -> str | None:
            return "Interaction text" if name == "metformin" else None

        with patch(
            "app.services.drug_interaction_service._fetch_interactions_from_fda",
            side_effect=_selective,
        ):
            result = service.check_patient_drug_interactions(uuid4())

        assert len(result) == 1
        assert result[0].medication_name == "metformin"

    def test_returns_empty_when_all_medications_lack_fda_data(self) -> None:
        repo = MagicMock()
        repo.find_all_by_patient.return_value = [_make_medication("obscuredrug")]
        service = DrugInteractionService(medication_repo=repo)

        with patch(
            "app.services.drug_interaction_service._fetch_interactions_from_fda",
            return_value=None,
        ):
            result = service.check_patient_drug_interactions(uuid4())

        assert result == []

    def test_returns_multiple_reports_for_multiple_medications(self) -> None:
        repo = MagicMock()
        repo.find_all_by_patient.return_value = [
            _make_medication("metformin"),
            _make_medication("losartan"),
        ]
        service = DrugInteractionService(medication_repo=repo)

        with patch(
            "app.services.drug_interaction_service._fetch_interactions_from_fda",
            return_value="Some interaction.",
        ):
            result = service.check_patient_drug_interactions(uuid4())

        assert len(result) == 2
        names = [r.medication_name for r in result]
        assert "metformin" in names
        assert "losartan" in names


class TestFetchInteractionsFromFda:
    """Tests for the module-level cached function that calls OpenFDA."""

    @pytest.fixture(autouse=True)
    def clear_lru_cache(self):
        """Clear lru_cache before each test to prevent cross-test caching."""
        _fetch_interactions_from_fda.cache_clear()
        yield
        _fetch_interactions_from_fda.cache_clear()

    def test_returns_interaction_text_on_successful_response(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"drug_interactions": ["May cause lactic acidosis."]}]
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            result = _fetch_interactions_from_fda("metformin_test_ok")

        assert result == "May cause lactic acidosis."

    def test_returns_none_when_no_results(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            result = _fetch_interactions_from_fda("nodrug_test_empty")

        assert result is None

    def test_returns_none_when_result_has_no_drug_interactions_field(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"other_field": "value"}]}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            result = _fetch_interactions_from_fda("nodrug_test_no_interactions")

        assert result is None

    def test_returns_none_on_non_200_status(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            result = _fetch_interactions_from_fda("nodrug_test_404")

        assert result is None

    def test_returns_none_on_http_error(self) -> None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        with patch("httpx.Client", return_value=mock_client):
            result = _fetch_interactions_from_fda("nodrug_test_timeout")

        assert result is None
