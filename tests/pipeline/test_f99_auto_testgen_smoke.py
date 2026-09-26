from __future__ import annotations

import pytest

from testgen_smoke import miles_to_km, overlap_days


def test_miles_to_km_converts_zero_and_positive_distances():
    assert miles_to_km(0.0) == 0.0
    assert miles_to_km(1.0) == 1.609
    assert miles_to_km(10.0) == 16.093
    assert miles_to_km(25.0) == 40.234


def test_miles_to_km_raises_on_negative_distance():
    with pytest.raises(ValueError, match="distance cannot be negative"):
        miles_to_km(-0.1)


def test_overlap_days_returns_zero_for_disjoint_windows():
    assert overlap_days(1, 5, 6, 10) == 0
    assert overlap_days(10, 20, 1, 9) == 0


def test_overlap_days_calculates_inclusive_intersection():
    assert overlap_days(1, 5, 3, 8) == 3
    assert overlap_days(1, 5, 5, 10) == 1
    assert overlap_days(2, 4, 1, 10) == 3
    assert overlap_days(1, 5, 1, 5) == 5


def test_overlap_days_raises_when_start_exceeds_end():
    with pytest.raises(ValueError, match="window start must not be after its end"):
        overlap_days(5, 4, 1, 10)

    with pytest.raises(ValueError, match="window start must not be after its end"):
        overlap_days(1, 10, 6, 5)
