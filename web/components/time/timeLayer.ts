// Three.js as a MapLibre custom layer. Scene units: x east / y north in metres from a fixed origin, z in YEARS since the
// axis epoch. One matrix per frame maps that into MapLibre's mercator world, so the vertical scale (pixels per year)
// can follow the zoom and the whole time axis can be flattened to 2D without touching a single stored fact.
import * as THREE from "three";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
import { LineSegments2 } from "three/examples/jsm/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/examples/jsm/lines/LineSegmentsGeometry.js";
import type { CustomLayerInterface, CustomRenderMethodInput, Map as MlMap } from "maplibre-gl";
import { calmAt, metersPerPixel, yearPxAt, type Span } from "./timeScale";
import { hex, mul, ease, points, fillPoints, lines, fillLines, project, createRenderer, disposeScene, type RGB, type Seg } from "./scenePrimitives";

type Ml = typeof import("maplibre-gl");

/** `out`: outside the chosen scope, laid down as a grey ground trace (F19 spec 17). */
export type Emphasis = "out" | "normal" | "dim" | "hot" | "sel";
export interface TimeItem {
  key: string;
  color: string;
  lng: number;
  lat: number;
  span: Span;
  /** Tentative location (C25): drawn as a hollow bead so it never reads as a reviewed point. */
  outline?: boolean;
  /** Independently confirmed location (C25): the bead and its ground mark carry an outer ring. Color is the state. */
  ringed?: boolean;
}
export interface Focus {
  emphasis: (key: string) => Emphasis;
  /** Ground links (the current view's pairs); `hot` links draw brighter. `path` ([lng, lat], A to B) is a stored
   * road route; without it the link is centre to centre. */
  links: { a: string; b: string; hot: boolean; path?: [number, number][] | null }[];
  /** Selected pair whose dates are both exact: draw the dimension bracket between their beads. */
  dimension: { a: string; b: string } | null;
  /** Where the time ruler stands. */
  ruler: { lng: number; lat: number };
  /** No scope: unfocused points go quiet at national zoom (thin, dim stems, no halos). */
  quiet: boolean;
}
export interface LabelSpec {
  id: string;
  lng: number;
  lat: number;
  /** Height in years above the axis ground. */
  years: number;
}
export type Projected = Map<string, { x: number; y: number; on: boolean }>;
/** The two centers of a selected pair, for drawing the 25-mile rule around each. */
export interface RuleRings {
  a: { lng: number; lat: number; color: string };
  /** Absent for a pin: one circle. */
  b?: { lng: number; lat: number; color: string };
}
/** Sweep progress during the intro: the year reached and how many dated items are filed in service by then. */
export type SweepState = { years: number; shown: number; total: number } | null;

const INK: RGB = hex("#f4efe6");
/** Out-of-scope trace: no data colour, so it never reads as a tier, a utility or an undated project. */
const TRACE: RGB = hex("#7d8799");
const BRIGHT: Record<Emphasis, number> = { out: 0.75, normal: 1, dim: 0.18, hot: 1.5, sel: 1.6 };
const RULE_M = 40_233.6; // 25 statute miles, the overlap rule's radius
const GHOST = 0.2; // brightness of items filed after the scrubber's date
const SIZE: Record<Emphasis, number> = { out: 6, normal: 10, dim: 7, hot: 16, sel: 22 };

// One point shader for beads (0), ground rings (1) and ruler ticks (2). Additive, so draw order doesn't matter.
const POINT_VS = /* glsl */ `
  attribute vec3 tint; attribute float size; attribute float shape; attribute float bright;
  uniform float uDpr; uniform float uW0;
  varying vec3 vTint; varying float vShape; varying float vBright; varying float vFade;
  void main() {
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * uDpr;
    vTint = tint; vShape = shape; vBright = bright;
    // Depth: points farther than the view's centre recede a little.
    vFade = uW0 > 0.0 ? clamp(1.35 - 0.35 * gl_Position.w / uW0, 0.45, 1.0) : 1.0;
  }`;
const POINT_FS = /* glsl */ `
  varying vec3 vTint; varying float vShape; varying float vBright; varying float vFade;
  void main() {
    vec2 c = gl_PointCoord * 2.0 - 1.0;
    float r = length(c);
    vec3 col; float a;
    if (vShape < 0.5) {
      if (r > 1.0) discard;
      float core = smoothstep(0.24, 0.12, r);
      float glow = pow(max(1.0 - r, 0.0), 2.4);
      col = mix(vTint * 1.15, vec3(1.0, 0.975, 0.94), core);
      a = max(core, glow * 0.85);
    } else if (vShape < 1.5) {
      float ring = smoothstep(0.2, 0.02, abs(r - 0.7));
      if (ring < 0.02) discard;
      col = vTint; a = ring * 0.9;
    } else if (vShape < 2.5) {
      if (abs(c.y) > 0.11 || abs(c.x) > 0.95) discard;
      col = vTint; a = 0.9;
    } else {
      // Halo: a soft gaussian, the stand-in for bloom (no post-processing in a shared GL context).
      if (r > 1.0) discard;
      col = vTint; a = exp(-r * r * 4.5) * 0.55;
    }
    gl_FragColor = vec4(col * vBright * vFade, a * min(vBright, 1.0) * vFade);
  }`;

// The "today" sheet: faint glass with a 10-mile grid, fading out toward its edges.
const PLANE_VS = /* glsl */ `
  varying vec2 vUv; varying vec2 vPos;
  void main() {
    vUv = uv; vPos = (modelMatrix * vec4(position, 1.0)).xy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;
const PLANE_FS = /* glsl */ `
  uniform vec3 uColor; uniform float uGrid; uniform float uOpacity;
  varying vec2 vUv; varying vec2 vPos;
  void main() {
    vec2 g = vPos / uGrid;
    vec2 w = abs(fract(g - 0.5) - 0.5) / max(fwidth(g), vec2(1e-6));
    float line = 1.0 - min(min(w.x, w.y), 1.0);
    float d = length(vUv - 0.5) * 2.0;
    float fade = smoothstep(1.0, 0.25, d);
    float rim = smoothstep(0.035, 0.0, abs(d - 0.93)) * 0.35;
    gl_FragColor = vec4(uColor, (0.05 + line * 0.13 + rim) * fade * uOpacity);
  }`;

/** A unit circle on the ground, scaled and placed per frame: one per end of the selected pair. */
function ring() {
  const pos: number[] = [];
  const n = 128;
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2;
    const a1 = ((i + 1) / n) * Math.PI * 2;
    pos.push(Math.cos(a0), Math.sin(a0), 0, Math.cos(a1), Math.sin(a1), 0);
  }
  const g = new LineSegmentsGeometry();
  g.setPositions(pos);
  const mat = new LineMaterial({
    color: 0xffffff,
    linewidth: 1.5,
    transparent: true,
    opacity: 0.75,
    depthTest: false,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new LineSegments2(g, mat);
  mesh.frustumCulled = false;
  mesh.visible = false;
  return { mesh, width: 1.5 };
}

/** Split a vertical segment at the today plane so its lower part renders under the glass and the rest above it. */
function split(z0: number, z1: number, zt: number): { below: [number, number] | null; above: [number, number] | null } {
  const lo = Math.min(z0, z1);
  const hi = Math.max(z0, z1);
  if (hi <= zt) return { below: [lo, hi], above: null };
  if (lo >= zt) return { below: null, above: [lo, hi] };
  return { below: [lo, zt], above: [zt, hi] };
}

export function createTimeLayer(
  ml: Ml,
  opts: { onFrame: (p: Projected) => void; onSweep?: (s: SweepState) => void },
) {
  let map: MlMap | null = null;
  let renderer: THREE.WebGLRenderer | null = null;
  const scene = new THREE.Scene();
  const camera = new THREE.Camera();
  let origin = ml.MercatorCoordinate.fromLngLat([-82, 33]);
  let unit = origin.meterInMercatorCoordinateUnits();

  let items: TimeItem[] = [];
  let todayYears = 0;
  let maxYears = 1;
  let focus: Focus | null = null;
  let labels: LabelSpec[] = [];
  // Years the axis must fit on screen: a selected pair's top, or null for every drawn item (maxYears).
  let fitYears: number | null = null;
  let heightFactor = 0;
  let anim: { from: number; to: number; start: number; ms: number } | null = null;
  // Intro sweep (years reached; Infinity = everything shown) and the scrubber's chosen date (null = analysis date).
  let sweep = Infinity;
  let sweepAnim: { start: number; ms: number; to: number } | null = null;
  let asOf: number | null = null;
  let rules: { a: [number, number, number]; b?: [number, number, number]; start: number } | null = null;
  // Last frame's screen geometry for picking: pillar foot and top per item.
  let hits: { key: string; x0: number; y0: number; x1: number; y1: number }[] = [];
  // Brightness of unfocused points (calmAt), and when the post-sweep settle into it began.
  let calm = 1;
  let settle: number | null = null;
  const calmNow = (now: number) => {
    if (!map || !focus?.quiet || sweepAnim) return 1;
    const t = settle === null ? 1 : Math.min((now - settle) / 1200, 1);
    if (t >= 1) settle = null;
    // Quantized, so zooming rebuilds a few dozen times rather than every frame.
    return Math.round((1 + (calmAt(map.getZoom()) - 1) * ease(t)) * 40) / 40;
  };

  const links = lines(1.2);
  const linksHot = lines(2.2);
  const pillarsBelow = lines(1.6);
  const pillarsAbove = lines(1.6);
  const pillarsSel = lines(3);
  const rangesBelow = lines(7);
  const rangesAbove = lines(7);
  const ruler = lines(1.2);
  const dimSolid = lines(1.6);
  const dimDashed = lines(1.1, { dashed: true });
  const beadsBelow = points(POINT_VS, POINT_FS);
  const beadsAbove = points(POINT_VS, POINT_FS);
  const anchors = points(POINT_VS, POINT_FS);
  const marks = points(POINT_VS, POINT_FS);
  const halos = points(POINT_VS, POINT_FS);
  const ruleA = ring();
  const ruleB = ring();
  const plane = new THREE.Mesh(
    new THREE.PlaneGeometry(1, 1),
    new THREE.ShaderMaterial({
      vertexShader: PLANE_VS,
      fragmentShader: PLANE_FS,
      uniforms: { uColor: { value: new THREE.Vector3(...hex("#bfe9ff")) }, uGrid: { value: 16_093.44 }, uOpacity: { value: 1 } },
      transparent: true,
      depthTest: false,
      depthWrite: false,
      side: THREE.DoubleSide,
    }),
  );
  plane.frustumCulled = false;

  // Draw order: ground, everything below today, the glass sheet, everything above it, then the drafting marks.
  const ordered: THREE.Object3D[] = [
    ruleA.mesh, ruleB.mesh, links.mesh, linksHot.mesh, anchors, halos, pillarsBelow.mesh, rangesBelow.mesh, beadsBelow, plane,
    pillarsAbove.mesh, pillarsSel.mesh, rangesAbove.mesh, beadsAbove, ruler.mesh, dimDashed.mesh, dimSolid.mesh, marks,
  ];
  ordered.forEach((o, i) => {
    o.renderOrder = i;
    scene.add(o);
  });
  const allLines = [links, linksHot, pillarsBelow, pillarsAbove, pillarsSel, rangesBelow, rangesAbove, ruler, dimSolid, dimDashed, ruleA, ruleB];
  const allPoints = [beadsBelow, beadsAbove, anchors, marks, halos];

  const local = (lng: number, lat: number): [number, number] => {
    const m = ml.MercatorCoordinate.fromLngLat([lng, lat]);
    return [(m.x - origin.x) / unit, -(m.y - origin.y) / unit];
  };
  const topOf = (s: Span) => (s.kind === "exact" ? s.day : s.kind === "range" ? s.to : 0) / 365.25;

  function rebuild() {
    const byKey = new Map(items.map((it) => [it.key, it]));
    const emph = (k: string) => focus?.emphasis(k) ?? "normal";
    const zt = asOf ?? todayYears;
    const segs = { pb: [] as Seg[], pa: [] as Seg[], ps: [] as Seg[], rb: [] as Seg[], ra: [] as Seg[] };
    const beads = { b: [] as Parameters<typeof fillPoints>[1], a: [] as Parameters<typeof fillPoints>[1] };
    const rings: Parameters<typeof fillPoints>[1] = [];
    const glow: Parameters<typeof fillPoints>[1] = [];
    const sweeping = sweepAnim !== null;
    let shown = 0;
    let dated = 0;

    // Dim first, bright last, so highlighted pillars read on top even with additive blending.
    const rank = { out: -1, dim: 0, normal: 1, hot: 2, sel: 3 } as const;
    for (const it of [...items].sort((x, y) => rank[emph(x.key)] - rank[emph(y.key)])) {
      const e = emph(it.key);
      if (e === "out") {
        rings.push({ p: [...local(it.lng, it.lat), 0], c: TRACE, size: SIZE.out, shape: 1, bright: BRIGHT.out });
        continue;
      }
      const c = hex(it.color);
      const [x, y] = local(it.lng, it.lat);
      const full = topOf(it.span);
      // Scrubber: anything filed after the chosen date is a ghost.
      const k = BRIGHT[e] * (asOf !== null && it.span.kind !== "unknown" && full > asOf ? GHOST : 1);
      // Quiet overview: an unfocused point is a dim stem (q) with a smaller-dimmed dot (dot) and no halo (lit).
      const q = e === "normal" ? calm : 1;
      const dot = 0.35 + 0.65 * q;
      const lit = e === "normal" ? Math.max(0, (calm - 0.4) / 0.6) : 1;
      rings.push({ p: [x, y, 0], c, size: e === "dim" ? 8 : e === "sel" ? 20 : 11, shape: 1, bright: k * 0.8 * dot });
      if (it.ringed) rings.push({ p: [x, y, 0], c, size: e === "dim" ? 15 : e === "sel" ? 36 : 20, shape: 1, bright: k * 0.6 * dot });
      if (e !== "dim" && k > GHOST && lit > 0) glow.push({ p: [x, y, 0], c, size: e === "sel" ? 46 : 20, shape: 3, bright: k * 0.16 * lit });
      if (it.span.kind === "unknown") continue;
      dated++;
      // Sweep: the pillar grows to min(date, sweep); its bead appears, with a flash, once the sweep passes it.
      if (sweep <= 0) continue;
      const top = Math.min(full, sweep);
      const reached = sweep >= full;
      if (reached) shown++;
      const flash = sweeping && reached ? Math.max(0, 1 - (sweep - full) / 0.9) : 0;
      // The pillar: a beam of light from the ground anchor up to the date, brightening with height.
      const beamTop = it.span.kind === "range" ? Math.min(it.span.from / 365.25, top) : top;
      const beam = split(0, beamTop, zt);
      const beamSeg = ([z0, z1]: [number, number]): Seg => ({
        a: [x, y, z0],
        b: [x, y, z1],
        ca: mul(c, (0.05 + (0.45 * z0) / Math.max(top, 1e-6)) * k * q),
        cb: mul(c, (0.05 + (0.45 * z1) / Math.max(top, 1e-6)) * k * q),
      });
      if (e === "sel") {
        // A selected pillar is one bright, wide beam drawn above the glass, so it reads through it.
        segs.ps.push({ a: [x, y, 0], b: [x, y, beamTop], ca: mul(c, 0.25), cb: mul(c, 1.1) });
      } else {
        if (beam.below) segs.pb.push(beamSeg(beam.below));
        if (beam.above) segs.pa.push(beamSeg(beam.above));
      }
      if (it.span.kind === "exact") {
        if (!reached) continue;
        (top >= zt ? beads.a : beads.b).push({ p: [x, y, top], c, size: SIZE[e] * (1 + 0.7 * flash), shape: it.outline ? 1 : 0, bright: k * (1 + 1.1 * flash) * dot });
        if (it.ringed) (top >= zt ? beads.a : beads.b).push({ p: [x, y, top], c, size: SIZE[e] * 2, shape: 1, bright: k * 0.8 * dot });
        if (e !== "dim" && k > GHOST && lit > 0) glow.push({ p: [x, y, top], c, size: SIZE[e] * (3.2 + 2.2 * flash), shape: 3, bright: k * (0.55 + 0.9 * flash) * lit });
      } else {
        // A month or year: frosted column over the whole span, with rings at both ends. No day is picked.
        if (sweep < it.span.from / 365.25) continue;
        const col = split(it.span.from / 365.25, top, zt);
        const colSeg = ([z0, z1]: [number, number]): Seg => ({ a: [x, y, z0], b: [x, y, z1], ca: mul(c, 0.32 * k * q), cb: mul(c, 0.32 * k * q) });
        if (col.below) segs.rb.push(colSeg(col.below));
        if (col.above) segs.ra.push(colSeg(col.above));
        for (const z of [it.span.from / 365.25, top])
          if (z <= sweep) (z >= zt ? beads.a : beads.b).push({ p: [x, y, z], c, size: SIZE[e] * 0.9, shape: 1, bright: k * dot });
      }
    }
    fillLines(pillarsBelow, segs.pb);
    fillLines(pillarsAbove, segs.pa);
    fillLines(pillarsSel, segs.ps);
    fillLines(rangesBelow, segs.rb);
    fillLines(rangesAbove, segs.ra);
    fillPoints(beadsBelow, beads.b);
    fillPoints(beadsAbove, beads.a);
    fillPoints(anchors, rings);
    fillPoints(halos, glow);
    if (sweeping) opts.onSweep?.({ years: sweep, shown, total: dated });

    // Ground links: the stored road route when the pair has one, otherwise centre to centre.
    const link = (hot: boolean) =>
      (focus?.links ?? [])
        .filter((l) => l.hot === hot)
        .flatMap((l): Seg[] => {
          const a = byKey.get(l.a);
          const b = byKey.get(l.b);
          if (!a || !b) return [];
          const c = mul(INK, hot ? 0.95 : 0.22);
          const pts: [number, number][] = l.path && l.path.length >= 2 ? l.path : [[a.lng, a.lat], [b.lng, b.lat]];
          return pts.slice(1).map((p, k): Seg => ({ a: [...local(...pts[k]), 0], b: [...local(...p), 0], ca: c, cb: c }));
        });
    fillLines(links, link(false));
    fillLines(linksHot, link(true));

    // Time ruler: a spine with a tick per year and a brighter tick at today.
    const marksRows: Parameters<typeof fillPoints>[1] = [];
    const rulerSegs: Seg[] = [];
    if (focus) {
      const [rx, ry] = local(focus.ruler.lng, focus.ruler.lat);
      const topYear = Math.ceil(maxYears) + 0.35;
      rulerSegs.push({ a: [rx, ry, 0], b: [rx, ry, topYear], ca: mul(INK, 0.14), cb: mul(INK, 0.5) });
      for (let yv = 0; yv <= Math.ceil(maxYears); yv++)
        marksRows.push({ p: [rx, ry, yv], c: INK, size: 12, shape: 2, bright: 0.55 });
      marksRows.push({ p: [rx, ry, zt], c: hex("#bfe9ff"), size: 22, shape: 2, bright: 1 });
    }
    // The dimension bracket: extension lines from each bead to a shared vertical, like a drafting dimension.
    const dim = focus?.dimension;
    const dimSegs: Seg[] = [];
    const dashSegs: Seg[] = [];
    if (dim) {
      const a = byKey.get(dim.a);
      const b = byKey.get(dim.b);
      if (a?.span.kind === "exact" && b?.span.kind === "exact") {
        const [ax, ay] = local(a.lng, a.lat);
        const [bx, by] = local(b.lng, b.lat);
        const mx = (ax + bx) / 2;
        const my = (ay + by) / 2;
        const za = topOf(a.span);
        const zb = topOf(b.span);
        dashSegs.push({ a: [ax, ay, za], b: [mx, my, za], ca: mul(INK, 0.7), cb: mul(INK, 0.7) });
        dashSegs.push({ a: [bx, by, zb], b: [mx, my, zb], ca: mul(INK, 0.7), cb: mul(INK, 0.7) });
        dimSegs.push({ a: [mx, my, za], b: [mx, my, zb], ca: INK, cb: INK });
        for (const z of [za, zb]) marksRows.push({ p: [mx, my, z], c: INK, size: 14, shape: 2, bright: 1.2 });
      }
    }
    fillLines(ruler, rulerSegs);
    fillLines(dimSolid, dimSegs);
    fillLines(dimDashed, dashSegs);
    fillPoints(marks, marksRows);

    // The glass sheet covers the drawn area with a margin, centred on it.
    const lifted = items.filter((it) => emph(it.key) !== "out");
    if (lifted.length) {
      const xs = lifted.map((it) => local(it.lng, it.lat));
      const minX = Math.min(...xs.map((p) => p[0]));
      const maxX = Math.max(...xs.map((p) => p[0]));
      const minY = Math.min(...xs.map((p) => p[1]));
      const maxY = Math.max(...xs.map((p) => p[1]));
      const size = Math.max(maxX - minX, maxY - minY, 40_000) * 1.6;
      plane.scale.set(size, size, 1);
      plane.position.set((minX + maxX) / 2, (minY + maxY) / 2, zt);
      plane.visible = true;
    } else plane.visible = false;
    map?.triggerRepaint();
  }

  function frameMatrix(args: CustomRenderMethodInput): THREE.Matrix4 {
    const c = map!.getCenter();
    const zoom = map!.getZoom();
    const yearPx = yearPxAt(zoom, fitYears ?? maxYears, map!.getCanvas().clientHeight * 0.75);
    const metresPerYear = yearPx * metersPerPixel(c.lat, zoom) * Math.max(heightFactor, 1e-4);
    const main = new THREE.Matrix4().fromArray(args.defaultProjectionData.mainMatrix as unknown as number[]);
    const localM = new THREE.Matrix4()
      .makeTranslation(origin.x, origin.y, origin.z)
      .scale(new THREE.Vector3(unit, -unit, unit * metresPerYear));
    return main.multiply(localM);
  }

  const layer: CustomLayerInterface = {
    id: "gridbridge-time",
    type: "custom",
    renderingMode: "3d",
    onAdd(m, gl) {
      map = m;
      renderer = createRenderer(m, gl);
    },
    onRemove() {
      disposeScene(scene, renderer);
      renderer = null;
      map = null;
    },
    render(gl, args) {
      if (!map || !renderer) return;
      const now = performance.now();
      if (anim) {
        const t = Math.min((now - anim.start) / anim.ms, 1);
        heightFactor = anim.from + (anim.to - anim.from) * ease(t);
        if (t >= 1) anim = null;
        map.triggerRepaint();
      }
      if (sweepAnim) {
        // Linear in time so years pass at an even pace; the flash decay gives each bead its own beat.
        const t = Math.max(0, (now - sweepAnim.start) / sweepAnim.ms);
        sweep = t >= 1 ? Infinity : t * sweepAnim.to;
        if (t >= 1) {
          sweepAnim = null;
          settle = now;
          opts.onSweep?.(null);
        }
        rebuild();
      }
      const c = calmNow(now);
      if (c !== calm) {
        calm = c;
        rebuild();
      }
      if (settle !== null) map.triggerRepaint();
      const w = gl.drawingBufferWidth;
      const h = gl.drawingBufferHeight;
      const dpr = w / Math.max(map.getCanvas().clientWidth, 1);
      for (const l of allLines) {
        const mat = l.mesh.material as LineMaterial;
        mat.resolution.set(w, h);
        // Unfocused stems thin out with the quiet overview; selected pillars (pillarsSel) keep their width.
        mat.linewidth = l.width * dpr * (l === pillarsBelow || l === pillarsAbove ? 0.5 + 0.5 * calm : 1);
        mat.dashSize = 6 * dpr;
        mat.gapSize = 5 * dpr;
      }
      for (const p of allPoints) p.material.uniforms.uDpr.value = dpr;
      // The sheet fades in with the axis and, during the sweep, only once the sweep has reached it.
      const sheetOn = sweep >= (asOf ?? todayYears) ? 1 : 0.18;
      (plane.material as THREE.ShaderMaterial).uniforms.uOpacity.value = Math.min(heightFactor * 1.4, 1) * sheetOn;
      ruler.mesh.visible = marks.visible = heightFactor > 0.03 && ruler.mesh.geometry.attributes.instanceStart !== undefined;

      const m = frameMatrix(args);
      // The 25-mile rule: a circle per end of the selected pair, growing in over 0.7 s.
      for (const [r, end] of [
        [ruleA, rules?.a],
        [ruleB, rules?.b],
      ] as const) {
        r.mesh.visible = !!end;
        if (!end || !rules) continue;
        const g = ease(Math.min((now - rules.start) / 700, 1));
        r.mesh.position.set(end[0], end[1], 0);
        r.mesh.scale.set(end[2] * g, end[2] * g, 1);
        r.mesh.updateMatrixWorld();
        if (g < 1) map.triggerRepaint();
      }
      // Depth fade reference: the clip-space w of the view's centre on the ground.
      const cc = map.getCenter();
      const w0 = new THREE.Vector4(...local(cc.lng, cc.lat), 0, 1).applyMatrix4(m).w;
      for (const p of allPoints) p.material.uniforms.uW0.value = w0 > 0 ? w0 : 0;
      camera.projectionMatrix.copy(m);
      camera.projectionMatrixInverse.copy(m).invert();
      renderer.resetState();
      renderer.setViewport(0, 0, w, h);
      renderer.render(scene, camera);

      // Screen positions for HTML labels and hit testing, in CSS pixels.
      const cw = map.getCanvas().clientWidth;
      const ch = map.getCanvas().clientHeight;
      const out: Projected = new Map();
      for (const l of labels) out.set(l.id, project(m, ...local(l.lng, l.lat), l.years, cw, ch));
      // Out-of-scope traces are context, not targets.
      hits = items.filter((it) => focus?.emphasis(it.key) !== "out").map((it) => {
        const [x, y] = local(it.lng, it.lat);
        const foot = project(m, x, y, 0, cw, ch);
        const top = project(m, x, y, topOf(it.span), cw, ch);
        return { key: it.key, x0: foot.x, y0: foot.y, x1: top.x, y1: top.y };
      });
      opts.onFrame(out);
    },
  };

  return {
    layer,
    setItems(next: TimeItem[], today: number) {
      items = next;
      todayYears = today;
      maxYears = Math.max(today, ...next.map((it) => topOf(it.span)), 1);
      if (next.length) {
        const lng = next.reduce((s, it) => s + it.lng, 0) / next.length;
        const lat = next.reduce((s, it) => s + it.lat, 0) / next.length;
        origin = ml.MercatorCoordinate.fromLngLat([lng, lat]);
        unit = origin.meterInMercatorCoordinateUnits();
      }
      rebuild();
    },
    setFocus(f: Focus) {
      focus = f;
      rebuild();
    },
    setLabels(next: LabelSpec[]) {
      labels = next;
      map?.triggerRepaint();
    },
    setFitYears(years: number | null) {
      fitYears = years;
      map?.triggerRepaint();
    },
    /** Grow (1) or flatten (0) the time axis. Facts are untouched either way. */
    setHeight(target: number, ms: number) {
      anim = ms > 0 ? { from: heightFactor, to: target, start: performance.now(), ms } : null;
      if (!anim) heightFactor = target;
      map?.triggerRepaint();
    },
    /** Replay the intro sweep: pillars grow in date order over `ms` (0 = show everything at once). */
    sweepIn(ms: number, delay = 0) {
      if (ms <= 0) {
        sweep = Infinity;
        sweepAnim = null;
        opts.onSweep?.(null);
      } else {
        sweep = 0;
        sweepAnim = { start: performance.now() + delay, ms, to: Math.ceil(maxYears) + 0.4 };
      }
      rebuild();
    },
    /** Scrubber: ghost everything filed after `years` and move the sheet there; null = back to the analysis date. */
    setAsOf(years: number | null) {
      asOf = years;
      rebuild();
    },
    /** Draw the 25-mile rule around both ends of the selected pair, or around a pin (null clears it). */
    setRules(next: RuleRings | null) {
      if (!next) {
        rules = null;
      } else {
        const end = (e: RuleRings["a"]): [number, number, number] => {
          const [x, y] = local(e.lng, e.lat);
          // Metres at the end's own latitude, expressed in the layer's local units.
          const r = (RULE_M * ml.MercatorCoordinate.fromLngLat([e.lng, e.lat]).meterInMercatorCoordinateUnits()) / unit;
          return [x, y, r];
        };
        rules = { a: end(next.a), b: next.b ? end(next.b) : undefined, start: performance.now() };
        (ruleA.mesh.material as LineMaterial).color.set(next.a.color);
        if (next.b) (ruleB.mesh.material as LineMaterial).color.set(next.b.color);
      }
      map?.triggerRepaint();
    },
    /** Nearest item to a screen point: distance to its pillar (foot to top), within `radius` CSS pixels. */
    pick(px: number, py: number, radius = 12): string | null {
      let best: string | null = null;
      let bestD = radius;
      for (const h of hits) {
        const dx = h.x1 - h.x0;
        const dy = h.y1 - h.y0;
        const len2 = dx * dx + dy * dy;
        const t = len2 ? Math.max(0, Math.min(1, ((px - h.x0) * dx + (py - h.y0) * dy) / len2)) : 0;
        // Favour the bead at the top: it's what people aim at.
        const d = Math.hypot(px - (h.x0 + t * dx), py - (h.y0 + t * dy)) + (1 - t) * 4;
        if (d < bestD) {
          bestD = d;
          best = h.key;
        }
      }
      return best;
    },
  };
}

export type TimeLayer = ReturnType<typeof createTimeLayer>;
