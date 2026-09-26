// Three.js as a MapLibre custom layer. Scene units: x east / y north in metres from a fixed origin, z in YEARS since the
// axis epoch. One matrix per frame maps that into MapLibre's mercator world, so the vertical scale (pixels per year)
// can follow the zoom and the whole time axis can be flattened to 2D without touching a single stored fact.
import * as THREE from "three";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
import { LineSegments2 } from "three/examples/jsm/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/examples/jsm/lines/LineSegmentsGeometry.js";
import type { CustomLayerInterface, CustomRenderMethodInput, Map as MlMap } from "maplibre-gl";
import { metersPerPixel, type Span } from "./timeScale";

type Ml = typeof import("maplibre-gl");
type RGB = [number, number, number];

export type Emphasis = "normal" | "dim" | "hot" | "sel";
export interface TimeItem {
  key: string;
  color: string;
  lng: number;
  lat: number;
  span: Span;
}
export interface Focus {
  emphasis: (key: string) => Emphasis;
  /** Ground links (the current view's pairs); `hot` links draw brighter. */
  links: { a: string; b: string; hot: boolean }[];
  /** Selected pair whose dates are both exact: draw the dimension bracket between their beads. */
  dimension: { a: string; b: string } | null;
  /** Where the time ruler stands. */
  ruler: { lng: number; lat: number };
}
export interface LabelSpec {
  id: string;
  lng: number;
  lat: number;
  /** Height in years above the axis ground. */
  years: number;
}
export type Projected = Map<string, { x: number; y: number; on: boolean }>;

const hex = (h: string): RGB => {
  const n = parseInt(h.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
};
const mul = (c: RGB, k: number): RGB => [c[0] * k, c[1] * k, c[2] * k];
const ease = (t: number) => 1 - (1 - t) ** 3;
const INK: RGB = hex("#f4efe6");
const BRIGHT: Record<Emphasis, number> = { normal: 1, dim: 0.26, hot: 1.5, sel: 1.6 };
const SIZE: Record<Emphasis, number> = { normal: 10, dim: 7, hot: 16, sel: 22 };

// One point shader for beads (0), ground rings (1) and ruler ticks (2). Additive, so draw order doesn't matter.
const POINT_VS = /* glsl */ `
  attribute vec3 tint; attribute float size; attribute float shape; attribute float bright;
  uniform float uDpr;
  varying vec3 vTint; varying float vShape; varying float vBright;
  void main() {
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * uDpr;
    vTint = tint; vShape = shape; vBright = bright;
  }`;
const POINT_FS = /* glsl */ `
  varying vec3 vTint; varying float vShape; varying float vBright;
  void main() {
    vec2 c = gl_PointCoord * 2.0 - 1.0;
    float r = length(c);
    vec3 col; float a;
    if (vShape < 0.5) {
      if (r > 1.0) discard;
      float core = smoothstep(0.36, 0.2, r);
      float glow = pow(max(1.0 - r, 0.0), 2.4);
      col = mix(vTint * 1.15, vec3(1.0, 0.975, 0.94), core);
      a = max(core, glow * 0.85);
    } else if (vShape < 1.5) {
      float ring = smoothstep(0.2, 0.02, abs(r - 0.7));
      if (ring < 0.02) discard;
      col = vTint; a = ring * 0.9;
    } else {
      if (abs(c.y) > 0.11 || abs(c.x) > 0.95) discard;
      col = vTint; a = 0.9;
    }
    gl_FragColor = vec4(col * vBright, a * min(vBright, 1.0));
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

function points(): THREE.Points<THREE.BufferGeometry, THREE.ShaderMaterial> {
  const mat = new THREE.ShaderMaterial({
    vertexShader: POINT_VS,
    fragmentShader: POINT_FS,
    uniforms: { uDpr: { value: 1 } },
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const pts = new THREE.Points(new THREE.BufferGeometry(), mat);
  pts.frustumCulled = false;
  return pts;
}

function fillPoints(
  pts: THREE.Points<THREE.BufferGeometry, THREE.ShaderMaterial>,
  rows: { p: [number, number, number]; c: RGB; size: number; shape: number; bright: number }[],
) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(rows.flatMap((r) => r.p), 3));
  g.setAttribute("tint", new THREE.Float32BufferAttribute(rows.flatMap((r) => r.c), 3));
  g.setAttribute("size", new THREE.Float32BufferAttribute(rows.map((r) => r.size), 1));
  g.setAttribute("shape", new THREE.Float32BufferAttribute(rows.map((r) => r.shape), 1));
  g.setAttribute("bright", new THREE.Float32BufferAttribute(rows.map((r) => r.bright), 1));
  pts.geometry.dispose();
  pts.geometry = g;
  pts.visible = rows.length > 0;
}

type Seg = { a: [number, number, number]; b: [number, number, number]; ca: RGB; cb: RGB };

function lines(width: number, opts: { dashed?: boolean; additive?: boolean } = {}) {
  const mat = new LineMaterial({
    vertexColors: true,
    linewidth: width,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    dashed: !!opts.dashed,
    dashSize: 6,
    gapSize: 5,
    blending: opts.additive === false ? THREE.NormalBlending : THREE.AdditiveBlending,
  });
  const mesh = new LineSegments2(new LineSegmentsGeometry(), mat);
  mesh.frustumCulled = false;
  return { mesh, width };
}

function fillLines(l: { mesh: LineSegments2 }, segs: Seg[]) {
  if (!segs.length) {
    l.mesh.visible = false;
    return;
  }
  const g = new LineSegmentsGeometry();
  g.setPositions(segs.flatMap((s) => [...s.a, ...s.b]));
  g.setColors(segs.flatMap((s) => [...s.ca, ...s.cb]));
  l.mesh.geometry.dispose();
  l.mesh.geometry = g;
  if ((l.mesh.material as LineMaterial).dashed) l.mesh.computeLineDistances();
  l.mesh.visible = true;
}

/** Split a vertical segment at the today plane so its lower part renders under the glass and the rest above it. */
function split(z0: number, z1: number, zt: number): { below: [number, number] | null; above: [number, number] | null } {
  const lo = Math.min(z0, z1);
  const hi = Math.max(z0, z1);
  if (hi <= zt) return { below: [lo, hi], above: null };
  if (lo >= zt) return { below: null, above: [lo, hi] };
  return { below: [lo, zt], above: [zt, hi] };
}

export function createTimeLayer(ml: Ml, opts: { yearPx: number; onFrame: (p: Projected) => void }) {
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
  let yearPx = opts.yearPx;
  let heightFactor = 0;
  let anim: { from: number; to: number; start: number; ms: number } | null = null;
  // Last frame's screen geometry for picking: pillar foot and top per item.
  let hits: { key: string; x0: number; y0: number; x1: number; y1: number }[] = [];

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
  const beadsBelow = points();
  const beadsAbove = points();
  const anchors = points();
  const marks = points();
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
    links.mesh, linksHot.mesh, anchors, pillarsBelow.mesh, rangesBelow.mesh, beadsBelow, plane,
    pillarsAbove.mesh, pillarsSel.mesh, rangesAbove.mesh, beadsAbove, ruler.mesh, dimDashed.mesh, dimSolid.mesh, marks,
  ];
  ordered.forEach((o, i) => {
    o.renderOrder = i;
    scene.add(o);
  });
  const allLines = [links, linksHot, pillarsBelow, pillarsAbove, pillarsSel, rangesBelow, rangesAbove, ruler, dimSolid, dimDashed];
  const allPoints = [beadsBelow, beadsAbove, anchors, marks];

  const local = (lng: number, lat: number): [number, number] => {
    const m = ml.MercatorCoordinate.fromLngLat([lng, lat]);
    return [(m.x - origin.x) / unit, -(m.y - origin.y) / unit];
  };
  const topOf = (s: Span) => (s.kind === "exact" ? s.day : s.kind === "range" ? s.to : 0) / 365.25;

  function rebuild() {
    const byKey = new Map(items.map((it) => [it.key, it]));
    const emph = (k: string) => focus?.emphasis(k) ?? "normal";
    const zt = todayYears;
    const segs = { pb: [] as Seg[], pa: [] as Seg[], ps: [] as Seg[], rb: [] as Seg[], ra: [] as Seg[] };
    const beads = { b: [] as Parameters<typeof fillPoints>[1], a: [] as Parameters<typeof fillPoints>[1] };
    const rings: Parameters<typeof fillPoints>[1] = [];

    // Dim first, bright last, so highlighted pillars read on top even with additive blending.
    const rank = { dim: 0, normal: 1, hot: 2, sel: 3 } as const;
    for (const it of [...items].sort((x, y) => rank[emph(x.key)] - rank[emph(y.key)])) {
      const e = emph(it.key);
      const k = BRIGHT[e];
      const c = hex(it.color);
      const [x, y] = local(it.lng, it.lat);
      rings.push({ p: [x, y, 0], c, size: e === "dim" ? 8 : e === "sel" ? 20 : 11, shape: 1, bright: k * 0.8 });
      if (it.span.kind === "unknown") continue;
      const top = topOf(it.span);
      // The pillar: a beam of light from the ground anchor up to the date, brightening with height.
      const beam = split(0, it.span.kind === "range" ? it.span.from / 365.25 : top, zt);
      const beamSeg = ([z0, z1]: [number, number]): Seg => ({
        a: [x, y, z0],
        b: [x, y, z1],
        ca: mul(c, (0.05 + (0.45 * z0) / Math.max(top, 1e-6)) * k),
        cb: mul(c, (0.05 + (0.45 * z1) / Math.max(top, 1e-6)) * k),
      });
      if (e === "sel") {
        // A selected pillar is one bright, wide beam drawn above the glass, so it reads through it.
        const z1 = it.span.kind === "range" ? it.span.from / 365.25 : top;
        segs.ps.push({ a: [x, y, 0], b: [x, y, z1], ca: mul(c, 0.25), cb: mul(c, 1.1) });
      } else {
        if (beam.below) segs.pb.push(beamSeg(beam.below));
        if (beam.above) segs.pa.push(beamSeg(beam.above));
      }
      if (it.span.kind === "exact") {
        (top >= zt ? beads.a : beads.b).push({ p: [x, y, top], c, size: SIZE[e], shape: 0, bright: k });
      } else {
        // A month or year: frosted column over the whole span, with rings at both ends. No day is picked.
        const col = split(it.span.from / 365.25, top, zt);
        const colSeg = ([z0, z1]: [number, number]): Seg => ({ a: [x, y, z0], b: [x, y, z1], ca: mul(c, 0.32 * k), cb: mul(c, 0.32 * k) });
        if (col.below) segs.rb.push(colSeg(col.below));
        if (col.above) segs.ra.push(colSeg(col.above));
        for (const z of [it.span.from / 365.25, top])
          (z >= zt ? beads.a : beads.b).push({ p: [x, y, z], c, size: SIZE[e] * 0.9, shape: 1, bright: k });
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

    // Ground links: centre to centre, never a route.
    const link = (hot: boolean) =>
      (focus?.links ?? [])
        .filter((l) => l.hot === hot)
        .flatMap((l): Seg[] => {
          const a = byKey.get(l.a);
          const b = byKey.get(l.b);
          if (!a || !b) return [];
          const k = hot ? 0.95 : 0.22;
          return [{ a: [...local(a.lng, a.lat), 0], b: [...local(b.lng, b.lat), 0], ca: mul(INK, k), cb: mul(INK, k) }];
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
    if (items.length) {
      const xs = items.map((it) => local(it.lng, it.lat));
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
    const metresPerYear = yearPx * metersPerPixel(c.lat, map!.getZoom()) * Math.max(heightFactor, 1e-4);
    const main = new THREE.Matrix4().fromArray(args.defaultProjectionData.mainMatrix as unknown as number[]);
    const localM = new THREE.Matrix4()
      .makeTranslation(origin.x, origin.y, origin.z)
      .scale(new THREE.Vector3(unit, -unit, unit * metresPerYear));
    return main.multiply(localM);
  }

  function project(m: THREE.Matrix4, x: number, y: number, z: number, w: number, h: number) {
    const v = new THREE.Vector4(x, y, z, 1).applyMatrix4(m);
    if (v.w <= 0) return { x: 0, y: 0, on: false };
    const sx = ((v.x / v.w + 1) / 2) * w;
    const sy = ((1 - v.y / v.w) / 2) * h;
    return { x: sx, y: sy, on: sx > -40 && sy > -40 && sx < w + 40 && sy < h + 40 };
  }

  const layer: CustomLayerInterface = {
    id: "gridbridge-time",
    type: "custom",
    renderingMode: "3d",
    onAdd(m, gl) {
      map = m;
      THREE.ColorManagement.enabled = false;
      renderer = new THREE.WebGLRenderer({ canvas: m.getCanvas(), context: gl, antialias: true });
      renderer.autoClear = false;
      renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    },
    onRemove() {
      scene.traverse((o) => {
        const mesh = o as THREE.Mesh;
        mesh.geometry?.dispose();
        (mesh.material as THREE.Material | undefined)?.dispose();
      });
      renderer?.dispose();
      renderer = null;
      map = null;
    },
    render(gl, args) {
      if (!map || !renderer) return;
      if (anim) {
        const t = Math.min((performance.now() - anim.start) / anim.ms, 1);
        heightFactor = anim.from + (anim.to - anim.from) * ease(t);
        if (t >= 1) anim = null;
        map.triggerRepaint();
      }
      const w = gl.drawingBufferWidth;
      const h = gl.drawingBufferHeight;
      const dpr = w / Math.max(map.getCanvas().clientWidth, 1);
      for (const l of allLines) {
        const mat = l.mesh.material as LineMaterial;
        mat.resolution.set(w, h);
        mat.linewidth = l.width * dpr;
        mat.dashSize = 6 * dpr;
        mat.gapSize = 5 * dpr;
      }
      for (const p of allPoints) p.material.uniforms.uDpr.value = dpr;
      (plane.material as THREE.ShaderMaterial).uniforms.uOpacity.value = Math.min(heightFactor * 1.4, 1);
      ruler.mesh.visible = marks.visible = heightFactor > 0.03 && ruler.mesh.geometry.attributes.instanceStart !== undefined;

      const m = frameMatrix(args);
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
      hits = items.map((it) => {
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
    setYearPx(px: number) {
      yearPx = px;
      map?.triggerRepaint();
    },
    /** Grow (1) or flatten (0) the time axis. Facts are untouched either way. */
    setHeight(target: number, ms: number) {
      anim = ms > 0 ? { from: heightFactor, to: target, start: performance.now(), ms } : null;
      if (!anim) heightFactor = target;
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
