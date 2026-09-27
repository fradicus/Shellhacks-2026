"use client";

import { useMemo, useState } from "react";
import type { Envelope, RoadworkData, RouteResponse, SiteResponse, WeatherData } from "@/lib/operations/contracts";
import {
  applyFactorRates,
  deriveRouteFactors,
  money,
  type FactorPresence,
  type FactorRateInput,
} from "./factors";
import styles from "./operations.module.css";

type Props = {
  site: SiteResponse | null;
  route: RouteResponse | null;
  weather: Envelope<WeatherData> | null;
  roadwork: Envelope<RoadworkData> | null;
  siteOutdated: boolean;
  routeOutdated: boolean;
  onOpenPlanning: () => void;
};

function presenceLabel(presence: FactorPresence): string {
  return presence.replaceAll("_", " ");
}

export function FactorsBoard({ site, route, weather, roadwork, siteOutdated, routeOutdated, onOpenPlanning }: Props) {
  const evidence = useMemo(
    () => deriveRouteFactors({ site, route, weather, roadwork }),
    [site, route, weather, roadwork],
  );
  const [rates, setRates] = useState<Record<string, FactorRateInput>>({});

  const { factors, totals } = useMemo(() => applyFactorRates(evidence, rates), [evidence, rates]);

  function setRate(id: string, patch: Partial<FactorRateInput>) {
    setRates((current) => ({
      ...current,
      [id]: { time_minutes: current[id]?.time_minutes ?? "", cost_usd: current[id]?.cost_usd ?? "", ...patch },
    }));
  }

  function resetRates() {
    setRates({});
  }

  return (
    <section className={styles.factorsBoard} aria-labelledby="factors-heading">
      <div className={styles.factorsIntro}>
        <div>
          <p className="eyebrow">Route factors pipeline</p>
          <h2 id="factors-heading">What adds time and cost on this route</h2>
          <p>
            Evidence rows come from the worksite and truck-route checks on Planning. Enter your own minutes and dollars;
            blanks stay unknown. GridBridge never invents rates or promised savings.
          </p>
        </div>
        <div className={styles.factorsActions}>
          <button type="button" className={styles.secondary} onClick={onOpenPlanning}>Back to Planning</button>
          <button type="button" className={styles.secondary} onClick={resetRates}>Reset rates</button>
        </div>
      </div>

      {(siteOutdated || routeOutdated) && (
        <p className={styles.inlineWarning} role="status">
          Planning inputs changed. Factor evidence below still reflects the last checked worksite or route until you re-check it.
        </p>
      )}

      {!site && (
        <div className={styles.blankSlate}>
          <span>+</span>
          <h3>Check a worksite first</h3>
          <p>Open Planning, confirm a point, then optionally run a truck route. Factors attach to that route evidence.</p>
          <button type="button" className={styles.primary} onClick={onOpenPlanning}>Open Planning</button>
        </div>
      )}

      {site && (
        <>
          <div className={styles.factorsTotals} aria-live="polite">
            <div>
              <span className="eyebrow">Present factors</span>
              <strong>{totals.present_count}</strong>
            </div>
            <div>
              <span className="eyebrow">Added time</span>
              <strong>{totals.time_minutes == null ? "Unknown" : `${totals.time_minutes.toLocaleString("en-US")} min`}</strong>
              <span>Baseline travel seeds when a route exists; other minutes need your rates.</span>
            </div>
            <div>
              <span className="eyebrow">Added cost</span>
              <strong>{totals.cost_cents == null ? "Unknown" : money(totals.cost_cents)}</strong>
              <span>Complete cost inputs on every time/cost factor you want in the total.</span>
            </div>
          </div>

          <div className={styles.factorsTableWrap}>
            <table className={styles.factorsTable}>
              <caption className={styles.srOnly}>Route factors with optional user time and cost rates</caption>
              <thead>
                <tr>
                  <th scope="col">Factor</th>
                  <th scope="col">Evidence</th>
                  <th scope="col">Added time (min)</th>
                  <th scope="col">Added cost (USD)</th>
                </tr>
              </thead>
              <tbody>
                {factors.map((factor) => (
                  <tr key={factor.id} data-presence={factor.presence}>
                    <th scope="row">
                      <div className={styles.factorLabel}>
                        <strong>{factor.label}</strong>
                        <span className={`${styles.badge} ${factor.presence === "present" ? styles.warn : factor.presence === "absent" ? styles.ok : styles.unknown}`}>
                          {presenceLabel(factor.presence)}
                        </span>
                      </div>
                      <span className={styles.small}>{factor.source}{factor.provider_status ? ` · ${factor.provider_status}` : ""}</span>
                    </th>
                    <td>
                      <p className={styles.factorEvidence}>{factor.evidence}</p>
                      {factor.known_time_minutes != null && (
                        <p className={styles.small}>Provider travel {factor.known_time_minutes} min used as baseline when time is left blank.</p>
                      )}
                    </td>
                    <td>
                      <label className={styles.factorRate}>
                        <span className={styles.srOnly}>Added minutes for {factor.label}</span>
                        <input
                          inputMode="numeric"
                          autoComplete="off"
                          maxLength={8}
                          placeholder={factor.known_time_minutes != null ? String(factor.known_time_minutes) : "—"}
                          value={rates[factor.id]?.time_minutes ?? ""}
                          aria-invalid={!!factor.time_error}
                          onChange={(event) => setRate(factor.id, { time_minutes: event.target.value })}
                        />
                      </label>
                      {factor.time_error && <span className={styles.error}>{factor.time_error}</span>}
                      {!factor.time_error && factor.time_minutes_add != null && (
                        <span className={styles.small}>{factor.time_minutes_add} min in total</span>
                      )}
                    </td>
                    <td>
                      <label className={styles.factorRate}>
                        <span className={styles.srOnly}>Added cost for {factor.label}</span>
                        <input
                          inputMode="decimal"
                          autoComplete="off"
                          maxLength={16}
                          placeholder="—"
                          value={rates[factor.id]?.cost_usd ?? ""}
                          aria-invalid={!!factor.cost_error}
                          onChange={(event) => setRate(factor.id, { cost_usd: event.target.value })}
                        />
                      </label>
                      {factor.cost_error && <span className={styles.error}>{factor.cost_error}</span>}
                      {!factor.cost_error && factor.cost_cents_add != null && (
                        <span className={styles.small}>{money(factor.cost_cents_add)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className={styles.disclosure}>
            <strong>Modeled additions, not quotes.</strong> Present/absent comes from provider evidence. Minutes and dollars are your assumptions
            except the seeded provider travel baseline. Partial coverage is not an all-clear.
          </p>
        </>
      )}
    </section>
  );
}
