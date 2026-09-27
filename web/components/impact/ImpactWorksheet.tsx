"use client";

import { useState } from "react";
import { Button } from "@/components/ui";
import { calculate, emptyInputs, milestoneGap, money, SCENARIOS, type Inputs, type ScenarioName } from "./model";
import s from "./impact.module.css";

const FIELDS: { key: keyof Inputs; label: string; help: string; money: boolean }[] = [
  { key: "mobilizations", label: "Mobilizations avoided", help: "Complete moves you assume can be avoided. Use the same scope as the quote below.", money: false },
  { key: "unitCost", label: "Quoted cost per mobilization · USD", help: "Freight and mobilization costs actually avoided per move; exclude costs still incurred.", money: true },
  { key: "coordinationCost", label: "Additional coordination cost · USD", help: "Total extra inter-site freight, handling, cleaning, inspection and administration. Exclude holding costs below.", money: true },
  { key: "idleDays", label: "Extra idle rental days", help: "Additional chargeable days while holding the package between jobs; check minimum rental terms.", money: false },
  { key: "dailyRate", label: "Daily holding cost · USD", help: "Quoted total per day for the whole mat or equipment package, including applicable storage costs.", money: true },
];
const CHECKS = [
  "Confirm actual release and need dates with both project managers.",
  "Confirm rental terms, transfer permission and equipment availability.",
  "Confirm freight, handling and minimum rental charges with the supplier.",
  "Confirm mat condition, site suitability and inspection/cleaning requirements.",
];

export function ImpactWorksheet({ pairLabel }: { pairLabel: string | null }) {
  const [inputs, setInputs] = useState<Record<ScenarioName, Inputs>>(() => ({ Low: emptyInputs(), Base: emptyInputs(), High: emptyInputs() }));
  const [holding, setHolding] = useState(false);
  const [resource, setResource] = useState("");
  const [notes, setNotes] = useState("");
  const [checks, setChecks] = useState<boolean[]>(CHECKS.map(() => false));
  const [dates, setDates] = useState({ a: "", b: "" });
  const gap = milestoneGap(dates.a, dates.b);
  const outcomes = SCENARIOS.map((name) => calculate(inputs[name], holding));
  const nets = outcomes.map((outcome) => outcome.result?.net);
  const unordered = nets.every((value) => value !== undefined) && (nets[0]! > nets[1]! || nets[1]! > nets[2]!);

  function reset() {
    setInputs({ Low: emptyInputs(), Base: emptyInputs(), High: emptyInputs() });
    setHolding(false); setResource(""); setNotes(""); setDates({ a: "", b: "" });
    setChecks(CHECKS.map(() => false));
  }

  return (
    <>
      <section className={s.section} aria-labelledby="worksheet-heading">
        <div className={s.sectionHead}>
          <div><span className="eyebrow">02 / User scenario</span><h2 id="worksheet-heading">Is another mobilization worth avoiding?</h2></div>
          <div className={`no-print ${s.actions}`}>
            <Button onClick={reset}>Reset worksheet</Button>
            <Button variant="primary" onClick={() => window.print()}>Print / save PDF</Button>
          </div>
        </div>
        <p className={s.muted}>Compare avoided mobilization costs against the extra cost of moving and holding a package between jobs.
          Enter your own quotes and assumptions. Blank means unknown; enter 0 when a cost does not apply.</p>
        <label className={s.resource}>Mat or equipment package
          <input value={resource} onChange={(event) => setResource(event.target.value)} maxLength={240} placeholder="Describe the package and what one mobilization includes" />
        </label>
        <p className={s.printNotes}>Package description: {resource || "None entered."}</p>
        <label className={`${s.toggle} no-print`}>
          <input type="checkbox" checked={holding} onChange={(event) => setHolding(event.target.checked)} />
          Include extra idle rental / holding costs
        </label>
        <p className={s.formula}>Avoided mobilizations × quoted cost per move − additional coordination cost{holding ? " − (extra idle days × daily holding cost)" : ""}</p>
        {!holding && <p className={s.muted}>Holding costs are excluded. Enable them if keeping the package between jobs creates additional charges.</p>}
        {unordered && <p className={s.warning} role="status">Your modeled results are not ordered low → base → high. Check the assumptions; they have not been rearranged.</p>}

        <div className={s.scenarios}>
          {SCENARIOS.map((name, index) => {
            const { result, errors, missing, overflow } = outcomes[index];
            return (
              <section key={name} className={s.scenario} aria-labelledby={`${name}-heading`} data-base={name === "Base"}>
                <header className={s.scenarioHead}><h3 id={`${name}-heading`}>{name}</h3><span className="eyebrow">User assumptions</span></header>
                <div className={s.result} aria-live="polite" aria-atomic="true">
                  <span className={s.muted}>Modeled potential · USD</span>
                  <strong data-negative={result !== null && result.net < 0} data-testid={`result-${name}`}>{result ? money(result.net) : "Not calculated"}</strong>
                  <span>{result ? (result.net < 0 ? "Added costs exceed avoided costs." : result.net === 0 ? "Break-even under these assumptions." : "Positive under these assumptions.") : "Complete the inputs below."}</span>
                </div>
                <div className={s.fields}>
                  {FIELDS.filter((field) => holding || (field.key !== "idleDays" && field.key !== "dailyRate")).map((field) => {
                    const id = `${name}-${field.key}`;
                    return (
                      <div className={s.field} key={field.key}>
                        <label htmlFor={id}>{field.label}</label>
                        <input id={id} inputMode={field.money ? "decimal" : "numeric"} type="text" autoComplete="off" maxLength={24}
                          value={inputs[name][field.key]} aria-invalid={!!errors[field.key]} aria-describedby={`${id}-help${errors[field.key] ? ` ${id}-error` : ""}`}
                          onChange={(event) => setInputs((previous) => ({ ...previous, [name]: { ...previous[name], [field.key]: event.target.value } }))} />
                        <small id={`${id}-help`}>{field.help}</small>
                        {errors[field.key] && <span id={`${id}-error`} className={s.error}>{errors[field.key]}</span>}
                      </div>
                    );
                  })}
                </div>
                <div className={s.breakdown}>
                  {result ? <>
                    <dl><div><dt>Avoided mobilization cost</dt><dd>{money(result.avoided)}</dd></div>
                      <div><dt>Additional coordination</dt><dd>{money(result.coordination)}</dd></div>
                      {holding && <div><dt>Extra holding cost</dt><dd>{money(result.carrying)}</dd></div>}
                    </dl>
                    {result.maxIdleDays !== null && <p><strong>{result.maxIdleDays.toLocaleString("en-US")} idle days</strong> maximum before modeled potential becomes negative, holding other inputs fixed.</p>}
                  </> : <p>{overflow ? "The combined amount is too large to calculate safely. Reduce the inputs." : Object.keys(errors).length ? "Correct the highlighted inputs to calculate." : `${missing} required inputs remaining.`}</p>}
                </div>
              </section>
            );
          })}
        </div>
        <p className={s.disclosure}><strong>Modeled potential, not realized savings.</strong> These scenarios are user assumptions, not bids, supplier rates or predictions. Only costs that actually disappear belong in the avoided amount.</p>
      </section>

      <section className={s.section} aria-labelledby="dates-heading">
        <span className="eyebrow">03 / Milestone assumption</span>
        <h2 id="dates-heading">What if the filed milestones moved?</h2>
        <p className={s.muted}>Enter two hypothetical in-service dates to compare their gap. They do not change the published records or calculate rental days. In-service milestones do not establish construction or equipment availability.</p>
        <div className={s.dates}>
          <label>Assumed in-service date · A<input aria-label="Assumed in-service date A" type="date" min="0001-01-01" max="9999-12-31" value={dates.a} onChange={(event) => setDates({ ...dates, a: event.target.value })} /></label>
          <label>Assumed in-service date · B<input aria-label="Assumed in-service date B" type="date" min="0001-01-01" max="9999-12-31" value={dates.b} onChange={(event) => setDates({ ...dates, b: event.target.value })} /></label>
          <div className={s.dateResult} aria-live="polite"><span className="eyebrow">Assumed gap</span><strong>{gap === null ? "Unknown" : `${gap.toLocaleString("en-US")} days`}</strong></div>
          <Button className="no-print" onClick={() => setDates({ a: "", b: "" })}>Reset dates</Button>
        </div>
      </section>

      <section className={s.section} aria-labelledby="handoff-heading">
        <span className="eyebrow">04 / Prepare the conversation</span>
        <h2 id="handoff-heading">Bring the assumptions with you.</h2>
        <p className={s.muted}>{pairLabel ? `Scenario context: ${pairLabel}.` : "Standalone scenario: no project pair attached."} Your entries stay in this page and are cleared on reload. Print or save a PDF to keep a copy.</p>
        <label className={s.resource}>Quote references and open questions
          <textarea rows={4} maxLength={5000} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Supplier / estimator, quote date, scope and exclusions. Who needs to confirm the assumptions?" />
        </label>
        <p className={s.printNotes}>Quote references and open questions: {notes || "None entered."}</p>
        <fieldset className={s.checklist}><legend>Confirm before treating this as a coordination opportunity</legend>
          {CHECKS.map((check, index) => <label key={check}><input type="checkbox" checked={checks[index]} onChange={(event) => setChecks((previous) => previous.map((value, i) => i === index ? event.target.checked : value))} /><span>{check}</span><small className={s.printOnly}>{checks[index] ? "Marked confirmed by user" : "Open"}</small></label>)}
        </fieldset>
        <p className={s.muted}>For timber mats, ask about soil conditions, deployment duration and inspection requirements. Pair project centers can open Field planning for survey pH and water context; this worksheet still does not estimate decay, select a safe mat material, or infer soil suitability.</p>
      </section>
    </>
  );
}
