"""Throwaway module for the Azure test-generation smoke run; never merged."""

from __future__ import annotations


def miles_to_km(miles: float) -> float:
    if miles < 0:
        raise ValueError("distance cannot be negative")
    return round(miles * 1.609344, 3)


def overlap_days(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    """Inclusive overlap, in days, of two [start, end] day-number windows; 0 if disjoint."""
    if a_start > a_end or b_start > b_end:
        raise ValueError("window start must not be after its end")
    return max(0, min(a_end, b_end) - max(a_start, b_start) + 1)
