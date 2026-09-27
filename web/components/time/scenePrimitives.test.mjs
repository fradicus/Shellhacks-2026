import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";
import { points, fillPoints, lines, fillLines, project, disposeScene, hex } from "./scenePrimitives.ts";
import { bearing } from "./sceneCamera.ts";

test("shared buffers retain attributes, dispose replaced geometry, and preserve line styles", () => {
  const beads = points("test vertex shader", "test fragment shader");
  let disposals = 0;
  beads.geometry.addEventListener("dispose", () => disposals++);
  fillPoints(beads, [{ p: [1, 2, 3], c: [1, 0, 0], size: 10, shape: 2, bright: 0.5 }]);
  assert.equal(disposals, 1);
  assert.deepEqual([...beads.geometry.getAttribute("position").array], [1, 2, 3]);
  assert.deepEqual([...beads.geometry.getAttribute("shape").array], [2]);
  assert.equal(beads.material.vertexShader, "test vertex shader");
  assert.equal(beads.frustumCulled, false);
  fillPoints(beads, []);
  assert.equal(beads.visible, false);

  const stroke = lines(1.1, { dashed: true, dashSize: 5 });
  stroke.mesh.geometry.addEventListener("dispose", () => disposals++);
  fillLines(stroke, [{ a: [0, 0, 0], b: [3, 4, 0], ca: [1, 0, 0], cb: [0, 1, 0] }]);
  assert.equal(disposals, 2);
  assert.equal(stroke.mesh.material.dashSize, 5);
  assert.equal(stroke.mesh.geometry.getAttribute("instanceDistanceEnd").getX(0), 5);
  fillLines(stroke, []);
  assert.equal(stroke.mesh.visible, false);
  const scene = new THREE.Scene();
  scene.add(beads, stroke.mesh);
  let released = 0;
  for (const object of [beads, stroke.mesh]) {
    object.geometry.addEventListener("dispose", () => released++);
    object.material.addEventListener("dispose", () => released++);
  }
  disposeScene(scene, null);
  assert.equal(released, 4);
});

test("screen projection and bearing preserve scene coordinates and offscreen handling", () => {
  assert.deepEqual(project(new THREE.Matrix4(), 0, 0, 0, 800, 600), { x: 400, y: 300, on: true });
  assert.equal(project(new THREE.Matrix4(), 2, 0, 0, 800, 600).on, false);
  const behind = new THREE.Matrix4();
  behind.elements[15] = -1;
  assert.deepEqual(project(behind, 0, 0, 0, 800, 600), { x: 0, y: 0, on: false });
  assert.deepEqual(hex("#ff0000"), [1, 0, 0]);
  assert.equal(bearing({ lat: 0, lon: 0 }, { lat: 0, lon: 1 }), 90);
});
