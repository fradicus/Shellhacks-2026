/* eslint-disable @typescript-eslint/no-require-imports */
// Build the decorative lower-48 outline used by the landing page network illustration.
// Source: U.S. Census Bureau TIGERweb States layer (generalized). Not used for matching.
// Usage: node scripts/build-us-illustration.cjs
const fs = require("node:fs");
const path = require("node:path");

const LAYER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/4";
const WIDTH = 1000;

// Albers equal-area conic tuned for the conterminous US.
const rad = Math.PI / 180;
const [phi1, phi2, phi0, lam0] = [29.5 * rad, 45.5 * rad, 37.5 * rad, -96 * rad];
const n = (Math.sin(phi1) + Math.sin(phi2)) / 2;
const C = Math.cos(phi1) ** 2 + 2 * n * Math.sin(phi1);
const rho0 = Math.sqrt(C - 2 * n * Math.sin(phi0)) / n;
function albers([lon, lat]) {
  const rho = Math.sqrt(C - 2 * n * Math.sin(lat * rad)) / n;
  const theta = n * (lon * rad - lam0);
  return [rho * Math.sin(theta), -(rho0 - rho * Math.cos(theta))];
}

async function main() {
  const query = new URLSearchParams({
    where: "STATE NOT IN ('02','15','60','66','69','72','78')",
    outFields: "STUSAB",
    returnGeometry: "true",
    outSR: "4326",
    maxAllowableOffset: "0.04",
    geometryPrecision: "3",
    f: "geojson",
  });
  const response = await fetch(`${LAYER}/query?${query}`);
  if (!response.ok) throw new Error(`TIGERweb ${response.status}`);
  const geo = await response.json();
  const states = geo.features.map((f) => {
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    return { c: f.properties.STUSAB, rings: polys.flatMap((p) => p).map((ring) => ring.map(albers)) };
  });
  const all = states.flatMap((s) => s.rings.flat());
  const minX = Math.min(...all.map((p) => p[0])), maxX = Math.max(...all.map((p) => p[0]));
  const minY = Math.min(...all.map((p) => p[1])), maxY = Math.max(...all.map((p) => p[1]));
  const k = WIDTH / (maxX - minX);
  const height = Math.round((maxY - minY) * k);
  const fit = ([x, y]) => [+((x - minX) * k).toFixed(1), +((y - minY) * k).toFixed(1)];
  const out = states
    .sort((a, b) => a.c.localeCompare(b.c))
    .map(({ c, rings }) => {
      const fitted = rings.map((r) => r.map(fit)).filter((r) => r.length > 3);
      const d = fitted.map((r) => `M${r.map((p) => p.join(",")).join("L")}Z`).join("");
      // Label point: area-weighted centroid of the largest ring.
      const main = fitted.reduce((best, r) => (Math.abs(area(r)) > Math.abs(area(best)) ? r : best));
      return { c, d, p: centroid(main) };
    });
  const target = path.resolve(__dirname, "../components/landing/illustration-us-states.json");
  fs.writeFileSync(
    target,
    JSON.stringify({
      source: "U.S. Census Bureau TIGERweb States layer, generalized (maxAllowableOffset 0.04°); Albers projection",
      source_url: `${LAYER}?f=pjson`,
      retrieved_at: new Date().toISOString(),
      width: WIDTH,
      height,
      states: out,
    }),
  );
  console.log(`wrote ${out.length} states → ${target}`);
}

function area(r) {
  let a = 0;
  for (let i = 0; i < r.length; i++) {
    const [x1, y1] = r[i], [x2, y2] = r[(i + 1) % r.length];
    a += x1 * y2 - x2 * y1;
  }
  return a / 2;
}
function centroid(r) {
  let cx = 0, cy = 0;
  const a = area(r);
  for (let i = 0; i < r.length; i++) {
    const [x1, y1] = r[i], [x2, y2] = r[(i + 1) % r.length];
    const f = x1 * y2 - x2 * y1;
    cx += (x1 + x2) * f;
    cy += (y1 + y2) * f;
  }
  return [+(cx / (6 * a)).toFixed(1), +(cy / (6 * a)).toFixed(1)];
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
