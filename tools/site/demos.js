/* インタラクティブデモ: ニュートン法 / MPPI の重み / ぼかしたコスト / NMPC と MPPI の比較 / トップページの MPPI
   すべて素の JavaScript (ライブラリなし)。色は CSS 変数から読むので、ライト/ダークの両方で読める。
   NMPC と MPPI の本体は ctrl.js (exercises/robot2d.py と同じパラメータ) */
(function () {
  "use strict";

  // ------------------------------------------------------------------ 共通
  var MINUS = "−";
  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (html != null) e.innerHTML = html;
    return e;
  }
  function fmt(x, d) {
    var s = Math.abs(x).toFixed(d);
    return (x < 0 && Number(s) !== 0 ? MINUS : "") + s;
  }
  function fitCanvas(canvas, aspect) {
    var r = Math.min(window.devicePixelRatio || 1, 2);
    var w = canvas.clientWidth || canvas.parentElement.clientWidth || 600;
    var h = Math.round(w * aspect);
    canvas.width = Math.round(w * r);
    canvas.height = Math.round(h * r);
    canvas.style.height = h + "px";
    var ctx = canvas.getContext("2d");
    ctx.setTransform(r, 0, 0, r, 0, 0);
    return { ctx: ctx, w: w, h: h };
  }
  function onResize(target, fn) {
    if (window.ResizeObserver) new ResizeObserver(function () { fn(); }).observe(target);
    else window.addEventListener("resize", fn);
  }
  function onTheme(fn) {
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      if (mq.addEventListener) mq.addEventListener("change", fn);
    }
    new MutationObserver(fn).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }
  function reducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }
  function shell(container, title, sub) {
    container.classList.add("demo");
    container.innerHTML = "";
    var head = el("div", { class: "demo-head" }, "<strong>" + title + "</strong><span>" + sub + "</span>");
    var body = el("div", { class: "demo-body" });
    container.appendChild(head);
    container.appendChild(body);
    return body;
  }
  function seg(options, current, onChange) {
    var box = el("div", { class: "seg", role: "group" });
    options.forEach(function (o) {
      var b = el("button", { type: "button", "aria-pressed": o[0] === current ? "true" : "false" }, o[1]);
      b.addEventListener("click", function () {
        box.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true");
        onChange(o[0]);
      });
      box.appendChild(b);
    });
    return box;
  }
  function sliderRow(label, attrs, show) {
    var lab = el("label", { class: "slider-row" });
    lab.appendChild(el("span", null, label));
    var input = el("input", Object.assign({ type: "range" }, attrs));
    lab.appendChild(input);
    var out = el("output", null, "");
    lab.appendChild(out);
    function sync() { out.textContent = show(parseFloat(input.value)); }
    input.addEventListener("input", sync);
    sync();
    return { row: lab, input: input, sync: sync, value: function () { return parseFloat(input.value); } };
  }
  function svgEl(viewBox, label) {
    var s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", viewBox);
    s.setAttribute("role", "img");
    s.setAttribute("aria-label", label);
    return s;
  }
  function pts(arr) {
    return arr.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" ");
  }
  // 標準正規分布の密度と累積分布 (erf の近似。誤差 1e-7 程度)
  function phi(x) { return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI); }
  function Phi(x) {
    var t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
    var y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x / 2);
    return x >= 0 ? 0.5 * (1 + y) : 0.5 * (1 - y);
  }

  // ------------------------------------------------------------------ 1. ニュートン法 (02 章)
  function demoNewton(root, mode) {
    var body = shell(root, "ニュートン法を 1 回ずつ", "接線を引き、接線が 0 になる所へ移る");
    var canvas = el("canvas", { "aria-label": "関数 r(z) のグラフと、ニュートン法の接線" });
    body.appendChild(canvas);
    var F = {
      sq: {
        r: function (z) { return z * z - 2; }, d: function (z) { return 2 * z; },
        label: "r(z) = z² − 2", view: [-0.2, 3.2, -2.6, 8.4], z0: 2.0, ans: Math.SQRT2
      },
      atan: {
        r: Math.atan, d: function (z) { return 1 / (1 + z * z); },
        label: "r(z) = arctan z", view: [-6, 6, -1.8, 1.8], z0: 1.2, ans: 0
      }
    };
    var fn = mode === "atan" ? "atan" : "sq";
    var controls = el("div", { class: "controls" });
    var slider = sliderRow("出発点 z₀", { min: "0.2", max: "2.4", step: "0.05", value: String(F[fn].z0) }, function (v) { return v.toFixed(2); });
    controls.appendChild(seg([["sq", "z² − 2"], ["atan", "arctan z"]], fn, function (m) {
      fn = m;
      slider.input.value = String(F[fn].z0);
      slider.sync();
      reset();
    }));
    var stepBtn = el("button", { type: "button", class: "btn primary" }, "1 回進める");
    var resetBtn = el("button", { type: "button", class: "btn" }, "リセット");
    controls.appendChild(stepBtn);
    controls.appendChild(resetBtn);
    controls.appendChild(slider.row);
    body.appendChild(controls);
    var table = el("div", { class: "iter-table" });
    body.appendChild(table);
    var note = el("p", { class: "note" });
    body.appendChild(note);
    var zs = [];

    function reset() { zs = [slider.value()]; draw(); }
    function step() {
      var f = F[fn], z = zs[zs.length - 1];
      if (!isFinite(z) || Math.abs(z) > 1e6 || zs.length > 40) return;
      var d = f.d(z);
      if (Math.abs(d) < 1e-300) return;
      zs.push(z - f.r(z) / d);
      draw();
    }
    function draw() {
      var f = F[fn], v = f.view;
      var c = fitCanvas(canvas, 0.5), ctx = c.ctx, w = c.w, h = c.h;
      var L = 34, R = 12, T = 14, B = 26;
      function X(z) { return L + (z - v[0]) / (v[1] - v[0]) * (w - L - R); }
      function Y(r) { return T + (v[3] - r) / (v[3] - v[2]) * (h - T - B); }
      ctx.clearRect(0, 0, w, h);
      ctx.font = "12px " + css("--font-mono");
      ctx.fillStyle = css("--muted");
      ctx.strokeStyle = css("--line");
      ctx.lineWidth = 1;
      // 軸
      ctx.beginPath(); ctx.moveTo(L, Y(0)); ctx.lineTo(w - R, Y(0)); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(X(0), T); ctx.lineTo(X(0), h - B); ctx.stroke();
      ctx.textAlign = "center";
      var stepTick = fn === "sq" ? 1 : 2;
      for (var t = Math.ceil(v[0]); t <= v[1]; t += stepTick) {
        if (t === 0) continue;
        ctx.fillText(t === 0 ? "0" : fmt(t, 0), X(t), Y(0) + 15);
      }
      ctx.textAlign = "left";
      ctx.fillText("z", w - R - 8, Y(0) - 6);
      ctx.save();
      ctx.beginPath(); ctx.rect(L, T, w - L - R, h - T - B); ctx.clip();
      // 関数
      ctx.strokeStyle = css("--ink");
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (var i = 0; i <= 300; i++) {
        var z = v[0] + (v[1] - v[0]) * i / 300;
        if (i === 0) ctx.moveTo(X(z), Y(f.r(z))); else ctx.lineTo(X(z), Y(f.r(z)));
      }
      ctx.stroke();
      // 最後の点での接線と、次の点の予告
      var zl = zs[zs.length - 1];
      if (isFinite(zl) && Math.abs(zl) < 1e6) {
        var rl = f.r(zl), dl = f.d(zl);
        ctx.strokeStyle = css("--mpc");
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(X(v[0]), Y(rl + dl * (v[0] - zl)));
        ctx.lineTo(X(v[1]), Y(rl + dl * (v[1] - zl)));
        ctx.stroke();
        var zn = zl - rl / dl;
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = css("--muted");
        ctx.beginPath(); ctx.moveTo(X(zn), Y(0)); ctx.lineTo(X(zn), Y(f.r(zn))); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = css("--surface");
        ctx.strokeStyle = css("--mpc");
        ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.arc(X(zn), Y(0), 4.5, 0, 7); ctx.fill(); ctx.stroke();
        ctx.fillStyle = css("--mpc");
        ctx.beginPath(); ctx.arc(X(zl), Y(rl), 5, 0, 7); ctx.fill();
      }
      // これまでの点
      zs.forEach(function (z, k) {
        if (!isFinite(z) || z < v[0] || z > v[1]) return;
        ctx.fillStyle = k === zs.length - 1 ? css("--mpc") : css("--muted");
        ctx.beginPath(); ctx.arc(X(z), Y(0), 3, 0, 7); ctx.fill();
      });
      ctx.restore();
      ctx.fillStyle = css("--ink");
      ctx.font = "13px " + css("--font-body");
      ctx.fillText(f.label, L + 8, T + 14);
      // 表と説明
      table.innerHTML = zs.slice(-6).map(function (z, j) {
        var k = zs.length - Math.min(6, zs.length) + j;
        var r = f.r(z);
        return "<span>z<sub>" + k + "</sub> = <b>" + (Math.abs(z) < 1e4 ? fmt(z, 6) : z.toExponential(2)) +
          "</b> (r = " + (Math.abs(r) < 1e4 ? fmt(r, 6) : r.toExponential(2)) + ")</span>";
      }).join("");
      var last = zs[zs.length - 1];
      if (Math.abs(f.r(last)) < 1e-9) {
        note.textContent = "収束しました (|r| < 10⁻⁹)。答えの近くでは、合っている桁数がおよそ倍々に増えます。";
      } else if (!isFinite(last) || last < v[0] || last > v[1]) {
        note.textContent = "z がグラフの外へ飛び出しました。答えから遠いと接線の近似が外れて、遠くへ飛ばされることがあります。LM 法の減衰は、これを防ぐためのものです。";
      } else if (fn === "atan" && Math.abs(zs[0]) > 1.39) {
        note.textContent = "arctan z は遠くで傾きが小さいので、接線が 0 になる所は遠くにあります。z₀ が約 1.39 より大きいと、1 回ごとに答えから遠ざかります。";
      } else {
        note.textContent = "青い線が今の点での接線、白丸が接線が 0 になる点 (次の z) です。「1 回進める」を押してください。";
      }
    }
    stepBtn.addEventListener("click", step);
    resetBtn.addEventListener("click", reset);
    slider.input.addEventListener("input", reset);
    onResize(canvas, draw);
    onTheme(draw);
    reset();
  }

  // ------------------------------------------------------------------ 2. MPPI の重み (05 章)
  function demoWeights(root) {
    var body = shell(root, "MPPI の重み", "S(u) = 2(u − 2)² + 8、今の案は u = 0。サンプルの重みと、更新後の案");
    var svg = svgEl("0 0 420 300", "サンプルのコストと重み");
    body.appendChild(svg);
    var controls = el("div", { class: "controls" });
    var sL = sliderRow("λ (目盛り)", { min: "-2", max: "2", step: "0.01", value: "0" }, function (v) { var l = Math.pow(10, v); return l < 10 ? l.toFixed(2) : l.toFixed(0); });
    var sS = sliderRow("σ (ゆらぎ)", { min: "0.2", max: "4", step: "0.1", value: "2" }, function (v) { return v.toFixed(1); });
    var selK = el("select", { "aria-label": "サンプル数 K" });
    [5, 20, 100, 1000].forEach(function (k) { selK.appendChild(el("option", { value: String(k) }, "K = " + k)); });
    var resample = el("button", { type: "button", class: "btn" }, "サンプルを引き直す");
    controls.appendChild(sL.row);
    controls.appendChild(sS.row);
    controls.appendChild(selK);
    controls.appendChild(resample);
    body.appendChild(controls);
    var readout = el("div", { class: "readout" });
    body.appendChild(readout);
    body.appendChild(el("div", { class: "legend" },
      '<span><i class="dot" style="--c:var(--mppi)"></i>サンプル (大きく濃いほど重い)</span>' +
      '<span><i style="--c:var(--mppi)"></i>重みつき平均 = 更新後の案</span>' +
      '<span><i class="dash" style="--c:var(--opt)"></i>サンプル無限のときの値 (06 章)</span>' +
      '<span><i class="dash" style="--c:var(--muted)"></i>コストの最小点 u = 2</span>'));
    var BASE_Z = [-0.5, 0.25, 0.5, 1.25, 2.0]; // σ = 2 のとき u = -1, 0.5, 1, 2.5, 4
    var seed = 0, Z = [];
    function drawZ() {
      var K = parseInt(selK.value, 10);
      var randn = window.Ctrl.makeNormal(window.Ctrl.mulberry32(1000 + seed));
      Z = [];
      for (var k = 0; k < K; k++) Z.push(seed === 0 && k < 5 ? BASE_Z[k] : randn());
    }
    var X0 = 40, X1 = 410, U0 = -5, U1 = 7, TOP = 24, BOT = 170, SMAX = 60, WB = 268, WH = 58;
    function px(u) { return X0 + (u - U0) / (U1 - U0) * (X1 - X0); }
    function py(s) { return BOT - Math.min(s, SMAX) / SMAX * (BOT - TOP); }
    function S(u) { return 2 * (u - 2) * (u - 2) + 8; }
    function render() {
      var lam = Math.pow(10, sL.value()), sig = sS.value(), K = Z.length;
      var us = Z.map(function (z) { return sig * z; });
      var Ss = us.map(S);
      var Smin = Math.min.apply(null, Ss);
      var e = Ss.map(function (s) { return Math.exp(-(s - Smin) / lam); });
      var eta = e.reduce(function (p, q) { return p + q; }, 0);
      var w = e.map(function (x) { return x / eta; });
      var mean = 0, sq = 0, wmax = 0;
      for (var k = 0; k < K; k++) { mean += w[k] * us[k]; sq += w[k] * w[k]; if (w[k] > wmax) wmax = w[k]; }
      var th = 8 * sig * sig / (lam + 4 * sig * sig);
      var s = "";
      [20, 40, 60].forEach(function (v) {
        s += '<line x1="' + X0 + '" y1="' + py(v) + '" x2="' + X1 + '" y2="' + py(v) + '" style="stroke:var(--line)"/>' +
          '<text x="' + (X0 - 6) + '" y="' + (py(v) + 4) + '" text-anchor="end" style="fill:var(--muted);font-size:11px">' + v + "</text>";
      });
      s += '<line x1="' + X0 + '" y1="' + BOT + '" x2="' + X1 + '" y2="' + BOT + '" style="stroke:var(--muted)"/>';
      s += '<line x1="' + X0 + '" y1="' + WB + '" x2="' + X1 + '" y2="' + WB + '" style="stroke:var(--muted)"/>';
      s += '<text x="4" y="14" style="fill:var(--muted);font-size:12px">コスト S</text>';
      s += '<text x="4" y="' + (WB - WH - 8) + '" style="fill:var(--muted);font-size:12px">重み w</text>';
      for (var t = -4; t <= 6; t += 2) {
        s += '<text x="' + px(t) + '" y="' + (WB + 16) + '" text-anchor="middle" style="fill:var(--muted);font-size:11px">' + (t === 0 ? "0 (今の案)" : fmt(t, 0)) + "</text>";
      }
      s += '<text x="' + X1 + '" y="' + (WB + 30) + '" text-anchor="end" style="fill:var(--muted);font-size:12px">サンプルの入力 u</text>';
      var curve = [];
      for (var i = 0; i <= 200; i++) {
        var u = U0 + (U1 - U0) * i / 200;
        if (S(u) <= SMAX) curve.push([px(u), py(S(u))]);
      }
      s += '<polyline points="' + pts(curve) + '" style="fill:none;stroke:var(--ink);stroke-width:2"/>';
      s += '<line x1="' + px(2) + '" y1="' + (TOP - 8) + '" x2="' + px(2) + '" y2="' + WB + '" style="stroke:var(--muted);stroke-dasharray:3 3"/>';
      var tx = px(Math.max(U0, Math.min(U1, th)));
      s += '<line x1="' + tx + '" y1="' + (TOP - 8) + '" x2="' + tx + '" y2="' + WB + '" style="stroke:var(--opt);stroke-width:1.5;stroke-dasharray:5 3"/>';
      var few = K <= 20;
      var order = us.map(function (_, j) { return j; }).sort(function (a, b) { return w[a] - w[b]; });
      var dots = "", bars = "";
      order.forEach(function (j) {
        var tw = w[j] / wmax;
        var x = px(Math.max(U0, Math.min(U1, us[j]))).toFixed(1);
        var y = py(Ss[j]).toFixed(1);
        var r = (few ? 4 + 4 * Math.sqrt(tw) : 1.5 + 2.5 * Math.sqrt(tw)).toFixed(1);
        var op = few ? (tw < 0.01 ? 0.8 : 0.35 + 0.65 * tw) : (tw < 0.01 ? 0.25 : 0.2 + 0.6 * tw);
        var fill = tw < 0.01 ? "var(--muted)" : "var(--mppi)";
        if ((Ss[j] <= SMAX && us[j] >= U0 && us[j] <= U1) || few) {
          dots += '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" style="fill:' + fill + ';fill-opacity:' + op.toFixed(2) + '"><title>u = ' + fmt(us[j], 2) + ", S = " + Ss[j].toFixed(2) + ", w = " + w[j].toFixed(4) + "</title></circle>";
        }
        if (tw >= 0.005) {
          bars += '<line x1="' + x + '" y1="' + WB + '" x2="' + x + '" y2="' + (WB - WH * tw).toFixed(1) + '" style="stroke:var(--mppi);stroke-width:' + (few ? 3 : 1.5) + ";stroke-opacity:" + (few ? 1 : 0.6) + '"/>';
        }
      });
      var mx = px(Math.max(U0, Math.min(U1, mean)));
      s += bars;
      s += '<line x1="' + mx + '" y1="' + (TOP - 8) + '" x2="' + mx + '" y2="' + WB + '" style="stroke:var(--mppi);stroke-width:2.5"/>';
      s += dots;
      svg.innerHTML = s;
      readout.innerHTML = "<span>更新後の案 (重みつき平均) <b>" + fmt(mean, 2) + "</b></span>" +
        "<span>ESS <b>" + (1 / sq).toFixed(1) + "</b> / K = " + K + "</span>" +
        "<span>サンプル無限なら <b>" + fmt(th, 2) + "</b></span>";
    }
    sL.input.addEventListener("input", render);
    sS.input.addEventListener("input", render);
    selK.addEventListener("change", function () { drawZ(); render(); });
    resample.addEventListener("click", function () { seed += 1; drawZ(); render(); });
    onTheme(render);
    drawZ();
    render();
  }

  // ------------------------------------------------------------------ 3. ぼかしたコスト (06 章)
  function demoSmooth(root, mode) {
    var body = shell(root, "ぼかしたコストの坂", "MPPI の更新量 Δu = −(σ²/λ) F′λ(ū) を、元のコストの傾きと比べる");
    var svg = svgEl("0 0 420 250", "元のコスト S と、ぼかしたコスト F_λ");
    body.appendChild(svg);
    var cost = mode === "quad" ? "quad" : "step";
    var DEF = { step: { u: -0.6, sig: 0.5, view: [-2.5, 2.5, -0.4, 4.8], umin: -2, umax: 2 },
                quad: { u: 0, sig: 1.0, view: [-1.5, 4.5, 5, 31], umin: -1, umax: 3.5 } };
    var controls = el("div", { class: "controls" });
    var sU = sliderRow("今の案 ū", { min: "-2", max: "2", step: "0.05", value: String(DEF[cost].u) }, function (v) { return fmt(v, 2); });
    var sS = sliderRow("σ (ゆらぎ)", { min: "0.1", max: "1.5", step: "0.05", value: String(DEF[cost].sig) }, function (v) { return v.toFixed(2); });
    var sL = sliderRow("λ (目盛り)", { min: "-1", max: "1", step: "0.01", value: "0" }, function (v) { return Math.pow(10, v).toFixed(2); });
    controls.appendChild(seg([["step", "段差のコスト"], ["quad", "2 次のコスト"]], cost, function (m) {
      cost = m;
      sU.input.min = String(DEF[cost].umin);
      sU.input.max = String(DEF[cost].umax);
      sU.input.value = String(DEF[cost].u);
      sS.input.value = String(DEF[cost].sig);
      sU.sync(); sS.sync();
      render();
    }));
    controls.appendChild(sU.row);
    controls.appendChild(sS.row);
    controls.appendChild(sL.row);
    body.appendChild(controls);
    sU.input.min = String(DEF[cost].umin);
    sU.input.max = String(DEF[cost].umax);
    sU.input.value = String(DEF[cost].u);
    sU.sync();
    var readout = el("div", { class: "readout" });
    body.appendChild(readout);
    body.appendChild(el("div", { class: "legend" },
      '<span><i style="--c:var(--ink)"></i>元のコスト S</span>' +
      '<span><i style="--c:var(--mppi)"></i>ぼかしたコスト F<sub>λ</sub></span>' +
      '<span><i style="--c:var(--mppi)"></i>→ MPPI の更新 (サンプル無限)</span>'));
    var note = el("p", { class: "note" });
    body.appendChild(note);
    var H = 4, A = 4, C = 2, S0 = 8;
    function model(u, sig, lam) {
      if (cost === "step") {
        var p = Phi(-u / sig), eh = Math.exp(-H / lam);
        var E = p * eh + 1 - p;
        var dE = (1 - eh) * phi(u / sig) / sig;
        return { S: u < 0 ? H : 0, dS: 0, F: -lam * Math.log(E), du: sig * sig * dE / E };
      }
      var den = lam + A * sig * sig;
      return {
        S: 0.5 * A * (u - C) * (u - C) + S0, dS: A * (u - C),
        F: S0 - 0.5 * lam * Math.log(lam / den) + lam * A * (u - C) * (u - C) / (2 * den),
        du: -A * (u - C) / (A + lam / (sig * sig))
      };
    }
    function render() {
      var ub = sU.value(), sig = sS.value(), lam = Math.pow(10, sL.value());
      var v = DEF[cost].view, L = 34, R = 10, T = 12, B = 26, W = 420, Hh = 250;
      function X(u) { return L + (u - v[0]) / (v[1] - v[0]) * (W - L - R); }
      function Y(y) { return T + (v[3] - Math.max(v[2], Math.min(v[3], y))) / (v[3] - v[2]) * (Hh - T - B); }
      var s = "";
      var ticksY = cost === "step" ? [0, 1, 2, 3, 4] : [10, 15, 20, 25, 30];
      ticksY.forEach(function (t) {
        s += '<line x1="' + L + '" y1="' + Y(t) + '" x2="' + (W - R) + '" y2="' + Y(t) + '" style="stroke:var(--line)"/>' +
          '<text x="' + (L - 5) + '" y="' + (Y(t) + 4) + '" text-anchor="end" style="fill:var(--muted);font-size:11px">' + t + "</text>";
      });
      for (var t = Math.ceil(v[0]); t <= v[1]; t += 1) {
        s += '<text x="' + X(t) + '" y="' + (Hh - 8) + '" text-anchor="middle" style="fill:var(--muted);font-size:11px">' + fmt(t, 0) + "</text>";
      }
      var sp = [], fp = [];
      for (var i = 0; i <= 240; i++) {
        var u = v[0] + (v[1] - v[0]) * i / 240;
        var m = model(u, sig, lam);
        fp.push([X(u), Y(m.F)]);
        if (cost === "quad") sp.push([X(u), Y(m.S)]);
      }
      if (cost === "step") sp = [[X(v[0]), Y(H)], [X(0), Y(H)], [X(0), Y(0)], [X(v[1]), Y(0)]];
      if (cost === "quad") s += '<line x1="' + X(C) + '" y1="' + T + '" x2="' + X(C) + '" y2="' + (Hh - B) + '" style="stroke:var(--muted);stroke-dasharray:3 3"/>';
      s += '<polyline points="' + pts(sp) + '" style="fill:none;stroke:var(--ink);stroke-width:2"/>';
      s += '<polyline points="' + pts(fp) + '" style="fill:none;stroke:var(--mppi);stroke-width:2.4"/>';
      var mb = model(ub, sig, lam);
      var x1 = X(ub), y1 = Y(mb.F), x2 = X(Math.max(v[0], Math.min(v[1], ub + mb.du)));
      s += '<defs><marker id="smooth-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill:var(--mppi)"/></marker></defs>';
      if (Math.abs(x2 - x1) > 3) s += '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y1 + '" style="stroke:var(--mppi);stroke-width:2.2" marker-end="url(#smooth-ah)"/>';
      s += '<circle cx="' + x1 + '" cy="' + y1 + '" r="5" style="fill:var(--mppi)"/>';
      s += '<circle cx="' + x1 + '" cy="' + Y(mb.S) + '" r="4.5" style="fill:var(--ink)"/>';
      svg.innerHTML = s;
      var html = "<span>S の傾き S′(ū) <b>" + fmt(mb.dS, 2) + "</b></span>" +
        "<span>MPPI の更新量 Δu <b>" + fmt(mb.du, 3) + "</b></span>" +
        "<span>更新後 ū + Δu <b>" + fmt(ub + mb.du, 3) + "</b></span>";
      if (cost === "quad") html += "<span>ニュートン法なら <b>" + fmt(C - ub, 3) + "</b></span>";
      readout.innerHTML = html;
      if (cost === "step") {
        note.textContent = ub < 0
          ? "黒い点 (元のコスト) は平らな所にあり、傾きは 0 です。オレンジのぼかしたコストには右へ下る坂があるので、MPPI は接触しない側 (u ≥ 0) へ動きます。ū を −2 まで離したり σ を小さくしたりすると、ゆらぎが段差に届かず、更新はほぼ 0 になります。"
          : "すでに接触しない側にいます。段差に近いほど、ぼかしたコストの坂に押されて少し遠ざかります。";
      } else {
        note.textContent = "2 次のコストでは、更新量は −(A + λ/σ²)⁻¹ S′(ū) (A = 4) で、LM 法と同じ形です。λ を小さく・σ を大きくするとニュートン法 (一気に最小点 u = 2 へ) に近づき、λ を大きくすると慎重になります。";
      }
    }
    [sU, sS, sL].forEach(function (x) { x.input.addEventListener("input", render); });
    onTheme(render);
    render();
  }

  // ------------------------------------------------------------------ 4. NMPC と MPPI (04, 07 章)
  function sceneColors() {
    return {
      floor: css("--bg"), wall: css("--line"), grid: css("--line"), ink: css("--ink"),
      muted: css("--muted"), mpc: css("--mpc"), mppi: css("--mppi"), surface: css("--surface")
    };
  }
  // 1 つの制御器の場面を描く。c は ctrl.js の createNMPC / createMPPI の戻り値
  function drawWorld(cv, c, opts) {
    var C = window.Ctrl, P = C.P;
    opts = opts || {};
    var ctx = cv.getContext("2d");
    if (!ctx) return;
    var Wc = cv.width, Hc = cv.height;
    var k = Wc / Math.max(1, cv.clientWidth || Wc);
    var s = Wc / 10;
    function X(x) { return x * s; }
    function Y(y) { return (3 - y) * s; }
    var col = sceneColors();
    var N = P.N, w = c.world, fin = w.finished();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.fillStyle = col.floor;
    ctx.fillRect(0, 0, Wc, Hc);
    ctx.fillStyle = col.wall;
    ctx.fillRect(0, 0, Wc, Y(P.yWall));
    ctx.fillRect(0, Y(-P.yWall), Wc, Hc - Y(-P.yWall));
    ctx.strokeStyle = col.grid;
    ctx.globalAlpha = 0.6;
    ctx.lineWidth = k;
    ctx.beginPath();
    for (var gx = 1; gx < 10; gx++) { ctx.moveTo(X(gx), Y(P.yWall)); ctx.lineTo(X(gx), Y(-P.yWall)); }
    for (var gy = -2; gy <= 2; gy++) { ctx.moveTo(0, Y(gy)); ctx.lineTo(Wc, Y(gy)); }
    ctx.stroke();
    ctx.globalAlpha = 1;
    // ゴール
    var g = P.goal, gs = 0.2;
    ctx.strokeStyle = col.ink;
    ctx.lineWidth = 2.5 * k;
    ctx.beginPath();
    ctx.moveTo(X(g.x - gs), Y(g.y - gs)); ctx.lineTo(X(g.x + gs), Y(g.y + gs));
    ctx.moveTo(X(g.x - gs), Y(g.y + gs)); ctx.lineTo(X(g.x + gs), Y(g.y - gs));
    ctx.stroke();
    // 目標点の列
    if (!fin) {
      ctx.fillStyle = col.muted;
      for (var n = 2; n <= N; n += 2) { ctx.beginPath(); ctx.arc(X(c.refX[n]), Y(c.refY[n]), 1.6 * k, 0, Math.PI * 2); ctx.fill(); }
    }
    // MPPI のサンプル (重いほど濃く太い)
    if (!fin && c.kind === "mppi") {
      var K = c.K, wmax = 0, order = [];
      for (var i = 0; i < K; i++) { if (c.w[i] > wmax) wmax = c.w[i]; order.push(i); }
      order.sort(function (a, b) { return c.w[a] - c.w[b]; });
      order.forEach(function (idx) {
        var t = wmax > 0 ? c.w[idx] / wmax : 0;
        if (t < 0.01) { ctx.strokeStyle = col.muted; ctx.globalAlpha = 0.14; ctx.lineWidth = k; }
        else { ctx.strokeStyle = col.mppi; ctx.globalAlpha = 0.2 + 0.8 * t; ctx.lineWidth = (1 + 1.5 * t) * k; }
        var o = idx * (N + 1);
        ctx.beginPath();
        ctx.moveTo(X(c.trajX[o]), Y(c.trajY[o]));
        for (var m = 1; m <= N; m++) ctx.lineTo(X(c.trajX[o + m]), Y(c.trajY[o + m]));
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }
    // NMPC の反復ごとの計画
    if (!fin && c.kind === "nmpc") {
      var L = c.iterX.length;
      for (var it = 0; it < L; it++) {
        ctx.strokeStyle = col.mpc;
        ctx.globalAlpha = 0.18 + 0.3 * (it / Math.max(1, L - 1));
        ctx.lineWidth = 1.5 * k;
        ctx.beginPath();
        ctx.moveTo(X(c.iterX[it][0]), Y(c.iterY[it][0]));
        for (var m2 = 1; m2 <= N; m2++) ctx.lineTo(X(c.iterX[it][m2]), Y(c.iterY[it][m2]));
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    // 人 (動く人はホライズンの最後の予測位置も薄く描く)
    var ring = c.mode === "cliff" ? P.rCol : P.dSafe;
    var tH = N * P.dt;
    w.people.forEach(function (p) {
      if (p.vx || p.vy) {
        var fx = p.x + p.vx * tH, fy = p.y + p.vy * tH;
        ctx.globalAlpha = 0.3;
        ctx.fillStyle = col.muted;
        ctx.beginPath(); ctx.arc(X(fx), Y(fy), P.rPerson * s, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;
        ctx.setLineDash([2 * k, 4 * k]);
        ctx.strokeStyle = col.muted;
        ctx.lineWidth = 1.5 * k;
        ctx.beginPath(); ctx.moveTo(X(p.x), Y(p.y)); ctx.lineTo(X(fx), Y(fy)); ctx.stroke();
      }
      ctx.setLineDash([3 * k, 3 * k]);
      ctx.strokeStyle = col.muted;
      ctx.lineWidth = k;
      ctx.beginPath(); ctx.arc(X(p.x), Y(p.y), ring * s, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = col.muted;
      ctx.beginPath(); ctx.arc(X(p.x), Y(p.y), P.rPerson * s, 0, Math.PI * 2); ctx.fill();
    });
    // 通った道
    ctx.strokeStyle = col.muted;
    ctx.lineWidth = 1.5 * k;
    ctx.setLineDash([4 * k, 4 * k]);
    ctx.beginPath();
    w.trail.forEach(function (pt, ti) { if (ti === 0) ctx.moveTo(X(pt.x), Y(pt.y)); else ctx.lineTo(X(pt.x), Y(pt.y)); });
    ctx.stroke();
    ctx.setLineDash([]);
    // 計画 (NMPC は青、MPPI は黒の太線)
    if (!fin) {
      ctx.strokeStyle = c.kind === "nmpc" ? col.mpc : col.ink;
      ctx.lineWidth = 3 * k;
      ctx.beginPath();
      ctx.moveTo(X(c.planX[0]), Y(c.planY[0]));
      for (var m3 = 1; m3 <= N; m3++) ctx.lineTo(X(c.planX[m3]), Y(c.planY[m3]));
      ctx.stroke();
    }
    // ロボット
    var st = w.state;
    ctx.fillStyle = col.surface;
    ctx.strokeStyle = col.ink;
    ctx.lineWidth = 2 * k;
    ctx.beginPath(); ctx.arc(X(st.x), Y(st.y), P.rRobot * s, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(X(st.x), Y(st.y));
    ctx.lineTo(X(st.x + Math.cos(st.th) * P.rRobot * 1.35), Y(st.y + Math.sin(st.th) * P.rRobot * 1.35));
    ctx.stroke();
  }
  function sizeCanvas(cv, aspect) {
    var w = cv.clientWidth || 480;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = Math.round(w * dpr);
    cv.height = Math.round(w * aspect * dpr);
  }

  function demoDuel(root, mode) {
    if (!window.Ctrl) { root.textContent = "ctrl.js が読み込めませんでした。"; return; }
    var C = window.Ctrl;
    var body = shell(root, "NMPC と MPPI を同じ場面で", "モデル・コスト・場面は同じで、違うのは解き方だけ");
    root.classList.add("wide");
    var KS = [20, 50, 100, 300, 1000];
    var controls = el("div", { class: "controls" });
    var selScene = el("select", { "aria-label": "場面" });
    [["offset", "少しずれて立つ人"], ["headon", "真正面の人"], ["cross", "横切る人"], ["two", "2 人"]].forEach(function (o) {
      selScene.appendChild(el("option", { value: o[0] }, o[1]));
    });
    if (mode && C.SCENES[mode]) selScene.value = mode;
    var selMode = el("select", { "aria-label": "人の罰" });
    [["smooth", "なめらかな罰"], ["cliff", "接触だけ罰"]].forEach(function (o) { selMode.appendChild(el("option", { value: o[0] }, o[1])); });
    var btnPlay = el("button", { type: "button", class: "btn primary", "aria-pressed": "false" }, "再生");
    var btnStep = el("button", { type: "button", class: "btn" }, "1 ステップ");
    var btnReset = el("button", { type: "button", class: "btn" }, "最初から");
    [selScene, selMode, btnPlay, btnStep, btnReset].forEach(function (x) { controls.appendChild(x); });
    body.appendChild(controls);
    var grid = el("div", { class: "demo-grid two" });
    function column(kind, title) {
      var colEl = el("div", { class: "demo-col " + (kind === "nmpc" ? "mpc" : "mppi") });
      colEl.appendChild(el("h4", null, title));
      var cv = el("canvas", { "aria-label": title + " の動き" });
      colEl.appendChild(cv);
      var ro = el("div", { class: "readout" });
      colEl.appendChild(ro);
      var ctl = el("div", { class: "controls" });
      colEl.appendChild(ctl);
      grid.appendChild(colEl);
      return { cv: cv, ro: ro, ctl: ctl };
    }
    var colN = column("nmpc", "NMPC (ガウス・ニュートン法)");
    var colM = column("mppi", "MPPI");
    body.appendChild(grid);
    var sIt = sliderRow("反復回数 / 周期", { min: "1", max: "10", step: "1", value: "3" }, function (v) { return String(v); });
    colN.ctl.appendChild(sIt.row);
    var sLam = sliderRow("λ", { min: "-2", max: "1.5", step: "0.05", value: "0" }, function (v) { var l = Math.pow(10, v); return l < 0.1 ? l.toFixed(3) : (l < 10 ? l.toFixed(2) : l.toFixed(0)); });
    var sSig = sliderRow("σ (ω のゆらぎ)", { min: "0.1", max: "2", step: "0.05", value: "0.8" }, function (v) { return v.toFixed(2); });
    var sK = sliderRow("サンプル数 K", { min: "0", max: "4", step: "1", value: "3" }, function (v) { return String(KS[v]); });
    [sLam, sSig, sK].forEach(function (x) { colM.ctl.appendChild(x.row); });
    body.appendChild(el("div", { class: "legend" },
      '<span><i style="--c:var(--mpc)"></i>NMPC の計画 (薄い線は反復の途中)</span>' +
      '<span><i style="--c:var(--mppi)"></i>MPPI のサンプル (濃く太いほど重い)</span>' +
      '<span><i style="--c:var(--ink)"></i>MPPI の計画 (重みつき平均)</span>' +
      '<span><i class="dash" style="--c:var(--muted)"></i>通った道 / 人の安全距離</span>'));
    body.appendChild(el("p", { class: "note" },
      "「真正面の人」では NMPC が人の手前で止まり、「接触だけ罰」では NMPC が人に気づかず接触します (04 章 8 節)。" +
      "MPPI の λ を小さくするとガタつき、大きくすると更新が進まなくなります (05 章 5 節)。"));

    var seed = 7, nm = null, mp = null;
    var playing = false, raf = 0, last = 0, doneAt = 0, userPaused = false;
    function lam() { return Math.pow(10, sLam.value()); }
    function create() {
      nm = C.createNMPC({ scene: selScene.value, mode: selMode.value, iters: sIt.value() });
      mp = C.createMPPI({ scene: selScene.value, mode: selMode.value, lambda: lam(), sigmaW: sSig.value(), K: KS[sK.value()], seed: seed });
      doneAt = 0;
    }
    function readout(c, ro) {
      var w = c.world, fin = w.finished();
      var status = "";
      if (w.arrived) status = "ゴール到着";
      else if (fin) status = "時間切れ";
      else if (w.t > 3 && c.uV[0] < 0.05) status = "止まっている";
      ro.innerHTML = "<span>時刻 <b>" + w.t.toFixed(1) + "</b> 秒</span>" +
        "<span>v <b>" + (fin ? 0 : c.uV[0]).toFixed(2) + "</b></span>" +
        "<span>接触 <b>" + w.contacts + "</b> 回</span>" +
        "<span>評価 <b>" + c.rollouts + "</b> 回/周期</span>" +
        (c.kind === "mppi" ? "<span>ESS <b>" + c.lastEss.toFixed(1) + "</b></span>" : "") +
        (status ? '<span class="status">' + status + "</span>" : "");
    }
    function draw() { drawWorld(colN.cv, nm); drawWorld(colM.cv, mp); readout(nm, colN.ro); readout(mp, colM.ro); }
    function resize() { sizeCanvas(colN.cv, 0.6); sizeCanvas(colM.cv, 0.6); draw(); }
    function bothDone() { return nm.world.finished() && mp.world.finished(); }
    function stepBoth() { nm.step(); mp.step(); draw(); }
    function restart() { seed += 1; create(); draw(); }
    function frame(ts) {
      raf = 0;
      if (!playing) return;
      if (!last) last = ts;
      if (ts - last >= 100) {
        last = ts;
        if (bothDone()) {
          if (!doneAt) doneAt = ts; else if (ts - doneAt > 1500) restart();
        } else {
          stepBoth();
        }
      }
      raf = window.requestAnimationFrame(frame);
    }
    function setPlaying(on) {
      playing = on;
      btnPlay.textContent = on ? "一時停止" : "再生";
      btnPlay.setAttribute("aria-pressed", String(on));
      if (on && !raf) { last = 0; raf = window.requestAnimationFrame(frame); }
    }
    btnPlay.addEventListener("click", function () { userPaused = playing; setPlaying(!playing); });
    btnStep.addEventListener("click", function () {
      userPaused = true;
      setPlaying(false);
      if (bothDone()) { restart(); return; }
      stepBoth();
    });
    btnReset.addEventListener("click", restart);
    selScene.addEventListener("change", restart);
    selMode.addEventListener("change", restart);
    function onParam() {
      nm.opts.iters = sIt.value();
      mp.opts.lambda = lam();
      mp.opts.sigmaW = sSig.value();
      mp.opts.K = KS[sK.value()];
      if (!playing) {
        if (!nm.world.finished()) nm.optimize();
        if (!mp.world.finished()) mp.optimize();
        draw();
      }
    }
    [sIt, sLam, sSig, sK].forEach(function (x) { x.input.addEventListener("input", onParam); });
    onResize(colN.cv, resize);
    onTheme(draw);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { if (!userPaused && !reducedMotion()) setPlaying(true); }
          else if (playing) setPlaying(false);
        });
      }, { threshold: 0.25 }).observe(root);
    }
    create();
    resize();
  }

  // ------------------------------------------------------------------ トップページ: MPPI が 2 人をよける
  function heroMPPI(canvas) {
    if (!window.Ctrl) return;
    var C = window.Ctrl, seed = 11, c = null, raf = 0, last = 0, doneAt = 0, visible = true;
    function create() { c = C.createMPPI({ scene: "two", mode: "smooth", lambda: 1.0, sigmaW: 0.8, K: 300, seed: seed }); doneAt = 0; }
    function resize() { sizeCanvas(canvas, 0.6); drawWorld(canvas, c); }
    function frame(ts) {
      raf = 0;
      if (!visible) return;
      if (!last) last = ts;
      if (ts - last >= 100) {
        last = ts;
        if (c.world.finished()) {
          if (!doneAt) doneAt = ts; else if (ts - doneAt > 1200) { seed += 1; create(); }
        } else {
          c.step();
        }
        drawWorld(canvas, c);
      }
      raf = window.requestAnimationFrame(frame);
    }
    function start() { if (!raf && !reducedMotion()) { last = 0; raf = window.requestAnimationFrame(frame); } }
    create();
    if (reducedMotion()) { for (var i = 0; i < 38; i++) c.step(); }
    onResize(canvas, resize);
    onTheme(function () { drawWorld(canvas, c); });
    resize();
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) { visible = entry.isIntersecting; if (visible) start(); });
      }, { threshold: 0.1 }).observe(canvas);
    } else {
      start();
    }
  }

  // ------------------------------------------------------------------ 起動
  var map = { newton: demoNewton, weights: demoWeights, smooth: demoSmooth, duel: demoDuel };
  document.querySelectorAll("[data-demo]").forEach(function (node) {
    var f = map[node.getAttribute("data-demo")];
    if (f) {
      try { f(node, node.getAttribute("data-mode")); } catch (e) { node.textContent = "デモの初期化に失敗しました: " + e.message; }
    }
  });
  var hero = document.getElementById("hero-mppi");
  if (hero) heroMPPI(hero);
})();
