import assert from "node:assert/strict";
import test from "node:test";
import {
  filterVerifiedUtilities,
  InvalidVerifiedQuery,
  parseVerifiedParams,
  rejectVerifiedCoverageParams,
  validateVerifiedGeography,
} from "../../../web/lib/verified/filters.ts";
import type { VerifiedUtilityRecord } from "../../../web/lib/verified/types.ts";

const geography = {
  states: [{ state_fips: "13" }, { state_fips: "25" }],
  counties: [{ county_geoid: "13001", state_fips: "13" }, { county_geoid: "25001", state_fips: "25" }],
};

const utilities: VerifiedUtilityRecord[] = [
  { id: "u-1", eia_utility_id: "17", data_year: 2024, name: "Alpha Power", state_fips: ["13"], county_geoids: ["13001"], source_ids: ["eia"], validation_status: "accepted", limitations: [] },
  { id: "u-2", eia_utility_id: "170", data_year: 2024, name: "Literal .* Utility", state_fips: ["25"], county_geoids: [], source_ids: ["eia"], validation_status: "needs_review", limitations: ["unresolved"] },
];

test("strict query parsing rejects duplicates, unknowns, unparented county and unsafe bounds", () => {
  assert.throws(() => parseVerifiedParams(new URLSearchParams("state=13&state=25")), InvalidVerifiedQuery);
  assert.throws(() => parseVerifiedParams(new URLSearchParams("owner=x")), /unknown/);
  assert.throws(() => parseVerifiedParams(new URLSearchParams("county=13001")), /requires/);
  assert.throws(() => parseVerifiedParams(new URLSearchParams("state=13&limit=101")), /<=100|less than or equal/);
  assert.throws(() => parseVerifiedParams(new URLSearchParams(`q=${"x".repeat(121)}`)), /too big|less than or equal/i);
});

test("coverage rejects every query parameter", () => {
  assert.doesNotThrow(() => rejectVerifiedCoverageParams(new URLSearchParams()));
  assert.throws(() => rejectVerifiedCoverageParams(new URLSearchParams("state=13")), InvalidVerifiedQuery);
});

test("state and county filters validate known parentage", () => {
  assert.equal(validateVerifiedGeography(parseVerifiedParams(new URLSearchParams("state=13&county=13001")), geography), null);
  assert.equal(validateVerifiedGeography(parseVerifiedParams(new URLSearchParams("state=25&county=13001")), geography), "county is not in the selected state");
  assert.equal(validateVerifiedGeography(parseVerifiedParams(new URLSearchParams("state=99")), geography), "unknown state FIPS");
});

test("search is bounded literal utility ID or name matching", () => {
  assert.deepEqual(filterVerifiedUtilities(utilities, parseVerifiedParams(new URLSearchParams("q=.*"))).map((item) => item.id), ["u-2"]);
  assert.deepEqual(filterVerifiedUtilities(utilities, parseVerifiedParams(new URLSearchParams("q=17"))).map((item) => item.id), ["u-1", "u-2"]);
  assert.deepEqual(filterVerifiedUtilities(utilities, parseVerifiedParams(new URLSearchParams("state=13&county=13001"))).map((item) => item.id), ["u-1"]);
});
