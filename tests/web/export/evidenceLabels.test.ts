import assert from "node:assert/strict";
import test from "node:test";
import type { Project } from "../../../web/lib/types.ts";
import { filedOwnerLabel, pairDescription } from "../../../web/components/pair/evidenceLabels.ts";

test("Georgia filing labels preserve raw SAV/GTC/GPC codes without asserting mapped ownership", () => {
  for (const owner_code of ["SAV", "GTC", "GPC"]) {
    const label = filedOwnerLabel({ utility: "GPC", owner_code } as Project);
    assert.equal(label, `Filed owner code ${owner_code} · Georgia filing`);
    assert.ok(!label?.includes("Georgia Power"));
  }
  assert.equal(filedOwnerLabel({ utility: "DESC", owner_code: "DESC" } as Project), null);
  assert.equal(filedOwnerLabel(null), null);
});

test("only confirmed pairs are described as reviewed leads", () => {
  assert.match(pairDescription("rejected"), /rejected pair retained for audit/);
  assert.match(pairDescription("rejected"), /not a validated coordination opportunity/);
  assert.match(pairDescription("needs_review"), /still needs evidence review/);
  assert.match(pairDescription(undefined), /still needs evidence review/);
  assert.match(pairDescription("confirmed"), /reviewed coordination lead/);
});
