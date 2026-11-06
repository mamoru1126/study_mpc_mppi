"""2 輪ロボット (差動 2 輪) の場面と、NMPC・MPPI の小さな実装

HTML 版のデモ (tools/site/ctrl.js) を numpy に移したものです。パラメータも同じです。

- 状態 x = (p_x, p_y, θ)、入力 u = (v, ω)
- モデル: x_{t+1} = x_t + Δt (v cosθ, v sinθ, ω)
- コスト S = Σ_t [ q_ref ||p_t - p_t^ref||^2 + q_ω ω_t^2 + (人の罰) + (壁の罰) ] + q_T ||p_N - p_N^ref||^2
    人の罰は 2 種類:
      mode="smooth": 人から d_safe より内側に入った深さの 2 乗 × q_o (なめらか)
      mode="cliff" : 人に接触したら (中心間距離 < r_col) 1 ステップごとに +1000 (段差)
- NMPC: single shooting + ガウス・ニュートン法 (LM 減衰、解析ヤコビアン、入力の上下限は射影)
- MPPI: サンプル K 本の重みつき平均
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# パラメータ (ctrl.js と同じ)
# ---------------------------------------------------------------------------
P = dict(
    dt=0.1, N=30,
    v_min=0.0, v_max=1.0, w_max=1.5,
    r_robot=0.25, r_person=0.3, margin=0.5,
    start=(1.0, 0.0, 0.0), goal=(9.0, 0.0),
    v_ref=0.8, y_wall=2.75,
    q_ref=1.0, q_w=0.1, q_o=40.0, q_wall=100.0, q_T=5.0, cliff=1000.0,
    goal_tol=0.2, time_limit=25.0,
)
P["r_col"] = P["r_robot"] + P["r_person"]   # 接触とみなす中心間距離 0.55 m
P["d_safe"] = P["r_col"] + P["margin"]       # なめらかな罰が始まる中心間距離 1.05 m
P["y_lim"] = P["y_wall"] - P["r_robot"]

SCENES = {
    "empty": [],                                               # 人なし (01 章)
    "offset": [dict(x=5.0, y=0.25, vx=0.0, vy=0.0)],           # 少しずれて立つ人
    "headon": [dict(x=5.0, y=0.0, vx=0.0, vy=0.0)],            # 真正面に立つ人
    "cross": [dict(x=5.5, y=-2.3, vx=0.0, vy=0.5, bounce_y=2.3)],  # 横切る人
    "two": [dict(x=4.0, y=-0.45, vx=0.0, vy=0.0),
            dict(x=8.6, y=0.5, vx=-0.4, vy=0.0, min_x=1.5)],   # 2 人
}


# ---------------------------------------------------------------------------
# 環境 (ロボットの真の状態と人)
# ---------------------------------------------------------------------------
@dataclass
class World:
    scene: str = "offset"
    state: np.ndarray = field(default_factory=lambda: np.array(P["start"], dtype=float))
    people: list = field(default_factory=list)
    t: float = 0.0
    trail: list = field(default_factory=list)
    arrived: bool = False
    contacts: int = 0
    in_contact: bool = False
    min_clear: float = np.inf

    def __post_init__(self):
        if not self.people:
            self.people = copy.deepcopy(SCENES[self.scene])
        self.trail = [self.state[:2].copy()]

    def apply(self, v: float, w: float, disturbance=(0.0, 0.0)):
        """入力 (v, ω) で 1 ステップ進める。disturbance は位置に足す外乱 [m/s]"""
        dt = P["dt"]
        x, y, th = self.state
        x += v * np.cos(th) * dt + disturbance[0] * dt
        y += v * np.sin(th) * dt + disturbance[1] * dt
        th += w * dt
        self.state = np.array([x, y, th])
        for p in self.people:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if "bounce_y" in p and abs(p["y"]) > p["bounce_y"]:
                p["vy"] = -p["vy"]
                p["y"] = float(np.clip(p["y"], -p["bounce_y"], p["bounce_y"]))
            if "min_x" in p and p["x"] < p["min_x"]:
                p["x"] = p["min_x"]
                p["vx"] = 0.0
        self.t += dt
        self.trail.append(self.state[:2].copy())
        touching = False
        for p in self.people:
            d = np.hypot(x - p["x"], y - p["y"]) - P["r_col"]
            self.min_clear = min(self.min_clear, d)
            touching = touching or d < 0
        if touching and not self.in_contact:
            self.contacts += 1
        self.in_contact = touching
        if np.hypot(x - P["goal"][0], y - P["goal"][1]) < P["goal_tol"]:
            self.arrived = True

    def finished(self) -> bool:
        return self.arrived or self.t >= P["time_limit"] - 1e-9


# ---------------------------------------------------------------------------
# 目標軌道とコスト
# ---------------------------------------------------------------------------
def make_ref(state, N=None):
    """今の位置からゴールへ向かう直線上を v_ref で進む点の列 (N+1 点)"""
    N = N or P["N"]
    gx, gy = P["goal"]
    dx, dy = gx - state[0], gy - state[1]
    D = np.hypot(dx, dy) or 1.0
    s = np.minimum(1.0, P["v_ref"] * np.arange(N + 1) * P["dt"] / D)
    return state[0] + s * dx, state[1] + s * dy


def rollout(state, V, W):
    """入力列 V, W (形は (N,) か (K, N)) から位置の列 (…, N+1) を返す"""
    V = np.atleast_2d(V)
    W = np.atleast_2d(W)
    K, N = V.shape
    dt = P["dt"]
    xs = np.empty((K, N + 1))
    ys = np.empty((K, N + 1))
    th = np.full(K, state[2], dtype=float)
    xs[:, 0], ys[:, 0] = state[0], state[1]
    for n in range(N):
        xs[:, n + 1] = xs[:, n] + V[:, n] * np.cos(th) * dt
        ys[:, n + 1] = ys[:, n] + V[:, n] * np.sin(th) * dt
        th = th + W[:, n] * dt
    return xs, ys


def cost(world: World, mode: str, ref, V, W, return_traj=False):
    """入力列のコスト S。V, W が (K, N) なら K 本ぶんをまとめて計算する"""
    squeeze = np.ndim(V) == 1
    xs, ys = rollout(world.state, V, W)
    Wm = np.atleast_2d(W)
    K, N1 = xs.shape
    N = N1 - 1
    refx, refy = ref
    ex = xs[:, 1:] - refx[None, 1:]
    ey = ys[:, 1:] - refy[None, 1:]
    S = P["q_ref"] * (ex**2 + ey**2).sum(1) + P["q_w"] * (Wm**2).sum(1)
    tF = np.arange(1, N + 1) * P["dt"]
    for p in world.people:
        d = np.hypot(xs[:, 1:] - (p["x"] + p["vx"] * tF), ys[:, 1:] - (p["y"] + p["vy"] * tF))
        if mode == "cliff":
            S += P["cliff"] * (d < P["r_col"]).sum(1)
        else:
            h = np.maximum(0.0, P["d_safe"] - d)
            S += P["q_o"] * (h**2).sum(1)
    ay = np.maximum(0.0, np.abs(ys[:, 1:]) - P["y_lim"])
    S += P["q_wall"] * (ay**2).sum(1)
    S += P["q_T"] * ((xs[:, -1] - refx[-1]) ** 2 + (ys[:, -1] - refy[-1]) ** 2)
    if squeeze:
        S = S[0]
        xs, ys = xs[0], ys[0]
    return (S, xs, ys) if return_traj else S


# ---------------------------------------------------------------------------
# NMPC: single shooting + ガウス・ニュートン法 (LM)
# ---------------------------------------------------------------------------
def position_jacobian(state, V, W):
    """位置 p_n = (x_n, y_n) の入力 z = (v_0..v_{N-1}, ω_0..ω_{N-1}) に対する微分

    連鎖律 ∂x_n/∂u_j = A_{n-1} … A_{j+1} B_j を 2 輪モデルで具体的に書くと
      ∂x_n/∂v_j = cosθ_j Δt,   ∂x_n/∂ω_j = -Δt^2 Σ_{i=j+1}^{n-1} v_i sinθ_i
      ∂y_n/∂v_j = sinθ_j Δt,   ∂y_n/∂ω_j =  Δt^2 Σ_{i=j+1}^{n-1} v_i cosθ_i
    (j < n。ω_j は θ_{j+1} 以降の向きを変え、その後の移動の向きを変える)
    """
    N = len(V)
    dt = P["dt"]
    th = state[2] + np.concatenate([[0.0], np.cumsum(W) * dt])  # θ_0..θ_N
    As = np.concatenate([[0.0], np.cumsum(V * np.sin(th[:N]))])  # As[k] = Σ_{i<k} v_i sinθ_i
    Ac = np.concatenate([[0.0], np.cumsum(V * np.cos(th[:N]))])
    n = np.arange(N + 1)[:, None]
    j = np.arange(N)[None, :]
    mv = j < n
    mw = j <= n - 2
    Dx = np.zeros((N + 1, 2 * N))
    Dy = np.zeros((N + 1, 2 * N))
    Dx[:, :N] = np.where(mv, np.cos(th[:N])[None, :] * dt, 0.0)
    Dy[:, :N] = np.where(mv, np.sin(th[:N])[None, :] * dt, 0.0)
    Dx[:, N:] = np.where(mw, -dt * dt * (As[n] - As[np.minimum(j + 1, N)]), 0.0)
    Dy[:, N:] = np.where(mw, dt * dt * (Ac[n] - Ac[np.minimum(j + 1, N)]), 0.0)
    return Dx, Dy


def residual_and_jacobian(world: World, mode: str, ref, V, W):
    """S = ||r||^2 となる残差 r と、そのヤコビアン J = ∂r/∂z を返す (段差の罰は含めない)"""
    N = len(V)
    xs, ys = rollout(world.state, V, W)
    xs, ys = xs[0], ys[0]
    Dx, Dy = position_jacobian(world.state, V, W)
    refx, refy = ref
    rows, res = [], []
    sr, so, sw, sT = (np.sqrt(P[k]) for k in ("q_ref", "q_o", "q_wall", "q_T"))
    for n in range(1, N + 1):
        rows += [sr * Dx[n], sr * Dy[n]]
        res += [sr * (xs[n] - refx[n]), sr * (ys[n] - refy[n])]
        if mode != "cliff":
            tF = n * P["dt"]
            for p in world.people:
                dx = xs[n] - (p["x"] + p["vx"] * tF)
                dy = ys[n] - (p["y"] + p["vy"] * tF)
                d = np.hypot(dx, dy)
                if 1e-9 < d < P["d_safe"]:
                    rows.append(-so * (dx * Dx[n] + dy * Dy[n]) / d)
                    res.append(so * (P["d_safe"] - d))
        ay = abs(ys[n]) - P["y_lim"]
        if ay > 0:
            rows.append(sw * np.sign(ys[n]) * Dy[n])
            res.append(sw * ay)
    rows += [sT * Dx[N], sT * Dy[N]]
    res += [sT * (xs[N] - refx[N]), sT * (ys[N] - refy[N])]
    sq = np.sqrt(P["q_w"])
    for k in range(N):
        e = np.zeros(2 * N)
        e[N + k] = sq
        rows.append(e)
        res.append(sq * W[k])
    return np.array(res), np.array(rows), (xs, ys)


class NMPC:
    """single shooting + ガウス・ニュートン法 (LM 減衰)。1 周期に iters 回だけ反復する"""

    kind = "nmpc"

    def __init__(self, scene="offset", mode="smooth", iters=3, world=None):
        self.mode, self.iters = mode, iters
        self.world = world or World(scene)
        N = P["N"]
        self.V = np.full(N, 0.5)
        self.W = np.zeros(N)
        self.mu = 1e-3
        self.evals = 0
        for _ in range(5):          # 最初だけ多めに反復してから始める
            self.optimize()

    def optimize(self):
        N = P["N"]
        self.ref = make_ref(self.world.state)
        S = cost(self.world, self.mode, self.ref, self.V, self.W)
        self.evals = 1
        self.iter_paths = []
        for _ in range(self.iters):
            r, J, path = residual_and_jacobian(self.world, self.mode, self.ref, self.V, self.W)
            self.iter_paths.append(path)
            H, g = J.T @ J, J.T @ r
            accepted = False
            for _ in range(8):
                Hs = H + np.diag(self.mu * (np.diag(H) + 1e-3))
                dz = np.linalg.solve(Hs, -g)
                Vn = np.clip(self.V + dz[:N], P["v_min"], P["v_max"])
                Wn = np.clip(self.W + dz[N:], -P["w_max"], P["w_max"])
                Sn = cost(self.world, self.mode, self.ref, Vn, Wn)
                self.evals += 1
                if Sn < S:
                    self.V, self.W, S = Vn, Wn, Sn
                    self.mu = max(self.mu / 3, 1e-7)
                    accepted = True
                    break
                self.mu = min(self.mu * 4, 1e8)
            if not accepted:
                break
        self.S = S
        _, self.plan_x, self.plan_y = cost(self.world, self.mode, self.ref, self.V, self.W, return_traj=True)

    def step(self, disturbance=(0.0, 0.0)):
        if self.world.finished():
            return
        self.world.apply(self.V[0], self.W[0], disturbance)
        if self.world.finished():
            return
        self.V = np.append(self.V[1:], self.V[-1])   # 1 ステップずらす (ウォームスタート)
        self.W = np.append(self.W[1:], self.W[-1])
        self.optimize()


# ---------------------------------------------------------------------------
# MPPI
# ---------------------------------------------------------------------------
class MPPI:
    """K 本のサンプルの重みつき平均。σ_v = 0.35 σ_ω (ctrl.js と同じ)"""

    kind = "mppi"

    def __init__(self, scene="offset", mode="smooth", lam=1.0, sigma_w=0.8, K=300, seed=1, world=None):
        self.mode, self.lam, self.sigma_w, self.K = mode, lam, sigma_w, K
        self.rng = np.random.default_rng(seed)
        self.world = world or World(scene)
        N = P["N"]
        self.V = np.full(N, 0.5)
        self.W = np.zeros(N)
        for _ in range(5):
            self.optimize()

    def optimize(self):
        N, K = P["N"], self.K
        self.ref = make_ref(self.world.state)
        sv, sw = 0.35 * self.sigma_w, self.sigma_w
        Vs = np.clip(self.V + sv * self.rng.standard_normal((K, N)), P["v_min"], P["v_max"])
        Ws = np.clip(self.W + sw * self.rng.standard_normal((K, N)), -P["w_max"], P["w_max"])
        S, xs, ys = cost(self.world, self.mode, self.ref, Vs, Ws, return_traj=True)
        w = np.exp(-(S - S.min()) / self.lam)
        w /= w.sum()
        self.samples = dict(S=S, w=w, xs=xs, ys=ys)
        self.ess = 1.0 / np.sum(w**2)
        self.V = np.clip(self.V + w @ (Vs - self.V), P["v_min"], P["v_max"])
        self.W = np.clip(self.W + w @ (Ws - self.W), -P["w_max"], P["w_max"])
        self.S, self.plan_x, self.plan_y = cost(self.world, self.mode, self.ref, self.V, self.W, return_traj=True)
        self.evals = K + 1

    def step(self, disturbance=(0.0, 0.0)):
        if self.world.finished():
            return
        self.world.apply(self.V[0], self.W[0], disturbance)
        if self.world.finished():
            return
        self.V = np.append(self.V[1:], self.V[-1])
        self.W = np.append(self.W[1:], self.W[-1])
        self.optimize()


def run(ctrl, max_steps=10_000):
    """ゴールに着くか時間切れまで回し、結果をまとめて返す"""
    plans = []
    while not ctrl.world.finished() and len(plans) < max_steps:
        plans.append((ctrl.world.t, ctrl.plan_x.copy(), ctrl.plan_y.copy()))
        ctrl.step()
    w = ctrl.world
    return dict(trail=np.array(w.trail), arrived=w.arrived, t=w.t, contacts=w.contacts,
                min_clear=w.min_clear, plans=plans)


def draw_scene(ax, world: World, mode="smooth", people_at=None):
    """場面 (壁・ゴール・人) を ax に描く"""
    import matplotlib.patches as mpatches

    from common import C_INK, C_MUTED, C_SHADE

    ax.add_patch(mpatches.Rectangle((0, P["y_wall"]), 10, 0.4, color=C_SHADE, lw=0))
    ax.add_patch(mpatches.Rectangle((0, -P["y_wall"] - 0.4), 10, 0.4, color=C_SHADE, lw=0))
    gx, gy = P["goal"]
    ax.plot([gx], [gy], marker="x", ms=10, mew=2.5, color=C_INK)
    ppl = people_at if people_at is not None else world.people
    ring = P["r_col"] if mode == "cliff" else P["d_safe"]
    for p in ppl:
        ax.add_patch(mpatches.Circle((p["x"], p["y"]), P["r_person"], color=C_MUTED, lw=0))
        ax.add_patch(mpatches.Circle((p["x"], p["y"]), ring, fill=False, ls=(0, (3, 3)), ec=C_MUTED, lw=1))
    ax.set_xlim(0.3, 9.7)
    ax.set_ylim(-2.2, 2.2)
    ax.set_aspect("equal")
    ax.set_xlabel("$p_x$ [m]")
    ax.set_ylabel("$p_y$ [m]")
