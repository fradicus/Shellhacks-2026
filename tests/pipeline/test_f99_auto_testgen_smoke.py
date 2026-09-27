from __future__ import annotations

import pytest

from testgen_smoke import km_to_miles, miles_to_km, overlap_days


def test_miles_to_km_zero() -> None:
    assert miles_to_km(0.0) == 0.0


def test_miles_to_km_positive() -> None:
    assert miles_to_km(1.0) == 1.609
    assert miles_to_km(25.0) == 40.234


def test_miles_to_km_negative_raises() -> None:
    with pytest.raises(ValueError, match="distance cannot be negative"):
        miles_to_km(-0.1)


def test_km_to_miles_zero() -> None:
    assert km_to_miles(0.0) == 0.0


def test_km_to_miles_positive() -> None:
    assert km_to_miles(1.609344) == 1.0
    assert km_to_miles(40.234) == 25.0


def test_km_to_miles_negative_raises() -> None:
    with pytest.raises(ValueError, match="distance cannot be negative"):
        km_to_miles(-1.0)


def test_overlap_days_disjoint_returns_zero() -> None:
    assert overlap_days(1, 5, 10, 15) == 0
    assert overlap_days(10, 15, 1, 5) == 0


def test_overlap_days_touching_endpoint() -> None:
    assert overlap_days(1, 5, 5, 10) == 1
    assert overlap_days(5, 10, 1, 5) == 1


def test_overlap_days_partial_overlap() -> None:
    assert overlap_days(1, 10, 5, 15) == 6
    assert overlap_days(5, 15, 1, 10) == 6


def test_overlap_days_contained_window() -> None:
    assert overlap_days(1, 10, 3, 7) == 5
    assert overlap_days(3, 7, 1, 10) == 5


def test_overlap_days_identical_windows() -> None:
    assert overlap_days(1, 5, 1, 5) == 5


def test_overlap_days_invalid_start_after_end_raises() -> None:
    with pytest.raises(ValueError, match="window start must not be after its end"):
        overlap_days(5, 2, 1, 10)

    with pytest.raises(ValueError, match="window start must not be after its end"):
        overlap_days(1, 10, 8, 4)
