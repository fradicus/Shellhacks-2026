// Self-check for csv.ts, plain JS so tsc (frozen config) skips it (no web test runner in this repo). Run: node web/app/api/export/csv.check.mjs
import assert from "node:assert/strict";
import { cell, toCsv } from "./csv.ts";

assert.equal(cell("=HYPERLINK(\"x\")"), `"'=HYPERLINK(""x"")"`);
assert.equal(cell("+1"), "'+1");
assert.equal(cell("-2+3"), "'-2+3");
assert.equal(cell("@SUM(A1)"), "'@SUM(A1)");
assert.equal(cell("\tcmd"), "'\tcmd");
assert.equal(cell(-81.2), "-81.2"); // numbers are data, never prefixed
assert.equal(cell("Okatie, Bluffton"), '"Okatie, Bluffton"');
assert.equal(cell(null), "");
assert.equal(cell(Number.NaN), "");
assert.equal(toCsv(["a", "b"], [["=x", 1]]), "a,b\r\n'=x,1\r\n");
console.log("csv.check: ok");
