// History's Three.js MapLibre layer (F37). Same frame as /time: x east / y north in metres from a fixed origin, z in
// YEARS since the axis ground, one matrix per frame into MapLibre's mercator world. What differs is the grammar:
// documented events as glyphs on each pillar, a movable year plane that the pillars grow up to, plan -> actual
// threads, and a ground ripple when the plane passes a documented actual in-service date.
import * as THREE from "three";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
import { LineSegments2 } from "three/examples/jsm/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/examples/jsm/lines/LineSegmentsGeometry.js";
import type { CustomLayerInterface, CustomRenderMethodInput, Map as MlMap } from "maplibre-gl";
import { metersPerPixel } from "@/components/time/timeScale";
import type { Meaning } from "@/lib/history/events";

type Ml = typeof import("maplibre-gl");
type RGB = [number, number, number];
type V3 = [number, number, number];

export type Emphasis = "normal" | "dim" | "hot" | "sel";
export interface Glyph {
  id: string;
  meaning: Meaning;
  /** Years above the axis ground; z0 === z1 for an exact day, a span for a month or a year. */
  z0: number;
  z1: number;
  superseded: boolean;
}
export interface HistoryItem {
  key: string;
  color: string;
  lng: number;
  lat: number;
  glyphs: Glyph[];
  /** Plan -> later documented date, in years; drawn as a brighter thread on the pillar. */
  thread: { z0: number; z1: number } | null;
}
export interface LabelSpec {
  id: string;
  lng: number;
  lat: number;
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
const AMBER: RGB = hex("#f1c27d");
const SKY: RGB = hex("#bfe9ff");
const BRIGHT: Record<Emphasis, number> = { normal: 1, dim: 0.16, hot: 1.5, sel: 1.7 };
const SIZE: Record<Emphasis, number> = { normal: 9, dim: 6, hot: 14, sel: 18 };
const GHOST = 0.13; // events above the plane
const RULE_M = 40_233.6; // 25 statute miles
const RIPPLE_MS = 1400;
const SHAPE: Record<Meaning, number> = { actual: 0, plan: 1, other: 2 };

// Beads (0), rings (1), squares (2), halos (3), ruler ticks (4). Additive, so draw order within a pass is free.
const POINT_VS = /* glsl */ `
  attribute vec3 tint; attribute float size; attribute float shape; attribute float bright;
  uniform float uDpr; uniform float uW0;
  varying vec3 vTint; varying float vShape; varying float vBright; varying float vFade;
  void main() {
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * uDpr;
    vTint = tint; vShape = shape; vBright = bright;
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
      float core = smoothstep(0.42, 0.24, r);
      float glow = pow(max(1.0 - r, 0.0), 2.2);
      col = mix(vTint * 1.1, vec3(1.0, 0.97, 0.92), core * 0.85);
      a = max(core, glow * 0.8);
    } else if (vShape < 1.5) {
      float ring = smoothstep(0.16, 0.03, abs(r - 0.66));
      if (ring < 0.02) discard;
      col = vTint; a = ring;
    } else if (vShape < 2.5) {
      float d = max(abs(c.x), abs(c.y));
      float edge = smoothstep(0.14, 0.02, abs(d - 0.52));
      float fill = step(d, 0.52) * 0.35;
      if (edge + fill < 0.02) discard;
      col = vTint; a = max(edge, fill);
    } else if (vShape < 3.5) {
      if (r > 1.0) discard;
      col = vTint; a = exp(-r * r * 4.5) * 0.5;
    } else {
      if (abs(c.y) > 0.11 || abs(c.x) > 0.95) discard;
      col = vTint; a = 0.9;
    }
    gl_FragColor = vec4(col * vBright * vFade, a * min(vBright, 1.0) * vFade);
  }`;

// The year plane: warm engraved glass. A 10-mile grid, concentric contour rings and a soft rim, fading to its edges.
const PLANE_VS = /* glsl */ `
  varying vec2 vUv; varying vec2 vPos;
  void main() {
    vUv = uv; vPos = (modelMatrix * vec4(position, 1.0)).xy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;
const PLANE_FS = /* glsl */ `
  uniform vec3 uColor; uniform float uGrid; uniform float uOpacity; uniform float uGlow;
  varying vec2 vUv; varying vec2 vPos;
  void main() {
    vec2 g = vPos / uGrid;
    vec2 w = abs(fract(g - 0.5) - 0.5) / max(fwidth(g), vec2(1e-6));
    float line = 1.0 - min(min(w.x, w.y), 1.0);
    float d = length(vUv - 0.5) * 2.0;
    float fade = smoothstep(1.0, 0.2, d);
    float contour = 1.0 - min(abs(fract(d * 7.0 - 0.5) - 0.5) / max(fwidth(d * 7.0), 1e-6), 1.0);
    float rim = smoothstep(0.035, 0.0, abs(d - 0.93)) * 0.45;
    gl_FragColor = vec4(uColor, (0.045 + uGlow * 0.05 + line * 0.1 + contour * 0.05 + rim) * fade * uOpacity);
  }`;

type Pt = { p: V3; c: RGB; size: number; shape: number; bright: number };
type Seg = { a: V3; b: V3; ca: RGB; cb: RGB };

function points() {
  const mat = new THREE.ShaderMaterial({
    vertexShader: POINT_VS,
    fragmentShader: POINT_FS,
    uniforms: { uDpr: { value: 1 }, uW0: { value: 0 } },
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const pts = new THREE.Points(new THREE.BufferGeometry(), mat);
  pts.frustumCulled = false;
  return pts;
}

function fillPoints(pts: THREE.Points<THREE.BufferGeometry, THREE.ShaderMaterial>, rows: Pt[]) {
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

function lines(width: number, dashed = false) {
  const mat = new LineMaterial({
    vertexColors: true,
    linewidth: width,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    dashed,
    dashSize: 5,
    gapSize: 5,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new LineSegments2(new LineSegmentsGeometry(), mat);
  mesh.frustumCulled = false;
  return { mesh, width, dashed };
}

function fillLines(l: ReturnType<typeof lines>, segs: Seg[]) {
  if (!segs.length) {
    l.mesh.visible = false;
    return;
  }
  const g = new LineSegmentsGeometry();
  g.setPositions(segs.flatMap((s) => [...s.a, ...s.b]));
  g.setColors(segs.flatMap((s) => [...s.ca, ...s.cb]));
  l.mesh.geometry.dispose();
  l.mesh.geometry = g;
  if (l.dashed) l.mesh.computeLineDistances();
  l.mesh.visible = true;
}

/** A unit circle on the ground: the 25-mile research radius around a /time origin. */
function circle() {
  const pos: number[] = [];
  const n = 144;
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2;
    const a1 = ((i + 1) / n) * Math.PI * 2;
    pos.push(Math.cos(a0), Math.sin(a0), 0, Math.cos(a1), Math.sin(a1), 0);
  }
  const g = new LineSegmentsGeometry();
  g.setPositions(pos);
  const mat = new LineMaterial({
    color: 0xffffff,
    linewidth: 1.4,
    transparent: true,
    opacity: 0.55,
    dashed: true,
    dashSize: 7,
    gapSize: 6,
    depthTest: false,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new LineSegments2(g, mat);
  mesh.computeLineDistances();
  mesh.frustumCulled = false;
  mesh.visible = false;
  return { mesh, width: 1.4, dashed: true };
}

export function createHistoryLayer(ml: Ml, opts: { yearPx: number; onFrame: (p: Projected) => void }) {
  let map: MlMap | null = null;
  let renderer: THREE.WebGLRenderer | null = null;
  const scene = new THREE.Scene();
  const camera = new THREE.Camera();
  let origin = ml.MercatorCoordinate.fromLngLat([-76, 40]);
  let unit = origin.meterInMercatorCoordinateUnits();

  let items: HistoryItem[] = [];
  let topYears = 1;
  let todayYears = 0;
  let plane = 0;
  let emphasis: (key: string) => Emphasis = () => "normal";
  let rulerAt = { lng: -70, lat: 40 };
  let labels: LabelSpec[] = [];
  let yearPx = opts.yearPx;
  let heightFactor = 0;
  let anim: { from: number; to: number; start: number; ms: number } | null = null;
  let ripples: { x: number; y: number; c: RGB; start: number }[] = [];
  let originAt: { x: number; y: number; r: number } | null = null;
  let hits: { key: string; x0: number; y0: number; x1: number; y1: number }[] = [];

  const beamsLit = lines(1.5);
  const beamsGhost = lines(1, true);
  const beamsSel = lines(3);
  const threads = lines(3.4);
  const spans = lines(6);
  const ruler = lines(1.2);
  const ghostPillar = lines(2, true);
  const radius = circle();
  const anchors = points();
  const halos = points();
  const glyphsBelow = points();
  const glyphsAbove = points();
  const marks = points();
  const rippleDots = points();
  const sheet = new THREE.Mesh(
    new THREE.PlaneGeometry(1, 1),
    new THREE.ShaderMaterial({
      vertexShader: PLANE_VS,
      fragmentShader: PLANE_FS,
      uniforms: {
        uColor: { value: new THREE.Vector3(...AMBER) },
        uGrid: { value: 16_093.44 },
        uOpacity: { value: 1 },
        uGlow: { value: 0 },
      },
      transparent: true,
      depthTest: false,
      depthWrite: false,
      side: THREE.DoubleSide,
    }),
  );
  sheet.frustumCulled = false;

  // Ground, everything under the plane, the plane, then what stands above it and the drafting marks.
  const ordered: THREE.Object3D[] = [
    radius.mesh, anchors, rippleDots, halos, beamsLit.mesh, threads.mesh, spans.mesh, glyphsBelow, sheet,
    beamsGhost.mesh, ghostPillar.mesh, beamsSel.mesh, glyphsAbove, ruler.mesh, marks,
  ];
  ordered.forEach((o, i) => {
    o.renderOrder = i;
    scene.add(o);
  });
  const allLines = [beamsLit, beamsGhost, beamsSel, threads, spans, ruler, ghostPillar, radius];
  const allPoints = [anchors, halos, glyphsBelow, glyphsAbove, marks, rippleDots];

  const local = (lng: number, lat: number): [number, number] => {
    const m = ml.MercatorCoordinate.fromLngLat([lng, lat]);
    return [(m.x - origin.x) / unit, -(m.y - origin.y) / unit];
  };
  const topOf = (it: HistoryItem) => Math.max(0, ...it.glyphs.map((g) => g.z1));

  function rebuild() {
    const segs = { lit: [] as Seg[], ghost: [] as Seg[], sel: [] as Seg[], thread: [] as Seg[], span: [] as Seg[] };
    const below: Pt[] = [];
    const above: Pt[] = [];
    const ground: Pt[] = [];
    const glow: Pt[] = [];
    const rank = { dim: 0, normal: 1, hot: 2, sel: 3 } as const;
    for (const it of [...items].sort((a, b) => rank[emphasis(a.key)] - rank[emphasis(b.key)])) {
      const e = emphasis(it.key);
      const k = BRIGHT[e];
      const c = hex(it.color);
      const [x, y] = local(it.lng, it.lat);
      const top = topOf(it);
      const lit = Math.min(top, plane);
      const reached = it.glyphs.some((g) => g.z0 <= plane);
      ground.push({ p: [x, y, 0], c, size: e === "sel" ? 18 : e === "dim" ? 6 : 9, shape: 1, bright: k * (reached ? 0.8 : 0.3) });
      if (reached && e !== "dim") glow.push({ p: [x, y, 0], c, size: e === "sel" ? 44 : 24, shape: 3, bright: k * 0.3 });
      // The pillar grows up to the plane; what the record documents later stands above it as a faint dashed ghost.
      if (lit > 0) {
        if (e === "sel") segs.sel.push({ a: [x, y, 0], b: [x, y, lit], ca: mul(c, 0.25), cb: mul(c, 1.1) });
        else segs.lit.push({ a: [x, y, 0], b: [x, y, lit], ca: mul(c, 0.05 * k), cb: mul(c, 0.5 * k) });
      }
      if (top > plane) segs.ghost.push({ a: [x, y, Math.max(plane, 0)], b: [x, y, top], ca: mul(c, 0.12 * k), cb: mul(c, 0.12 * k) });
      if (it.thread) {
        const z0 = Math.min(it.thread.z0, it.thread.z1);
        const z1 = Math.min(Math.max(it.thread.z0, it.thread.z1), plane);
        if (z1 > z0) segs.thread.push({ a: [x, y, z0], b: [x, y, z1], ca: mul(INK, 0.55 * k), cb: mul(INK, 0.55 * k) });
      }
      for (const g of it.glyphs) {
        const on = g.z0 <= plane;
        const b = k * (on ? (g.superseded ? 0.55 : 1) : GHOST);
        const size = SIZE[e] * (g.meaning === "actual" ? 1.05 : 1.15);
        if (g.z1 > g.z0) {
          // A month or a year: the whole span as a frosted column, open rings at both ends. No day is picked.
          segs.span.push({ a: [x, y, g.z0], b: [x, y, g.z1], ca: mul(c, 0.3 * b), cb: mul(c, 0.3 * b) });
          for (const z of [g.z0, g.z1]) (z > plane ? above : below).push({ p: [x, y, z], c, size: size * 0.8, shape: 1, bright: b });
        } else {
          (g.z0 > plane ? above : below).push({ p: [x, y, g.z0], c: g.meaning === "other" ? INK : c, size, shape: SHAPE[g.meaning], bright: b });
          if (on && e !== "dim" && g.meaning === "actual") glow.push({ p: [x, y, g.z0], c, size: size * 3, shape: 3, bright: k * 0.5 });
        }
      }
    }
    fillLines(beamsLit, segs.lit);
    fillLines(beamsGhost, segs.ghost);
    fillLines(beamsSel, segs.sel);
    fillLines(threads, segs.thread);
    fillLines(spans, segs.span);
    fillPoints(glyphsBelow, below);
    fillPoints(glyphsAbove, above);
    fillPoints(anchors, ground);
    fillPoints(halos, glow);

    // The ruler: a spine with a tick per year, an amber tick at the plane and a sky tick at the analysis date.
    const [rx, ry] = local(rulerAt.lng, rulerAt.lat);
    const top = Math.ceil(topYears);
    fillLines(ruler, [{ a: [rx, ry, 0], b: [rx, ry, top + 0.3], ca: mul(INK, 0.14), cb: mul(INK, 0.5) }]);
    const tickRows: Pt[] = [];
    for (let yv = 0; yv <= top; yv++) tickRows.push({ p: [rx, ry, yv], c: INK, size: yv % 5 === 0 ? 16 : 10, shape: 4, bright: 0.5 });
    if (todayYears >= 0 && todayYears <= top + 0.3) tickRows.push({ p: [rx, ry, todayYears], c: SKY, size: 20, shape: 4, bright: 1 });
    tickRows.push({ p: [rx, ry, plane], c: AMBER, size: 26, shape: 4, bright: 1.3 });
    fillPoints(marks, tickRows);

    if (originAt) {
      fillLines(ghostPillar, [{ a: [originAt.x, originAt.y, 0], b: [originAt.x, originAt.y, top + 0.3], ca: mul(INK, 0.9), cb: mul(INK, 0.25) }]);
      radius.mesh.position.set(originAt.x, originAt.y, 0);
      radius.mesh.scale.set(originAt.r, originAt.r, 1);
      radius.mesh.updateMatrixWorld();
      radius.mesh.visible = true;
    } else {
      ghostPillar.mesh.visible = false;
      radius.mesh.visible = false;
    }

    if (items.length) {
      const xs = items.map((it) => local(it.lng, it.lat));
      const minX = Math.min(...xs.map((p) => p[0]));
      const maxX = Math.max(...xs.map((p) => p[0]));
      const minY = Math.min(...xs.map((p) => p[1]));
      const maxY = Math.max(...xs.map((p) => p[1]));
      const size = Math.max(maxX - minX, maxY - minY, 60_000) * 1.5;
      sheet.scale.set(size, size, 1);
      sheet.position.set((minX + maxX) / 2, (minY + maxY) / 2, plane);
      sheet.visible = true;
    } else sheet.visible = false;
    map?.triggerRepaint();
  }

  function frameMatrix(args: CustomRenderMethodInput): THREE.Matrix4 {
    const c = map!.getCenter();
    const metresPerYear = yearPx * metersPerPixel(c.lat, map!.getZoom()) * Math.max(heightFactor, 1e-4);
    const main = new THREE.Matrix4().fromArray(args.defaultProjectionData.mainMatrix as unknown as number[]);
    return main.multiply(
      new THREE.Matrix4().makeTranslation(origin.x, origin.y, origin.z).scale(new THREE.Vector3(unit, -unit, unit * metresPerYear)),
    );
  }

  function project(m: THREE.Matrix4, x: number, y: number, z: number, w: number, h: number) {
    const v = new THREE.Vector4(x, y, z, 1).applyMatrix4(m);
    if (v.w <= 0) return { x: 0, y: 0, on: false };
    const sx = ((v.x / v.w + 1) / 2) * w;
    const sy = ((1 - v.y / v.w) / 2) * h;
    return { x: sx, y: sy, on: sx > -40 && sy > -40 && sx < w + 40 && sy < h + 40 };
  }

  const layer: CustomLayerInterface = {
    id: "gridbridge-history",
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
      const now = performance.now();
      if (anim) {
        const t = Math.min((now - anim.start) / anim.ms, 1);
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
        mat.dashSize = 5 * dpr;
        mat.gapSize = 5 * dpr;
      }
      for (const p of allPoints) p.material.uniforms.uDpr.value = dpr;
      const uniforms = (sheet.material as THREE.ShaderMaterial).uniforms;
      uniforms.uOpacity.value = Math.min(heightFactor * 1.4, 1);
      ruler.mesh.visible = marks.visible = heightFactor > 0.03;

      // Ground ripples: one expanding ring per actual in-service date the plane just passed.
      ripples = ripples.filter((r) => now - r.start < RIPPLE_MS);
      if (ripples.length || rippleDots.visible) fillPoints(
        rippleDots,
        ripples.map((r) => {
          const t = Math.max(0, (now - r.start) / RIPPLE_MS);
          return { p: [r.x, r.y, 0], c: r.c, size: 10 + 70 * ease(t), shape: 1, bright: 1.3 * (1 - t) };
        }),
      );
      uniforms.uGlow.value = Math.min(ripples.length / 6, 1);
      if (ripples.length) map.triggerRepaint();

      const m = frameMatrix(args);
      const cc = map.getCenter();
      const w0 = new THREE.Vector4(...local(cc.lng, cc.lat), 0, 1).applyMatrix4(m).w;
      for (const p of allPoints) p.material.uniforms.uW0.value = w0 > 0 ? w0 : 0;
      camera.projectionMatrix.copy(m);
      camera.projectionMatrixInverse.copy(m).invert();
      renderer.resetState();
      renderer.setViewport(0, 0, w, h);
      renderer.render(scene, camera);

      const cw = map.getCanvas().clientWidth;
      const ch = map.getCanvas().clientHeight;
      const out: Projected = new Map();
      for (const l of labels) out.set(l.id, project(m, ...local(l.lng, l.lat), l.years, cw, ch));
      hits = items.map((it) => {
        const [x, y] = local(it.lng, it.lat);
        const foot = project(m, x, y, 0, cw, ch);
        const top = project(m, x, y, topOf(it), cw, ch);
        return { key: it.key, x0: foot.x, y0: foot.y, x1: top.x, y1: top.y };
      });
      opts.onFrame(out);
    },
  };

  return {
    layer,
    setItems(next: HistoryItem[], top: number, today: number) {
      items = next;
      topYears = Math.max(top, 1);
      todayYears = today;
      if (next.length) {
        const lng = next.reduce((s, it) => s + it.lng, 0) / next.length;
        const lat = next.reduce((s, it) => s + it.lat, 0) / next.length;
        origin = ml.MercatorCoordinate.fromLngLat([lng, lat]);
        unit = origin.meterInMercatorCoordinateUnits();
      }
      rebuild();
    },
    setFocus(f: { emphasis: (key: string) => Emphasis; ruler: { lng: number; lat: number } }) {
      emphasis = f.emphasis;
      rulerAt = f.ruler;
      rebuild();
    },
    /** Move the year plane. With `ripple`, every actual event it passes on the way up sends a ring across the ground. */
    setPlane(years: number, ripple = false) {
      if (ripple && years > plane) {
        const now = performance.now();
        for (const it of items)
          for (const g of it.glyphs)
            if (g.meaning === "actual" && g.z0 > plane && g.z0 <= years) {
              const [x, y] = local(it.lng, it.lat);
              ripples.push({ x, y, c: hex(it.color), start: now });
            }
        // ponytail: ripple cap keeps a dense year cheap; raise it if a region ever needs every ring at once.
        if (ripples.length > 240) ripples = ripples.slice(-240);
      }
      plane = years;
      rebuild();
    },
    setOrigin(o: { lng: number; lat: number } | null) {
      if (!o) originAt = null;
      else {
        const [x, y] = local(o.lng, o.lat);
        const r = (RULE_M * ml.MercatorCoordinate.fromLngLat([o.lng, o.lat]).meterInMercatorCoordinateUnits()) / unit;
        originAt = { x, y, r };
      }
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
    /** Nearest pillar to a screen point, within `radius` CSS pixels. */
    pick(px: number, py: number, rad = 12): string | null {
      let best: string | null = null;
      let bestD = rad;
      for (const hh of hits) {
        const dx = hh.x1 - hh.x0;
        const dy = hh.y1 - hh.y0;
        const len2 = dx * dx + dy * dy;
        const t = len2 ? Math.max(0, Math.min(1, ((px - hh.x0) * dx + (py - hh.y0) * dy) / len2)) : 0;
        const d = Math.hypot(px - (hh.x0 + t * dx), py - (hh.y0 + t * dy)) + (1 - t) * 3;
        if (d < bestD) {
          bestD = d;
          best = hh.key;
        }
      }
      return best;
    },
  };
}

export type HistoryLayer = ReturnType<typeof createHistoryLayer>;
