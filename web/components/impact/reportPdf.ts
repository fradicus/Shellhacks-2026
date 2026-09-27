import type { DateReport, DelayInputs } from "./delayModel";
import { PAGE, PdfDoc, type Rgb } from "./pdf";
import type { LastYear } from "./reportModel";
import type { ForecastDay, SiteHints } from "./siteModel";
import { phClass } from "./siteModel";
import type { HistoryPayload } from "./WeatherDelay";

const INK: Rgb = [20, 24, 32], MUTED: Rgb = [96, 100, 108], RULE: Rgb = [210, 214, 220], BAR: Rgb = [70, 170, 148], STOP: Rgb = [226, 110, 76], PANEL: Rgb = [244, 246, 249];
const PERMIT_SOURCE = "https://www.govinfo.gov/content/pkg/FR-2025-06-18/html/2025-11190.htm";
const date = (d: string | null) => (d ? new Date(Date.parse(`${d}T00:00:00Z`)).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }) : "-");
const usd = (cents: number) => (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });

export type ReportPdfInput = {
  pointLabel: string; point: { lat: number; lon: number } | null; start: string; inputs: DelayInputs; history: HistoryPayload;
  report: DateReport; lastYear: LastYear | null; cost: number | null; costLabel: string; hints: SiteHints | null; forecast: ForecastDay[];
};

function heading(doc: PdfDoc, text: string) {
  doc.ensure(40);
  doc.y -= 8;
  doc.text(PAGE.margin, doc.y - 12, text, 12, { bold: true });
  doc.y -= 18;
  doc.line(PAGE.margin, doc.y, PAGE.w - PAGE.margin, doc.y, RULE, 0.75);
  doc.y -= 8;
}

function row(doc: PdfDoc, label: string, value: string) {
  doc.ensure(16);
  doc.text(PAGE.margin, doc.y - 10, label, 9, { color: MUTED });
  doc.paragraph(value, 10, { x: PAGE.margin + 150, width: PAGE.w - 2 * PAGE.margin - 150, gap: 2 });
}

export function buildReportPdf(r: ReportPdfInput): Uint8Array {
  const doc = new PdfDoc();
  const { report, history, inputs } = r;
  // Title band
  doc.rect(0, PAGE.h - 86, PAGE.w, 86, [12, 17, 25]);
  doc.text(PAGE.margin, PAGE.h - 44, "Common Ground | Site weather delay report", 18, { bold: true, color: [244, 239, 230] });
  doc.text(PAGE.margin, PAGE.h - 66, `${r.pointLabel}${r.point ? `  (${r.point.lat.toFixed(4)}, ${r.point.lon.toFixed(4)})` : ""}`, 10, { color: [191, 233, 255] });
  doc.y = PAGE.h - 104;
  doc.paragraph(`Generated ${new Date().toLocaleString("en-US")}. Historical replay of NOAA station records, not a forecast. All costs use user-entered rates.`, 9, { color: MUTED });

  // Headline numbers
  const cards: [string, string, string][] = [
    ["Normal finish", date(report.target.normalFinish), `${report.baselineDays ?? "-"} calendar days`],
    ["Typical weather", date(report.target.typicalFinish), `+${report.medianExtra ?? "-"} days${r.cost !== null && report.medianExtra !== null ? ` | ${usd(Math.round(report.medianExtra * r.cost))}` : ""}`],
    [`Worst year (${report.worst?.year ?? "-"})`, date(report.target.worstFinish), `+${report.worst?.extraDays ?? "-"} days${r.cost !== null && report.worst ? ` | ${usd(report.worst.extraDays * r.cost)}` : ""}`],
    [`Last year (${r.lastYear?.year ?? "-"})`, r.lastYear?.run ? `+${r.lastYear.run.extraDays} days` : "Not available", r.lastYear?.run && r.cost !== null ? usd(r.lastYear.run.extraDays * r.cost) : r.lastYear?.from === "recent" ? "NOAA latest observations" : ""],
  ];
  const cw = (PAGE.w - 2 * PAGE.margin - 3 * 8) / 4, top = doc.y - 4;
  cards.forEach(([label, big, small], i) => {
    const x = PAGE.margin + i * (cw + 8);
    doc.rect(x, top - 62, cw, 62, i === 2 ? [253, 236, 229] : PANEL);
    doc.text(x + 8, top - 14, label, 8, { color: MUTED });
    doc.text(x + 8, top - 32, big, 10.5, { bold: true });
    doc.text(x + 8, top - 48, small, 8.5, { color: INK });
  });
  doc.y = top - 74;

  heading(doc, "Plan");
  row(doc, "Start date", date(r.start));
  row(doc, "Workable days needed", `${inputs.workdays}${inputs.weekdaysOnly ? " (weekdays only)" : " (7-day week)"}`);
  const rules = [
    inputs.rainIn.trim() && `rain >= ${inputs.rainIn} in/day`, inputs.windMph.trim() && history.wind && `wind gust >= ${inputs.windMph} mph`,
    inputs.heatF.trim() && `high >= ${inputs.heatF} F`, inputs.freezeF.trim() && `low <= ${inputs.freezeF} F`, inputs.snowIn.trim() && `snow >= ${inputs.snowIn} in`,
    inputs.dryingDays.trim() !== "0" && `${inputs.dryingDays} wet-ground day(s) after each rain stop`,
  ].filter(Boolean).join("; ");
  row(doc, "Stop rules", rules || "none");
  row(doc, "Delay-day cost", r.cost !== null ? `${usd(r.cost)} (${r.costLabel})` : "not entered");
  row(doc, "Weather station", `${history.rain.name} (${history.rain.id}), ${history.rain.distance_mi} mi${history.wind ? `; wind: ${history.wind.name}, ${history.wind.distance_mi} mi` : "; no wind record nearby"}`);
  row(doc, "Record", `${history.window.start} to ${history.window.end}, NOAA NCEI GHCN-Daily`);

  // Last-year chart
  const ly = r.lastYear;
  heading(doc, `This time last year${ly ? `: ${date(ly.start)} onward` : ""}`);
  if (ly && ly.days.length) {
    doc.ensure(170);
    const x0 = PAGE.margin + 28, x1 = PAGE.w - PAGE.margin, h = 120, base = doc.y - h - 8;
    const max = Math.max(0.5, Number(inputs.rainIn) || 0, ...ly.days.map((d) => d.prcp ?? 0));
    const topV = max <= 1 ? Math.ceil(max * 4) / 4 : Math.ceil(max);
    const yv = (v: number) => base + (h * v) / topV;
    [0, topV / 2, topV].forEach((v) => { doc.line(x0, yv(v), x1, yv(v), RULE, 0.5); doc.text(PAGE.margin, yv(v) - 3, v.toFixed(v > 0 && v < 1 ? 2 : 0), 7, { color: MUTED }); });
    if (inputs.rainIn.trim() && Number(inputs.rainIn) <= topV) doc.line(x0, yv(Number(inputs.rainIn)), x1, yv(Number(inputs.rainIn)), STOP, 0.75, true);
    const band = (x1 - x0) / ly.days.length, bw = Math.max(1.5, Math.min(12, band - 1.5));
    ly.days.forEach((d, i) => {
      const cx = x0 + band * i + band / 2;
      if (d.prcp && d.prcp > 0) doc.rect(cx - bw / 2, base, bw, Math.max(0.8, yv(d.prcp) - base), d.reasons.length && d.workday ? STOP : BAR);
      const other = d.reasons.filter((x) => x !== "rain").map((x) => x[0].toUpperCase()).join("");
      if (other) doc.text(cx - 3, base - 10, other, 6.5, { bold: true, color: STOP });
      if (i === 0 || i % 7 === 0) doc.text(cx - 8, base - 20, d.date.slice(5).replace("-", "/"), 6.5, { color: MUTED });
    });
    doc.text(PAGE.margin, base + h + 6, "in/day", 7, { color: MUTED });
    doc.y = base - 30;
    doc.paragraph(`Orange bars: workdays lost to a stop rule. Letters: W wind, H heat, F freeze, S snow. Source: ${ly.from === "recent" ? "latest NOAA observations" : "NOAA 10-year record"}.${ly.run ? ` Replaying the task on these dates: +${ly.run.extraDays} days (${ly.run.stops.rain} rain, ${ly.run.stops.wind} wind stops).` : ""}`, 8.5, { color: MUTED });
  } else doc.paragraph("No record for last year's dates at this station.", 9, { color: MUTED });

  if (r.forecast.length) {
    heading(doc, "NWS forecast for the first days (context, not a stop rule)");
    r.forecast.forEach((f) => row(doc, date(f.date), `${f.summary} | ${f.maxPrecipChance ?? "-"}% chance of rain | high ${f.maxTemp ?? "-"} F`));
  }

  heading(doc, "Year-by-year replay from the same start date");
  const cols = ["Start", "Finished", "Extra", "Rain", "Wind", "Heat", "Freeze", "Snow", "Wet"], xs = [0, 80, 160, 210, 255, 300, 345, 395, 440];
  doc.ensure(16); cols.forEach((c, i) => doc.text(PAGE.margin + xs[i], doc.y - 10, c, 8, { bold: true, color: MUTED })); doc.y -= 16;
  report.runs.forEach((run) => {
    doc.ensure(13);
    [run.start, run.finish, `+${run.extraDays}`, run.stops.rain, run.stops.wind, run.stops.heat, run.stops.freeze, run.stops.snow, run.stops.wet].forEach((v, i) => doc.text(PAGE.margin + xs[i], doc.y - 9, String(v), 8.5));
    doc.y -= 13;
  });

  if (r.hints) {
    heading(doc, "Site conditions that add time");
    const h = r.hints;
    row(doc, "Wetland", h.wetlandMapped === null ? "Wetland map unavailable." : h.wetlandMapped ? `Mapped in NWI${h.wetlandType ? ` (${h.wetlandType})` : ""}. A Section 404 permit may be needed: USACE FY2024 average 55 days (nationwide permit notification) or 253 days (individual permit). Lead time before work; source: ${PERMIT_SOURCE}` : "No NWI wetland polygon at this point; a delineation decides.");
    row(doc, "Drainage", h.drainage ? `${h.drainage} (SSURGO).${h.poorlyDrained ? " Ground holds water after rain; see wet-ground rule." : ""}` : "Not available.");
    row(doc, "Soil pH", h.ph === null ? "No pH in the soil survey." : `${h.ph.toFixed(1)} (${phClass(h.ph)?.toLowerCase()}). Affects corrosion of buried steel and concrete (materials and cost), not weather days. No delay applied.`);
    row(doc, "Flood zone", h.floodZone ? `FEMA zone ${h.floodZone}${h.sfha ? " (special flood hazard area)" : ""}. River and tidal flooding are not in this replay.` : "Unknown.");
  }

  heading(doc, "Method and sources");
  doc.paragraph("Each recorded year is replayed from the same calendar start date: a workday is lost when it crosses a stop rule, and the task finishes after it banks its workable days. Missing readings count as workable. Station weather can differ from the site. This is planning evidence, not a schedule guarantee, bid or forecast.", 8.5, { color: MUTED });
  [history.citation, history.rain.source_url, ly?.sourceUrl ?? null].filter(Boolean).forEach((u) => doc.paragraph(u!, 7.5, { color: MUTED, gap: 1 }));
  return doc.bytes();
}

export function downloadReportPdf(r: ReportPdfInput) {
  const blob = new Blob([buildReportPdf(r) as BlobPart], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `site-weather-report-${r.start}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5_000);
}
