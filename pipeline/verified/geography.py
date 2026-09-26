from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

ENTITY_SUFFIXES = (
    "city and borough",
    "county city",
    "census area",
    "municipality",
    "municipio",
    "borough",
    "parish",
    "county",
)


def normalized_name(value: str) -> str:
    ascii_value = "".join(char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def alias_name(value: str) -> str:
    name = normalized_name(value)
    for suffix in ENTITY_SUFFIXES:
        if name.endswith(f" {suffix}"):
            name = name[: -(len(suffix) + 1)]
            break
    return name.replace(" ", "")


@dataclass(frozen=True)
class CountyMatch:
    status: str
    county_geoid: str | None
    candidates: tuple[str, ...]
    method: str | None


class GeographyIndex:
    def __init__(self, geography: dict[str, Any]):
        self.states_by_usps = {item["usps"]: item for item in geography["states"]}
        self.states_by_fips = {item["state_fips"]: item for item in geography["states"]}
        self.counties_by_geoid = {item["county_geoid"]: item for item in geography["counties"]}
        self._exact: dict[tuple[str, str], set[str]] = {}
        self._aliases: dict[tuple[str, str], set[str]] = {}
        for item in geography["counties"]:
            usps = item["state_usps"]
            for name in {item["name"], item["full_name"]}:
                self._exact.setdefault((usps, normalized_name(name)), set()).add(item["county_geoid"])
                self._aliases.setdefault((usps, alias_name(name)), set()).add(item["county_geoid"])

    def state_fips(self, usps: str) -> str | None:
        state = self.states_by_usps.get(usps.strip().upper())
        return state["state_fips"] if state else None

    def match_county(self, usps: str, raw_name: str) -> CountyMatch:
        state = usps.strip().upper()
        exact = tuple(sorted(self._exact.get((state, normalized_name(raw_name)), set())))
        if len(exact) == 1:
            return CountyMatch("accepted", exact[0], exact, "census_name_exact")
        if len(exact) > 1:
            return CountyMatch("conflicting", None, exact, "census_name_exact")
        aliases = tuple(sorted(self._aliases.get((state, alias_name(raw_name)), set())))
        if len(aliases) == 1:
            return CountyMatch("accepted", aliases[0], aliases, "census_name_alias")
        if len(aliases) > 1:
            return CountyMatch("conflicting", None, aliases, "census_name_alias")
        return CountyMatch("unresolved", None, (), None)
