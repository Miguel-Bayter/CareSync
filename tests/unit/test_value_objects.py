"""Unit tests for domain value objects."""

import pytest

from app.domain.value_objects import AdherenceRate, CriticalStockReport


class TestAdherenceRate:
    def test_adherence_percentage_normal(self) -> None:
        vo = AdherenceRate(
            medication_id="med-1",
            generic_name="Aspirin",
            confirmed_count=18,
            missed_count=2,
            total_scheduled=20,
        )
        assert vo.adherence_percentage == 90.0

    def test_adherence_percentage_zero_total(self) -> None:
        vo = AdherenceRate(
            medication_id="med-1",
            generic_name="Aspirin",
            confirmed_count=0,
            missed_count=0,
            total_scheduled=0,
        )
        assert vo.adherence_percentage == 0.0

    def test_adherence_percentage_perfect(self) -> None:
        vo = AdherenceRate(
            medication_id="med-2",
            generic_name="Ibuprofen",
            confirmed_count=30,
            missed_count=0,
            total_scheduled=30,
        )
        assert vo.adherence_percentage == 100.0

    def test_adherence_percentage_zero_confirmed(self) -> None:
        vo = AdherenceRate(
            medication_id="med-3",
            generic_name="Metformin",
            confirmed_count=0,
            missed_count=10,
            total_scheduled=10,
        )
        assert vo.adherence_percentage == 0.0

    def test_adherence_percentage_rounds_to_two_decimals(self) -> None:
        # 1/3 ≈ 33.33%
        vo = AdherenceRate(
            medication_id="med-4",
            generic_name="Lisinopril",
            confirmed_count=1,
            missed_count=2,
            total_scheduled=3,
        )
        assert vo.adherence_percentage == 33.33

    def test_equality_by_value(self) -> None:
        a = AdherenceRate("m", "Drug", 5, 5, 10)
        b = AdherenceRate("m", "Drug", 5, 5, 10)
        assert a == b

    def test_immutable(self) -> None:
        vo = AdherenceRate("m", "Drug", 5, 5, 10)
        with pytest.raises((AttributeError, TypeError)):
            vo.confirmed_count = 99  # type: ignore[misc]


class TestCriticalStockReport:
    def test_fields_stored(self) -> None:
        report = CriticalStockReport(
            medication_id="med-1",
            generic_name="Aspirin",
            current_stock_units=5,
            minimum_stock_units=10,
            days_until_expiration=3,
            is_expired=False,
        )
        assert report.medication_id == "med-1"
        assert report.generic_name == "Aspirin"
        assert report.current_stock_units == 5
        assert report.minimum_stock_units == 10
        assert report.days_until_expiration == 3
        assert report.is_expired is False

    def test_expired_flag(self) -> None:
        report = CriticalStockReport(
            medication_id="med-2",
            generic_name="Expired Drug",
            current_stock_units=100,
            minimum_stock_units=10,
            days_until_expiration=-5,
            is_expired=True,
        )
        assert report.is_expired is True

    def test_equality_by_value(self) -> None:
        a = CriticalStockReport("m", "Drug", 5, 10, 3, False)
        b = CriticalStockReport("m", "Drug", 5, 10, 3, False)
        assert a == b

    def test_immutable(self) -> None:
        report = CriticalStockReport("m", "Drug", 5, 10, 3, False)
        with pytest.raises((AttributeError, TypeError)):
            report.current_stock_units = 999  # type: ignore[misc]
