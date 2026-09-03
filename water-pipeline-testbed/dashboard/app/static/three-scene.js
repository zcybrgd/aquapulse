/**
 * 3D pipeline digital twin.
 *
 * Renders the physical simulation only: pipes, a reservoir, spinning pumps,
 * valve gates, a particle stream whose speed follows the real flow rate,
 * and a leak spray that appears exactly when a leak-type fault is
 * physically active on that segment. None of this reflects a cybersecurity
 * verdict -- it's the ground-truth physical state, the same thing a plant
 * operator would see on a real HMI.
 *
 * The only place a classification from the Anomaly Investigation Agent
 * touches this scene is `setVerdict()`, which lights a small ring at the
 * valve -- a distinct, clearly-separate overlay, and only ever called from
 * app.js after an `aia:results` message actually arrives. Nothing here is
 * ever set in response to a fault injection by itself.
 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const PARTICLE_COUNT = 26;
const LEAK_PARTICLE_COUNT = 18;
const PIPE_START_X = -8;
const PIPE_END_X = 8;

let scene, camera, renderer, controls, clock, containerEl, gridHelper;
const clusterObjects = {};

const TIER_COLORS = { 1: 0xeab308, 2: 0xf97316, 3: 0xef4444 };
const CLASS_COLORS = {
  confirmed_instrument_fault: 0x94a3b8,
  likely_connectivity_artifact: 0x38bdf8,
  insufficient_data: 0xa855f7,
};
const LEAK_FAULT_TYPES = new Set(["leak", "pipe_rupture", "pressure_drop"]);

const GRID_COLORS = {
  dark: { main: 0x2a3446, sub: 0x161c27 },
  light: { main: 0xb9c2d0, sub: 0xdde3ec },
};

function readInitialTheme() {
  return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}

function applyGridTheme(theme) {
  if (!scene) return;
  if (gridHelper) {
    scene.remove(gridHelper);
    gridHelper.geometry.dispose();
    gridHelper.material.dispose();
  }
  const colors = GRID_COLORS[theme] || GRID_COLORS.dark;
  const grid = new THREE.GridHelper(44, 34, colors.main, colors.sub);
  grid.material.transparent = true;
  grid.material.opacity = theme === "light" ? 0.55 : 0.9;
  scene.add(grid);
  gridHelper = grid;
}

/** Called from app.js whenever the user flips the light/dark toggle. Only
 * the grid needs to change here -- pipe/pump/valve materials are neutral
 * industrial tones that read fine against either background, and the
 * viewport's own background gradient is handled by CSS variables. */
export function setTheme(theme) {
  applyGridTheme(theme === "light" ? "light" : "dark");
}

export function init(container, segments) {
  containerEl = container;
  scene = new THREE.Scene();

  const width = container.clientWidth || 800;
  const height = container.clientHeight || 420;

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 200);
  camera.position.set(2, 9, 17);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(width, height);
  container.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 6;
  controls.maxDistance = 32;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.update();

  scene.add(new THREE.AmbientLight(0x9fb4c9, 0.7));
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(8, 14, 6);
  scene.add(dir);

  const grid = new THREE.GridHelper(44, 34, 0x1c2531, 0x141a24);
  scene.add(grid);
  gridHelper = grid;
  applyGridTheme(readInitialTheme());

  buildReservoir();
  buildPipes(segments);

  clock = new THREE.Clock();
  window.addEventListener("resize", onResize);
  animate();
}

function buildReservoir() {
  const tank = new THREE.Mesh(
    new THREE.CylinderGeometry(2.1, 2.3, 3, 24),
    new THREE.MeshStandardMaterial({ color: 0x141a24, metalness: 0.3, roughness: 0.6 }),
  );
  tank.position.set(-10.5, 1.5, 0);
  scene.add(tank);

  const water = new THREE.Mesh(
    new THREE.CylinderGeometry(1.9, 1.9, 0.15, 24),
    new THREE.MeshStandardMaterial({ color: 0x2dd4bf, emissive: 0x0c3d37, roughness: 0.3 }),
  );
  water.position.set(-10.5, 2.95, 0);
  scene.add(water);
}

function buildPipes(segments) {
  const n = segments.length || 1;
  const spacingZ = 3.4;
  const startZ = -((n - 1) * spacingZ) / 2;
  const pipeLength = PIPE_END_X - PIPE_START_X;

  segments.forEach((seg, i) => {
    const z = startZ + i * spacingZ;
    const cid = seg.sensor_cluster_id;
    const group = new THREE.Group();
    group.position.z = z;

    const pipe = new THREE.Mesh(
      new THREE.CylinderGeometry(0.22, 0.22, pipeLength, 16),
      new THREE.MeshStandardMaterial({ color: 0x232b38, metalness: 0.5, roughness: 0.4 }),
    );
    pipe.rotation.z = Math.PI / 2;
    pipe.position.set((PIPE_START_X + PIPE_END_X) / 2, 1, 0);
    group.add(pipe);

    // Pump: a pivot group at identity rotation so we can spin it around the
    // world X axis unambiguously (pipe-aligned mesh nested inside).
    const pumpPivot = new THREE.Group();
    pumpPivot.position.set(PIPE_START_X + 1.2, 1, 0);
    const pumpMesh = new THREE.Mesh(
      new THREE.CylinderGeometry(0.4, 0.4, 0.5, 6),
      new THREE.MeshStandardMaterial({ color: 0x2dd4bf, metalness: 0.4, roughness: 0.35, emissive: 0x0a3a34 }),
    );
    pumpMesh.rotation.z = Math.PI / 2;
    pumpPivot.add(pumpMesh);
    group.add(pumpPivot);

    const valveHousing = new THREE.Mesh(
      new THREE.BoxGeometry(0.5, 0.9, 0.9),
      new THREE.MeshStandardMaterial({ color: 0x1c2431, metalness: 0.5, roughness: 0.5 }),
    );
    valveHousing.position.set(PIPE_END_X - 0.6, 1, 0);
    group.add(valveHousing);

    const valveGate = new THREE.Mesh(
      new THREE.BoxGeometry(0.08, 0.5, 0.5),
      new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.3, roughness: 0.5 }),
    );
    valveGate.position.set(PIPE_END_X - 0.6, 1.22, 0);
    group.add(valveGate);

    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.55, 0.045, 12, 32),
      new THREE.MeshBasicMaterial({ color: 0x2dd4bf, transparent: true, opacity: 0.9 }),
    );
    ring.position.set(PIPE_END_X - 0.6, 1, 0);
    ring.rotation.x = Math.PI / 2;
    ring.visible = false;
    group.add(ring);

    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const tvals = new Float32Array(PARTICLE_COUNT);
    for (let p = 0; p < PARTICLE_COUNT; p++) tvals[p] = p / PARTICLE_COUNT;
    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const points = new THREE.Points(
      geom,
      new THREE.PointsMaterial({ color: 0x7dd8ce, size: 0.14, sizeAttenuation: true, transparent: true, opacity: 0.9 }),
    );
    group.add(points);

    const leakGeom = new THREE.BufferGeometry();
    leakGeom.setAttribute("position", new THREE.BufferAttribute(new Float32Array(LEAK_PARTICLE_COUNT * 3), 3));
    const leakPoints = new THREE.Points(
      leakGeom,
      new THREE.PointsMaterial({ color: 0x60a5fa, size: 0.09, transparent: true, opacity: 0.85 }),
    );
    leakPoints.visible = false;
    group.add(leakPoints);

    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    const texture = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false }));
    sprite.scale.set(2.6, 0.65, 1);
    sprite.position.set(PIPE_START_X + 3.6, 2.15, 0);
    group.add(sprite);

    scene.add(group);

    clusterObjects[cid] = {
      pump: pumpPivot,
      valveGate,
      ring,
      points,
      tvals,
      leakPoints,
      leakVel: new Float32Array(LEAK_PARTICLE_COUNT * 3),
      leakLife: new Float32Array(LEAK_PARTICLE_COUNT),
      leakActive: false,
      leakOriginT: 0.55,
      canvas,
      ctx,
      texture,
      baselinePressure: seg.baseline_pressure_psi,
      baselineFlow: seg.baseline_flow_lps,
      flowRatio: 1,
      pumpAngle: 0,
      valveTargetOffset: 0.22,
      valveCurrentOffset: 0.22,
      clusterId: cid,
    };

    drawLabel(clusterObjects[cid], seg.baseline_pressure_psi, seg.baseline_flow_lps);
  });
}

function drawLabel(obj, pressure, flow) {
  const ctx = obj.ctx;
  ctx.clearRect(0, 0, obj.canvas.width, obj.canvas.height);
  ctx.font = "600 22px Inter, sans-serif";
  ctx.fillStyle = "#e8ebf1";
  ctx.textBaseline = "middle";
  ctx.fillText(obj.clusterId.replace("cluster-desert-", "CL-"), 4, 20);
  ctx.font = "400 17px monospace";
  ctx.fillStyle = "#9aa4b8";
  ctx.fillText(`${pressure.toFixed(1)} psi \u00b7 ${flow.toFixed(1)} L/s`, 4, 46);
  obj.texture.needsUpdate = true;
}

export function updateCluster(cid, data) {
  const obj = clusterObjects[cid];
  if (!obj) return;

  obj.flowRatio = obj.baselineFlow > 0 ? Math.max(0, data.flow_rate_lps / obj.baselineFlow) : 0;
  drawLabel(obj, data.pressure_psi, data.flow_rate_lps);

  let targetOffset = 0.22; // neutral, partially-open resting position
  if (data.active_fault === "valve_stuck_closed" || data.active_fault === "pump_failure") {
    targetOffset = 0;
  } else if (data.active_fault === "valve_stuck_open") {
    targetOffset = 0.42;
  }
  obj.valveTargetOffset = targetOffset;
  obj.leakActive = LEAK_FAULT_TYPES.has(data.active_fault);
  obj.leakPoints.visible = obj.leakActive;
}

export function setVerdict(cid, classification, tier) {
  const obj = clusterObjects[cid];
  if (!obj) return;
  obj.ring.visible = true;
  const color = classification === "confirmed_anomaly" ? (TIER_COLORS[tier] || 0xeab308) : (CLASS_COLORS[classification] || 0x2dd4bf);
  obj.ring.material.color.setHex(color);
}

export function clearAllVerdicts() {
  for (const cid in clusterObjects) clusterObjects[cid].ring.visible = false;
}

function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.1);

  for (const cid in clusterObjects) {
    const obj = clusterObjects[cid];

    const tSpeed = 0.05 + obj.flowRatio * 0.15; // fraction of pipe length per second
    const posAttr = obj.points.geometry.attributes.position;
    for (let p = 0; p < PARTICLE_COUNT; p++) {
      obj.tvals[p] += tSpeed * dt;
      if (obj.tvals[p] > 1) obj.tvals[p] -= 1;
      const x = PIPE_START_X + obj.tvals[p] * (PIPE_END_X - PIPE_START_X);
      posAttr.array[p * 3] = x;
      posAttr.array[p * 3 + 1] = 1;
      posAttr.array[p * 3 + 2] = 0;
    }
    posAttr.needsUpdate = true;

    obj.pumpAngle += dt * (2 + obj.flowRatio * 10);
    obj.pump.rotation.x = obj.pumpAngle;

    obj.valveCurrentOffset += (obj.valveTargetOffset - obj.valveCurrentOffset) * Math.min(1, dt * 3);
    obj.valveGate.position.y = 1 + obj.valveCurrentOffset;

    if (obj.leakActive) {
      const lpos = obj.leakPoints.geometry.attributes.position;
      const originX = PIPE_START_X + obj.leakOriginT * (PIPE_END_X - PIPE_START_X);
      for (let p = 0; p < LEAK_PARTICLE_COUNT; p++) {
        obj.leakLife[p] -= dt;
        if (obj.leakLife[p] <= 0) {
          lpos.array[p * 3] = originX + (Math.random() - 0.5) * 0.1;
          lpos.array[p * 3 + 1] = 1.1;
          lpos.array[p * 3 + 2] = (Math.random() - 0.5) * 0.1;
          obj.leakVel[p * 3] = (Math.random() - 0.5) * 0.4;
          obj.leakVel[p * 3 + 1] = Math.random() * 1.2 + 0.4;
          obj.leakVel[p * 3 + 2] = (Math.random() - 0.5) * 0.4;
          obj.leakLife[p] = 0.6 + Math.random() * 0.6;
        } else {
          obj.leakVel[p * 3 + 1] -= dt * 2.2;
          lpos.array[p * 3] += obj.leakVel[p * 3] * dt;
          lpos.array[p * 3 + 1] += obj.leakVel[p * 3 + 1] * dt;
          lpos.array[p * 3 + 2] += obj.leakVel[p * 3 + 2] * dt;
        }
      }
      lpos.needsUpdate = true;
    }

    if (obj.ring.visible) {
      const s = 1 + Math.sin(performance.now() / 400) * 0.05;
      obj.ring.scale.set(s, s, s);
    }
  }

  controls.update();
  renderer.render(scene, camera);
}

function onResize() {
  if (!containerEl || !renderer || !camera) return;
  const width = containerEl.clientWidth;
  const height = containerEl.clientHeight;
  if (width === 0 || height === 0) return;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

window.PipelineScene = { init, updateCluster, setVerdict, clearAllVerdicts, setTheme };
