// 2 輪ロボットで NMPC（ガウス・ニュートン法）と MPPI を同じコストで比べる（ブラウザ・Node 共通）
// exercises/robot2d.py は、これを numpy に移したもの（パラメータも同じ）
(function (root) {
  'use strict';

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function makeNormal(rand) {
    let spare = null;
    return function () {
      if (spare !== null) { const s = spare; spare = null; return s; }
      let u, v, r;
      do { u = rand() * 2 - 1; v = rand() * 2 - 1; r = u * u + v * v; } while (r === 0 || r >= 1);
      const m = Math.sqrt(-2 * Math.log(r) / r);
      spare = v * m;
      return u * m;
    };
  }
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  const P = {
    dt: 0.1, N: 30,
    vMin: 0.0, vMax: 1.0, wMax: 1.5,
    rRobot: 0.25, rPerson: 0.3, margin: 0.5,
    start: { x: 1.0, y: 0.0, th: 0.0 },
    goal: { x: 9.0, y: 0.0 },
    vRef: 0.8, yWall: 2.75,
    qRef: 1.0, qW: 0.1, qO: 40.0, qWall: 100.0, qT: 5.0, cliff: 1000.0,
    goalTol: 0.2, timeLimit: 25
  };
  P.rCol = P.rRobot + P.rPerson;          // 接触とみなす中心間距離
  P.dSafe = P.rCol + P.margin;            // なめらかな罰が始まる中心間距離
  P.yLim = P.yWall - P.rRobot;

  const SCENES = {
    offset: [{ x: 5.0, y: 0.25, vx: 0, vy: 0 }],
    headon: [{ x: 5.0, y: 0.0, vx: 0, vy: 0 }],
    cross: [{ x: 5.5, y: -2.3, vx: 0, vy: 0.5, bounceY: 2.3 }],
    two: [
      { x: 4.0, y: -0.45, vx: 0, vy: 0 },
      { x: 8.6, y: 0.5, vx: -0.4, vy: 0, minX: 1.5 }
    ]
  };

  // ---- 環境（ロボットの状態と人）。両方の制御器で同じ動きをする
  function createWorld(scene) {
    const w = {
      state: { x: P.start.x, y: P.start.y, th: P.start.th },
      people: SCENES[scene].map(function (p) { return Object.assign({}, p); }),
      t: 0, trail: [{ x: P.start.x, y: P.start.y }],
      arrived: false, contacts: 0, inContact: false, minClear: Infinity
    };
    w.apply = function (v, om) {
      const s = w.state;
      s.x += v * Math.cos(s.th) * P.dt;
      s.y += v * Math.sin(s.th) * P.dt;
      s.th += om * P.dt;
      for (let i = 0; i < w.people.length; i++) {
        const p = w.people[i];
        p.x += p.vx * P.dt; p.y += p.vy * P.dt;
        if (p.bounceY !== undefined && Math.abs(p.y) > p.bounceY) { p.vy = -p.vy; p.y = clamp(p.y, -p.bounceY, p.bounceY); }
        if (p.minX !== undefined && p.x < p.minX) { p.x = p.minX; p.vx = 0; }
      }
      w.t += P.dt;
      w.trail.push({ x: s.x, y: s.y });
      let touching = false;
      for (let i = 0; i < w.people.length; i++) {
        const p = w.people[i];
        const d = Math.hypot(s.x - p.x, s.y - p.y) - P.rCol;
        if (d < w.minClear) w.minClear = d;
        if (d < 0) touching = true;
      }
      if (touching && !w.inContact) w.contacts++;
      w.inContact = touching;
      if (Math.hypot(s.x - P.goal.x, s.y - P.goal.y) < P.goalTol) w.arrived = true;
    };
    w.finished = function () { return w.arrived || w.t >= P.timeLimit - 1e-9; };
    return w;
  }

  // ---- 共通のコスト S = ||r||^2（+ 崖モードでは接触の罰）
  // 目標軌道：今の位置からゴールへ向かう直線上を vRef で進む点
  function makeRef(state, refX, refY) {
    const dx = P.goal.x - state.x, dy = P.goal.y - state.y;
    const D = Math.hypot(dx, dy) || 1;
    for (let n = 0; n <= P.N; n++) {
      const s = Math.min(1, P.vRef * n * P.dt / D);
      refX[n] = state.x + s * dx;
      refY[n] = state.y + s * dy;
    }
  }

  // 入力列 (v, w) をロールアウトしてコストを返す。軌跡は ox, oy に書く
  function rolloutCost(ctx, vArr, wArr, off, ox, oy, oOff) {
    const st = ctx.world.state, ppl = ctx.world.people, mode = ctx.mode;
    let x = st.x, y = st.y, th = st.th, S = 0;
    if (ox) { ox[oOff] = x; oy[oOff] = y; }
    for (let n = 0; n < P.N; n++) {
      const v = vArr[off + n], om = wArr[off + n];
      x += v * Math.cos(th) * P.dt;
      y += v * Math.sin(th) * P.dt;
      th += om * P.dt;
      const ex = x - ctx.refX[n + 1], ey = y - ctx.refY[n + 1];
      S += P.qRef * (ex * ex + ey * ey) + P.qW * om * om;
      const tF = (n + 1) * P.dt;
      for (let i = 0; i < ppl.length; i++) {
        const p = ppl[i];
        const d = Math.hypot(x - (p.x + p.vx * tF), y - (p.y + p.vy * tF));
        if (mode === 'cliff') { if (d < P.rCol) S += P.cliff; }
        else if (d < P.dSafe) { const h = P.dSafe - d; S += P.qO * h * h; }
      }
      const ay = Math.abs(y) - P.yLim;
      if (ay > 0) S += P.qWall * ay * ay;
      if (ox) { ox[oOff + n + 1] = x; oy[oOff + n + 1] = y; }
    }
    const tx = x - ctx.refX[P.N], ty = y - ctx.refY[P.N];
    S += P.qT * (tx * tx + ty * ty);
    return S;
  }

  // ---- MPPI
  function createMPPI(opts) {
    const o = Object.assign({ scene: 'offset', mode: 'smooth', lambda: 1.0, sigmaW: 0.8, K: 300, seed: 1 }, opts || {});
    const N = P.N;
    const c = {
      kind: 'mppi', opts: o, world: null, mode: o.mode,
      refX: new Float64Array(N + 1), refY: new Float64Array(N + 1),
      uV: new Float64Array(N), uW: new Float64Array(N),
      K: 0, eV: null, eW: null, cV: null, cW: null, S: null, w: null, trajX: null, trajY: null,
      planX: new Float64Array(N + 1), planY: new Float64Array(N + 1),
      lastEss: 0, rollouts: 0
    };
    function allocate(K) {
      c.K = K;
      c.eV = new Float64Array(K * N); c.eW = new Float64Array(K * N);
      c.cV = new Float64Array(K * N); c.cW = new Float64Array(K * N);
      c.S = new Float64Array(K); c.w = new Float64Array(K);
      c.trajX = new Float64Array(K * (N + 1)); c.trajY = new Float64Array(K * (N + 1));
    }
    c.optimize = function () {
      if (c.K !== o.K) allocate(o.K);
      c.mode = o.mode;
      makeRef(c.world.state, c.refX, c.refY);
      const K = c.K, sV = o.sigmaW * 0.35, sW = o.sigmaW;
      for (let k = 0; k < K; k++) {
        for (let n = 0; n < N; n++) {
          const i = k * N + n;
          const v = clamp(c.uV[n] + sV * c.randn(), P.vMin, P.vMax);
          const om = clamp(c.uW[n] + sW * c.randn(), -P.wMax, P.wMax);
          c.cV[i] = v; c.cW[i] = om;
          c.eV[i] = v - c.uV[n]; c.eW[i] = om - c.uW[n];
        }
        c.S[k] = rolloutCost(c, c.cV, c.cW, k * N, c.trajX, c.trajY, k * (N + 1));
      }
      let Smin = Infinity;
      for (let k = 0; k < K; k++) if (c.S[k] < Smin) Smin = c.S[k];
      let eta = 0, sq = 0;
      for (let k = 0; k < K; k++) { c.w[k] = Math.exp(-(c.S[k] - Smin) / o.lambda); eta += c.w[k]; }
      for (let k = 0; k < K; k++) { c.w[k] /= eta; sq += c.w[k] * c.w[k]; }
      for (let n = 0; n < N; n++) {
        let dv = 0, dw = 0;
        for (let k = 0; k < K; k++) { dv += c.w[k] * c.eV[k * N + n]; dw += c.w[k] * c.eW[k * N + n]; }
        c.uV[n] = clamp(c.uV[n] + dv, P.vMin, P.vMax);
        c.uW[n] = clamp(c.uW[n] + dw, -P.wMax, P.wMax);
      }
      c.cost = rolloutCost(c, c.uV, c.uW, 0, c.planX, c.planY, 0);
      c.lastEss = 1 / sq;
      c.rollouts = K + 1;
    };
    c.reset = function () {
      c.randn = makeNormal(mulberry32(o.seed));
      c.world = createWorld(o.scene);
      c.uV.fill(0.5); c.uW.fill(0);
      allocate(o.K);
      for (let i = 0; i < 5; i++) c.optimize();
    };
    c.step = function () {
      const w = c.world;
      if (w.finished()) return;
      w.apply(c.uV[0], c.uW[0]);
      if (w.finished()) return;
      for (let n = 0; n < N - 1; n++) { c.uV[n] = c.uV[n + 1]; c.uW[n] = c.uW[n + 1]; }
      c.optimize();
    };
    c.reset();
    return c;
  }

  // ---- NMPC：single shooting + ガウス・ニュートン法（LM 減衰、解析ヤコビアン）
  function cholSolve(A, b, n) {
    // A は n×n の正定値行列（行優先、上書きする）。A x = b を解いて x を返す
    const L = A;
    for (let j = 0; j < n; j++) {
      let s = L[j * n + j];
      for (let k = 0; k < j; k++) s -= L[j * n + k] * L[j * n + k];
      if (s <= 1e-14) return null;
      const d = Math.sqrt(s);
      L[j * n + j] = d;
      for (let i = j + 1; i < n; i++) {
        let t = L[i * n + j];
        for (let k = 0; k < j; k++) t -= L[i * n + k] * L[j * n + k];
        L[i * n + j] = t / d;
      }
    }
    const y = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let t = b[i];
      for (let k = 0; k < i; k++) t -= L[i * n + k] * y[k];
      y[i] = t / L[i * n + i];
    }
    const x = new Float64Array(n);
    for (let i = n - 1; i >= 0; i--) {
      let t = y[i];
      for (let k = i + 1; k < n; k++) t -= L[k * n + i] * x[k];
      x[i] = t / L[i * n + i];
    }
    return x;
  }

  function createNMPC(opts) {
    const o = Object.assign({ scene: 'offset', mode: 'smooth', iters: 3 }, opts || {});
    const N = P.N, M = 2 * N;
    const c = {
      kind: 'nmpc', opts: o, world: null, mode: o.mode,
      refX: new Float64Array(N + 1), refY: new Float64Array(N + 1),
      uV: new Float64Array(N), uW: new Float64Array(N),
      planX: new Float64Array(N + 1), planY: new Float64Array(N + 1),
      iterX: [], iterY: [], mu: 1e-3, cost: 0, rollouts: 0, stalled: false
    };
    const H = new Float64Array(M * M), Hs = new Float64Array(M * M), g = new Float64Array(M);
    const th = new Float64Array(N + 1), xs = new Float64Array(N + 1), ys = new Float64Array(N + 1);
    const As = new Float64Array(N + 1), Ac = new Float64Array(N + 1);
    const a = new Float64Array(M);
    const tV = new Float64Array(N), tW = new Float64Array(N);

    // 位置 (x_n, y_n) の入力に対する感度を a に書く。cx, cy は位置の係数
    function rowFromPos(n, cx, cy) {
      a.fill(0);
      for (let j = 0; j < n; j++) {
        a[j] = (cx * Math.cos(th[j]) + cy * Math.sin(th[j])) * P.dt;            // ∂/∂v_j
        if (j <= n - 2) {
          const sS = As[n] - As[j + 1], sC = Ac[n] - Ac[j + 1];               // Σ_{i=j+1}^{n-1} v_i sin/cos θ_i
          a[N + j] = (-cx * sS + cy * sC) * P.dt * P.dt;                        // ∂/∂ω_j
        }
      }
    }
    function addRow(r) {
      for (let p = 0; p < M; p++) {
        const ap = a[p];
        if (ap === 0) continue;
        g[p] += ap * r;
        for (let q = p; q < M; q++) H[p * M + q] += ap * a[q];
      }
    }
    // 現在の入力列でロールアウトし、H = J^T J と g = J^T r を組む
    function linearize() {
      const st = c.world.state, ppl = c.world.people;
      H.fill(0); g.fill(0);
      xs[0] = st.x; ys[0] = st.y; th[0] = st.th; As[0] = 0; Ac[0] = 0;
      for (let n = 0; n < N; n++) {
        As[n + 1] = As[n] + c.uV[n] * Math.sin(th[n]);
        Ac[n + 1] = Ac[n] + c.uV[n] * Math.cos(th[n]);
        xs[n + 1] = xs[n] + c.uV[n] * Math.cos(th[n]) * P.dt;
        ys[n + 1] = ys[n] + c.uV[n] * Math.sin(th[n]) * P.dt;
        th[n + 1] = th[n] + c.uW[n] * P.dt;
      }
      const sr = Math.sqrt(P.qRef), so = Math.sqrt(P.qO), sw = Math.sqrt(P.qWall), sT = Math.sqrt(P.qT);
      for (let n = 1; n <= N; n++) {
        const ex = xs[n] - c.refX[n], ey = ys[n] - c.refY[n];
        rowFromPos(n, sr, 0); addRow(sr * ex);
        rowFromPos(n, 0, sr); addRow(sr * ey);
        if (c.mode !== 'cliff') {
          const tF = n * P.dt;
          for (let i = 0; i < ppl.length; i++) {
            const p = ppl[i];
            const dx = xs[n] - (p.x + p.vx * tF), dy = ys[n] - (p.y + p.vy * tF);
            const d = Math.hypot(dx, dy);
            if (d < P.dSafe && d > 1e-9) {
              rowFromPos(n, -so * dx / d, -so * dy / d);
              addRow(so * (P.dSafe - d));
            }
          }
        }
        const ay = Math.abs(ys[n]) - P.yLim;
        if (ay > 0) { rowFromPos(n, 0, sw * Math.sign(ys[n])); addRow(sw * ay); }
      }
      const tx = xs[N] - c.refX[N], ty = ys[N] - c.refY[N];
      rowFromPos(N, sT, 0); addRow(sT * tx);
      rowFromPos(N, 0, sT); addRow(sT * ty);
      const sq = Math.sqrt(P.qW);
      for (let j = 0; j < N; j++) { a.fill(0); a[N + j] = sq; addRow(sq * c.uW[j]); }
      for (let p = 0; p < M; p++) for (let q = 0; q < p; q++) H[p * M + q] = H[q * M + p];
    }
    c.optimize = function () {
      c.mode = o.mode;
      makeRef(c.world.state, c.refX, c.refY);
      c.iterX = []; c.iterY = [];
      let cost = rolloutCost(c, c.uV, c.uW, 0, null, null, 0);
      let evals = 1;
      c.stalled = false;
      for (let it = 0; it < o.iters; it++) {
        linearize();
        // 反復ごとの軌跡を残す（描画用）
        const ix = new Float64Array(N + 1), iy = new Float64Array(N + 1);
        ix.set(xs); iy.set(ys);
        c.iterX.push(ix); c.iterY.push(iy);
        let accepted = false;
        for (let tries = 0; tries < 8; tries++) {
          Hs.set(H);
          for (let p = 0; p < M; p++) Hs[p * M + p] += c.mu * (H[p * M + p] + 1e-3);
          const rhs = new Float64Array(M);
          for (let p = 0; p < M; p++) rhs[p] = -g[p];
          const dz = cholSolve(Hs, rhs, M);
          if (dz) {
            for (let n = 0; n < N; n++) {
              tV[n] = clamp(c.uV[n] + dz[n], P.vMin, P.vMax);
              tW[n] = clamp(c.uW[n] + dz[N + n], -P.wMax, P.wMax);
            }
            const ct = rolloutCost(c, tV, tW, 0, null, null, 0);
            evals++;
            if (ct < cost) {
              c.uV.set(tV); c.uW.set(tW); cost = ct;
              c.mu = Math.max(c.mu / 3, 1e-7);
              accepted = true;
              break;
            }
          }
          c.mu = Math.min(c.mu * 4, 1e8);
        }
        if (!accepted) { c.stalled = true; break; }
      }
      c.cost = rolloutCost(c, c.uV, c.uW, 0, c.planX, c.planY, 0);
      c.rollouts = evals + c.iterX.length;
    };
    c.reset = function () {
      c.world = createWorld(o.scene);
      c.uV.fill(0.5); c.uW.fill(0); c.mu = 1e-3;
      for (let i = 0; i < 5; i++) c.optimize();
    };
    c.step = function () {
      const w = c.world;
      if (w.finished()) return;
      w.apply(c.uV[0], c.uW[0]);
      if (w.finished()) return;
      for (let n = 0; n < N - 1; n++) { c.uV[n] = c.uV[n + 1]; c.uW[n] = c.uW[n + 1]; }
      c.optimize();
    };
    // テスト用：解析ヤコビアンから作った勾配を返す
    c._grad = function () { makeRef(c.world.state, c.refX, c.refY); linearize(); return Array.from(g); };
    c.reset();
    return c;
  }

  root.Ctrl = { P: P, SCENES: SCENES, createMPPI: createMPPI, createNMPC: createNMPC, rolloutCost: rolloutCost, makeRef: makeRef, mulberry32: mulberry32, makeNormal: makeNormal };
})(typeof window !== 'undefined' ? window : globalThis);
