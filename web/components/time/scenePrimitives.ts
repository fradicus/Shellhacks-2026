// Shared Three.js drawing primitives. Scene shaders, dates and interaction policy stay with each view.
import * as THREE from "three";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
import { LineSegments2 } from "three/examples/jsm/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/examples/jsm/lines/LineSegmentsGeometry.js";
import type { Map as MlMap } from "maplibre-gl";

export type RGB = [number, number, number];

export const hex = (h: string): RGB => {
  const n = parseInt(h.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
};
export const mul = (c: RGB, k: number): RGB => [c[0] * k, c[1] * k, c[2] * k];
export const ease = (t: number) => 1 - (1 - t) ** 3;

export function points(vertexShader: string, fragmentShader: string): THREE.Points<THREE.BufferGeometry, THREE.ShaderMaterial> {
  const mat = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
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

export function fillPoints(
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

export type Seg = { a: [number, number, number]; b: [number, number, number]; ca: RGB; cb: RGB };

export function lines(width: number, opts: { dashed?: boolean; dashSize?: number; additive?: boolean } = {}) {
  const mat = new LineMaterial({
    vertexColors: true,
    linewidth: width,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    dashed: !!opts.dashed,
    dashSize: opts.dashSize ?? 6,
    gapSize: 5,
    blending: opts.additive === false ? THREE.NormalBlending : THREE.AdditiveBlending,
  });
  const mesh = new LineSegments2(new LineSegmentsGeometry(), mat);
  mesh.frustumCulled = false;
  return { mesh, width };
}

export function fillLines(l: { mesh: LineSegments2 }, segs: Seg[]) {
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

export function project(m: THREE.Matrix4, x: number, y: number, z: number, w: number, h: number) {
  const v = new THREE.Vector4(x, y, z, 1).applyMatrix4(m);
  if (v.w <= 0) return { x: 0, y: 0, on: false };
  const sx = ((v.x / v.w + 1) / 2) * w;
  const sy = ((1 - v.y / v.w) / 2) * h;
  return { x: sx, y: sy, on: sx > -40 && sy > -40 && sx < w + 40 && sy < h + 40 };
}


export function createRenderer(map: MlMap, gl: WebGLRenderingContext | WebGL2RenderingContext) {
  THREE.ColorManagement.enabled = false;
  const renderer = new THREE.WebGLRenderer({ canvas: map.getCanvas(), context: gl, antialias: true });
  renderer.autoClear = false;
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  return renderer;
}

export function disposeScene(scene: THREE.Scene, renderer: THREE.WebGLRenderer | null) {
  scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    mesh.geometry?.dispose();
    (mesh.material as THREE.Material | undefined)?.dispose();
  });
  renderer?.dispose();
}
