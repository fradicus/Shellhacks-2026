import assert from "node:assert/strict";
import test from "node:test";
import type { Match, Project, Brief } from "../../../web/lib/types.ts";
import { pairCsv, pairCsvFilename } from "../../../web/components/pair/pairCsv.ts";

const match = { _id: "DESC:a|GPC:b", a: "DESC:a", b: "GPC:b", view: "historical", rank: 2,
  review_state: "rejected", band: 0, distance_mi: 3.123456789, time_gap_days: null,
  analysis_date: "2026-09-26", rule_version: "rule-1", rank_version: "rank-1" } as Match;
const project = { _id: "DESC:a@source-v2", project_key: "DESC:a", utility: "DESC", native_id: "a", name: "A",
  owner_code: "DESC", source: { source_id: "source-v2", page: 7 },
  in_service: { raw: "2027", date: null, precision: "year" }, center: { lat: 32, lon: -81, basis: "one" },
  location_confidence: "low", active: true } as Project;

function parse(csv: string) {
  const rows: string[][] = [[]]; let cell = "", quoted = false;
  for (let i = 0; i < csv.length; i++) {
    const c = csv[i];
    if (c === '"') {
      if (quoted && csv[i + 1] === '"') { cell += '"'; i++; } else quoted = !quoted;
    } else if (!quoted && c === ',') { rows.at(-1)!.push(cell); cell = ""; }
    else if (!quoted && c === '\r' && csv[i + 1] === '\n') { rows.at(-1)!.push(cell); cell = ""; rows.push([]); i++; }
    else cell += c;
  }
  return rows.filter((row) => row.length);
}

test("selected-pair CSV has exactly one record and retains source versions, precision and uncertainty", () => {
  const [headers, values, ...extra] = parse(pairCsv(match, project, null, null));
  const row = Object.fromEntries(headers.map((h, i) => [h, values[i]]));
  assert.equal(extra.length, 0);
  assert.equal(headers.length, values.length);
  assert.equal(row.pair_id, match._id);
  assert.equal(row.a_project_version_id, project._id);
  assert.equal(row.a_source_id, "source-v2");
  assert.equal(row.a_source_page, "7");
  assert.equal(row.distance_mi_unrounded, "3.123456789");
  assert.equal(row.a_center_lon, "-81");
  assert.equal(row.review_state, "rejected");
  assert.equal(row.a_in_service_precision, "year");
  assert.equal(row.a_in_service_date, "");
  assert.equal(row.b_project_key, "GPC:b");
  assert.equal(row.b_project_version_id, "");
  assert.equal(row.time_gap_days, "unknown");
  assert.equal(row.gemini_brief, "unavailable");
  assert.ok(!headers.includes("publication_id"));
});

test("CSV quotes commas/newlines/quotes and neutralizes spreadsheet formula text", () => {
  for (const name of ['=HYPERLINK("https://example.invalid", "x")', '+formula', '-formula', '@formula', '\tformula', '\rformula', 'Public, "name"\nnext line']) {
    const [headers, values] = parse(pairCsv(match, { ...project, name }, null, null));
    assert.equal(headers.length, values.length);
    assert.equal(values[headers.indexOf("a_name")], /^[=+\-@\t\r]/.test(name) ? `'${name}` : name);
  }
});

test("stored model provenance stays labeled and unsafe filenames are normalized", () => {
  const brief = { model: "gemini-test", prompt_version: "p1", generated_at: "2026-09-26T00:00:00Z" } as Brief;
  const [headers, values] = parse(pairCsv(match, project, null, brief));
  assert.equal(values[headers.indexOf("gemini_model")], "gemini-test");
  assert.equal(values[headers.indexOf("gemini_brief")], "validated");
  assert.equal(pairCsvFilename('../bad:name|line\r\n"'), "gridbridge-pair-..-bad-name-line.csv");
});
