import assert from "node:assert/strict";
import { test } from "node:test";
import { stemFrom } from "../../../web/components/history/historyLayer.ts";

test("the lit stem starts at the earliest documented date, not the axis ground", () => {
  assert.equal(stemFrom([{ z0: 21.3 }, { z0: 19.8 }, { z0: 20.5 }]), 19.8);
  assert.equal(stemFrom([{ z0: 0 }]), 0);
  assert.equal(stemFrom([]), Infinity); // nothing documented: no stem at all
});
