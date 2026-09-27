from __future__ import annotations

import pytest

from testgen_smoke import miles_to_km, overlap_days


def test_miles_to_km_converts_zero() -> None:
    assert miles_to_km(0.0) == 0.0


def test_miles_to_km_converts_positive_value() -> None:
    assert miles_to_km(1.0) == 1.609


def test_miles_to_km_rounds_to_three_decimal_places() -> None:
    assert miles_to_km(25.0) == 40.234


def test_miles_to_km_raises_value_error_on_negative_distance() -> None:
    with pytest.raises(ValueError, match="distance cannot be negative"):
        miles_to_km(-1.0)


def test_overlap_days_returns_zero_when_windows_are_disjoint() -> None:
    assert overlap_days(1, 5, 10, 15) == 0


def test_overlap_days_single_day_contact_returns_one() -> None:
    assert overlap_days(1, 5, 5, 10) == 1


def test_overlap_days_partial_overlap() -> None:
    assert overlap_days(1, 10, 5, 15) == 6


def test_overlap_days_subset_window() -> None:
    assert overlap_days(1, 20, 5, 10) == 6


def test_overlap_days_identical_windows() -> None:
    assert overlap_days(3, 7, 3, 7) == 5


def test_overlap_days_raises_value_error_when_first_window_inverted() -> None:
    with pytest.raises(ValueError, match="window start must not be after its end"):
        overlap_days(5, 4, 1, 10)


def test_overlap_days_raises_value_error_when_second_window_inverted() -> None:
    with pytest.raises(ValueError, match="window start must not be after its end"):
        overlap_days(1, 10, 10, 9)
