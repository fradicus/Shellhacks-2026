/** Truck artwork adapted from the user-supplied GridBridge HTML (GridBridge_updated / GridBridge_24df intent).
 * Decorative illustration only; no operational fleet data is represented.
 * Motion: cab faces left; the truck scrolls continuously right → left across the road.
 * @param {HTMLCanvasElement} cv
 * @param {boolean | (() => boolean)} paused  static flag or live getter (so Pause does not remount)
 * @returns {() => void}
 */
export function startRoadScene(cv, paused) {
  const ctx = cv.getContext("2d");
  if (!ctx) return () => {};
  const isPaused = () => (typeof paused === "function" ? !!paused() : !!paused);
  const DISP = '"Public Sans", sans-serif';
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  let W = 1, H = 1, DPR = 1, L = 1, roadY = 1, frameId = 0, visible = true, disposed = false;
  let scrollT = 0, lastNow = null;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const motes = Array.from({ length: 50 }, (_, i) => ({
    x: (i * 0.618) % 1,
    y: (i * 0.371) % 1,
    v: 0.2 + (i % 5) * 0.1,
    r: 0.6 + (i % 3) * 0.3,
    p: i,
  }));

  function resize() {
    const box = cv.getBoundingClientRect();
    W = box.width;
    H = box.height;
    DPR = Math.min(2, devicePixelRatio || 1);
    cv.width = Math.round(W * DPR);
    cv.height = Math.round(H * DPR);
    L = W < 700 ? W * 0.95 : Math.min(W * 0.59, 900);
    roadY = H * 0.83;
    render(performance.now());
  }

  function beam(xf, h, t) {
    if (h <= 0) return;
    const lx = xf + L * 0.016, ly = roadY - L * 0.115, R = Math.max(W * 1.1, L * 1.4);
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    let g = ctx.createLinearGradient(lx, 0, lx - R, 0);
    g.addColorStop(0, `rgba(255,238,210,${0.26 * h})`);
    g.addColorStop(0.4, `rgba(255,238,210,${0.07 * h})`);
    g.addColorStop(1, "rgba(255,238,210,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(lx, ly - L * 0.01);
    ctx.lineTo(lx - R, ly - R * 0.17);
    ctx.lineTo(lx - R, ly + R * 0.24);
    ctx.lineTo(lx, ly + L * 0.01);
    ctx.fill();
    ctx.save();
    ctx.translate(lx - L * 0.45, roadY + 1);
    ctx.scale(1, 0.06);
    g = ctx.createRadialGradient(0, 0, 0, 0, 0, L * 0.7);
    g.addColorStop(0, `rgba(255,232,196,${0.28 * h})`);
    g.addColorStop(1, "rgba(255,232,196,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, L * 0.7, 0, 7);
    ctx.fill();
    ctx.restore();
    for (const m of motes) {
      const x = (((m.x * W - t * m.v * 30) % W) + W) % W, y = m.y * H, dx = lx - x;
      if (dx <= 0) continue;
      const half = dx * 0.2 + L * 0.01, off = y - (ly + dx * 0.035);
      if (Math.abs(off) > half) continue;
      const a = h * (1 - dx / R) * (1 - Math.abs(off) / half) * (0.5 + 0.5 * Math.sin(t * 1.5 + m.p)) * 0.7;
      if (a < 0.02) continue;
      ctx.fillStyle = `rgba(255,240,215,${a})`;
      ctx.beginPath();
      ctx.arc(x, y, m.r, 0, 7);
      ctx.fill();
    }
    g = ctx.createRadialGradient(lx, ly, 0, lx, ly, L * 0.1);
    g.addColorStop(0, `rgba(255,252,242,${h})`);
    g.addColorStop(0.1, `rgba(255,236,200,${0.45 * h})`);
    g.addColorStop(1, "rgba(255,220,170,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(lx, ly, L * 0.1, 0, 7);
    ctx.fill();
    ctx.save();
    ctx.translate(lx, ly);
    ctx.scale(1, 0.008);
    g = ctx.createRadialGradient(0, 0, 0, 0, 0, W * 0.6);
    g.addColorStop(0, `rgba(255,245,230,${0.35 * h})`);
    g.addColorStop(1, "rgba(255,245,230,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, W * 0.6, 0, 7);
    ctx.fill();
    ctx.restore();
    ctx.restore();
  }

  function wheel(x, r, rot) {
    ctx.fillStyle = "#030303";
    ctx.beginPath();
    ctx.arc(x, -r, r, 0, 7);
    ctx.fill();
    const g = ctx.createRadialGradient(x - r * 0.15, -r * 1.15, 0, x, -r, r * 0.58);
    g.addColorStop(0, "#5C5F66");
    g.addColorStop(1, "#1C1D21");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, -r, r * 0.56, 0, 7);
    ctx.fill();
    ctx.strokeStyle = "rgba(0,0,0,.55)";
    ctx.lineWidth = 0.004;
    for (let i = 0; i < 8; i++) {
      const a = rot + (i * Math.PI) / 4;
      ctx.beginPath();
      ctx.moveTo(x + Math.cos(a) * r * 0.16, -r + Math.sin(a) * r * 0.16);
      ctx.lineTo(x + Math.cos(a) * r * 0.5, -r + Math.sin(a) * r * 0.5);
      ctx.stroke();
    }
    ctx.fillStyle = "#0A0A0B";
    ctx.beginPath();
    ctx.arc(x, -r, r * 0.12, 0, 7);
    ctx.fill();
  }

  function truck(xf, rot, mk, hd) {
    if (xf > W + 10 || xf + L < -10) return;
    ctx.save();
    ctx.translate(xf, roadY);
    ctx.scale(L, L);
    ctx.save();
    ctx.scale(1, 0.04);
    const sg = ctx.createRadialGradient(0.5, 0, 0, 0.5, 0, 0.62);
    sg.addColorStop(0, "rgba(0,0,0,.9)");
    sg.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = sg;
    ctx.fillRect(-0.12, -0.7, 1.24, 1.4);
    ctx.restore();
    let g = ctx.createLinearGradient(0, -0.31, 0, -0.085);
    g.addColorStop(0, "#2A2C31");
    g.addColorStop(0.08, "#1A1B1F");
    g.addColorStop(0.6, "#111215");
    g.addColorStop(1, "#08080A");
    ctx.fillStyle = g;
    ctx.fillRect(0.3, -0.31, 0.7, 0.225);
    g = ctx.createLinearGradient(0.3, 0, 1, 0);
    g.addColorStop(0, `rgba(255,240,215,${0.05 * hd})`);
    g.addColorStop(1, "rgba(255,240,215,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0.3, -0.31, 0.7, 0.225);
    ctx.fillStyle = `rgba(255,255,255,${0.1 + 0.2 * hd})`;
    ctx.fillRect(0.3, -0.31, 0.7, 0.0018);
    ctx.fillStyle = "#040405";
    ctx.fillRect(0.3, -0.087, 0.7, 0.013);
    ctx.fillRect(0.43, -0.075, 0.005, 0.05);
    g = ctx.createLinearGradient(0, -0.3, 0, -0.07);
    g.addColorStop(0, "#26282D");
    g.addColorStop(0.35, "#141518");
    g.addColorStop(1, "#08080A");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(0.012, -0.075);
    ctx.lineTo(0.012, -0.16);
    ctx.quadraticCurveTo(0.014, -0.178, 0.034, -0.18);
    ctx.lineTo(0.13, -0.19);
    ctx.lineTo(0.146, -0.272);
    ctx.quadraticCurveTo(0.15, -0.286, 0.167, -0.287);
    ctx.lineTo(0.236, -0.289);
    ctx.lineTo(0.246, -0.3);
    ctx.lineTo(0.322, -0.3);
    ctx.quadraticCurveTo(0.33, -0.298, 0.33, -0.288);
    ctx.lineTo(0.33, -0.085);
    ctx.lineTo(0.3, -0.07);
    ctx.lineTo(0.012, -0.07);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = `rgba(255,255,255,${0.08 + 0.28 * hd})`;
    ctx.lineWidth = 0.0018;
    ctx.beginPath();
    ctx.moveTo(0.012, -0.16);
    ctx.quadraticCurveTo(0.014, -0.178, 0.034, -0.18);
    ctx.lineTo(0.13, -0.19);
    ctx.lineTo(0.146, -0.272);
    ctx.quadraticCurveTo(0.15, -0.286, 0.167, -0.287);
    ctx.lineTo(0.236, -0.289);
    ctx.stroke();
    g = ctx.createLinearGradient(0.14, -0.27, 0.2, -0.2);
    g.addColorStop(0, "#3A3F48");
    g.addColorStop(0.45, "#0B0C0F");
    g.addColorStop(1, "#1A1D22");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(0.139, -0.2);
    ctx.lineTo(0.15, -0.266);
    ctx.lineTo(0.19, -0.268);
    ctx.lineTo(0.19, -0.2);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(0.197, -0.205);
    ctx.lineTo(0.197, -0.266);
    ctx.lineTo(0.229, -0.268);
    ctx.lineTo(0.229, -0.205);
    ctx.fill();
    ctx.fillStyle = "#1E1F23";
    ctx.fillRect(-0.003, -0.082, 0.038, 0.028);
    ctx.fillStyle = `rgba(255,255,255,${0.12 + 0.3 * hd})`;
    ctx.fillRect(-0.003, -0.082, 0.038, 0.002);
    ctx.fillStyle = "#0C0C0E";
    ctx.fillRect(0.012, -0.158, 0.007, 0.074);
    g = ctx.createLinearGradient(0.237, 0, 0.245, 0);
    g.addColorStop(0, "#2A2B30");
    g.addColorStop(0.5, "#8E9097");
    g.addColorStop(1, "#1E1F23");
    ctx.fillStyle = g;
    ctx.fillRect(0.237, -0.365, 0.007, 0.185);
    ctx.fillStyle = "#000";
    ctx.beginPath();
    ctx.arc(0.085, -0.052, 0.061, Math.PI, 0);
    ctx.fill();
    [0.085, 0.262, 0.318, 0.872, 0.932].forEach((x) => wheel(x, 0.05, rot));
    ctx.fillStyle = hd > 0 ? `rgba(255,250,238,${0.3 + 0.7 * hd})` : "#1E1F23";
    ctx.fillRect(0.012, -0.123, 0.012, 0.016);
    ctx.fillStyle = `rgba(255,59,48,${0.3 + 0.7 * mk})`;
    ctx.fillRect(0.994, -0.117, 0.006, 0.018);
    ctx.restore();
    ctx.save();
    ctx.font = `600 ${L * 0.05}px ${DISP}`;
    ctx.fillStyle = `rgba(245,245,247,${0.07 + 0.08 * hd})`;
    ctx.fillText("GridBridge", xf + L * 0.56, roadY - L * 0.175);
    ctx.restore();
    const mks = [];
    for (let i = 0; i < 5; i++) mks.push([0.168 + i * 0.015, -0.29]);
    for (let x = 0.34; x < 1; x += 0.109) mks.push([x, -0.306]);
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    mks.forEach(([x, y], i) => {
      const on = clamp(mk * mks.length - i);
      if (on <= 0) return;
      const sx = xf + x * L, sy = roadY + y * L, rr = Math.max(1, L * 0.0022);
      const gg = ctx.createRadialGradient(sx, sy, 0, sx, sy, rr * 6);
      gg.addColorStop(0, `rgba(255,196,120,${0.4 * on})`);
      gg.addColorStop(1, "rgba(255,196,120,0)");
      ctx.fillStyle = gg;
      ctx.fillRect(sx - rr * 6, sy - rr * 6, rr * 12, rr * 12);
      ctx.fillStyle = `rgba(255,222,170,${on})`;
      ctx.beginPath();
      ctx.arc(sx, sy, rr, 0, 7);
      ctx.fill();
    });
    const tx = xf + L, ty = roadY - L * 0.108;
    const tg = ctx.createRadialGradient(tx, ty, 0, tx, ty, L * 0.05);
    tg.addColorStop(0, `rgba(255,59,48,${0.4 * mk})`);
    tg.addColorStop(1, "rgba(255,59,48,0)");
    ctx.fillStyle = tg;
    ctx.fillRect(tx - L * 0.05, ty - L * 0.05, L * 0.1, L * 0.1);
    ctx.restore();
  }

  function truckX() {
    // Reduced motion: park mid-frame. Otherwise xf decreases over time (right → left).
    if (reduced.matches) return W < 700 ? W * 0.11 : W * 0.48;
    const speed = Math.max(90, W * 0.14);
    const cycle = W + L * 1.45;
    return W - ((scrollT * speed) % cycle);
  }

  function render(now) {
    if (disposed) return;
    const moving = !reduced.matches && !isPaused();
    if (moving) {
      if (lastNow != null) scrollT += (now - lastNow) / 1000;
      lastNow = now;
    } else {
      lastNow = null;
    }
    const t = scrollT;
    const speed = Math.max(90, W * 0.14);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const road = ctx.createLinearGradient(0, roadY, 0, H);
    road.addColorStop(0, "#111114");
    road.addColorStop(1, "#000");
    ctx.fillStyle = road;
    ctx.fillRect(0, roadY, W, H - roadY);
    ctx.strokeStyle = "rgba(255,226,176,.12)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, roadY);
    ctx.lineTo(W, roadY);
    ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,.09)";
    ctx.setLineDash([48, 100]);
    ctx.lineDashOffset = reduced.matches ? 0 : t * speed * 0.55;
    ctx.beginPath();
    ctx.moveTo(0, roadY + 30);
    ctx.lineTo(W, roadY + 30);
    ctx.stroke();
    ctx.setLineDash([]);
    const xf = truckX();
    const rot = reduced.matches ? 0 : -(t * speed) / (L * 0.05);
    const onScreen = xf < W + 10 && xf + L > -10;
    const hd = onScreen ? 1 : 0;
    beam(xf, hd, t);
    truck(xf, rot, onScreen ? 1 : 0, hd);
  }

  function tick(now) {
    frameId = 0;
    if (disposed || !visible || document.hidden) return;
    render(now);
    // Keep the loop alive while paused so Play resumes without remounting; reduced-motion stays static.
    if (!reduced.matches) frameId = requestAnimationFrame(tick);
  }
  function schedule() {
    cancelAnimationFrame(frameId);
    frameId = requestAnimationFrame(tick);
  }
  const observer = new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    schedule();
  });
  observer.observe(cv);
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(cv);
  document.addEventListener("visibilitychange", schedule);
  reduced.addEventListener("change", schedule);
  resize();
  schedule();
  return () => {
    disposed = true;
    cancelAnimationFrame(frameId);
    observer.disconnect();
    resizeObserver.disconnect();
    document.removeEventListener("visibilitychange", schedule);
    reduced.removeEventListener("change", schedule);
  };
}
