"""演習 1: 最適制御問題を解いて動かす。「1 回だけ計画」と「毎周期計画し直す」の違い

実行: python exercises/ex01_receding_horizon.py
出力: docs/figures/ex01_receding_horizon.png

- ロボットは (1, 0) から (9, 0) のゴールへ、p_y = 0 の線に沿って 0.8 m/s で進みたい。
- 実際には、モデルが知らない横風 (+y 向きに 0.15 m/s) が吹いている。
- (a) 開ループ: 最初に 10 秒分の入力列を 1 回だけ計画し、そのまま最後まで実行する。
- (b) receding horizon: 3 秒先 (N = 30) まで計画し、最初の 1 手だけ実行して、毎周期計画し直す。
- 最適化の中身は 02〜04 章で扱うので、ここでは scipy の汎用ソルバー (L-BFGS-B) に任せる。
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from common import C_INK, C_MPC, C_MUTED, C_OPT, fig_path, setup_matplotlib
from robot2d import P, World, draw_scene, residual_and_jacobian

WIND = (0.0, 0.15)  # モデルが知らない外乱 [m/s]


def line_ref(state, N):
    """目標軌道: p_y = 0 の線の上を、今の p_x から v_ref で進む点の列 (ゴールで止まる)"""
    x = np.minimum(state[0] + P["v_ref"] * np.arange(N + 1) * P["dt"], P["goal"][0])
    return x, np.zeros(N + 1)


def solve_ocp(world: World, N: int, V0, W0):
    """有限ホライズン最適制御問題を解いて、入力列 (V, W) と目標軌道を返す"""
    ref = line_ref(world.state, N)

    def f(z):
        r, J, _ = residual_and_jacobian(world, "smooth", ref, z[:N], z[N:])
        return r @ r, 2.0 * J.T @ r  # コスト S = ||r||^2 とその勾配

    bounds = [(P["v_min"], P["v_max"])] * N + [(-P["w_max"], P["w_max"])] * N
    res = minimize(f, np.concatenate([V0, W0]), jac=True, method="L-BFGS-B", bounds=bounds,
                   options=dict(maxiter=300))
    return res.x[:N], res.x[N:], ref, res.fun


def predicted_path(state, V, W):
    x, y, th = state
    xs, ys = [x], [y]
    for v, w in zip(V, W):
        x += v * np.cos(th) * P["dt"]
        y += v * np.sin(th) * P["dt"]
        th += w * P["dt"]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)


def open_loop():
    world = World("empty")
    N = 100
    V, W, _, _ = solve_ocp(world, N, np.full(N, 0.5), np.zeros(N))
    plan = predicted_path(world.state, V, W)
    for v, w in zip(V, W):
        world.apply(v, w, WIND)
        if world.arrived:
            break
    return world, plan


def receding_horizon():
    world = World("empty")
    N = P["N"]
    V, W = np.full(N, 0.5), np.zeros(N)
    plans = []
    while not world.finished():
        V, W, _, S = solve_ocp(world, N, V, W)
        plans.append((world.t, predicted_path(world.state, V, W)))
        world.apply(V[0], W[0], WIND)                  # 最初の 1 手だけ実行
        V, W = np.append(V[1:], V[-1]), np.append(W[1:], W[-1])  # 1 ステップずらして次の初期値に
    return world, plans


def main():
    plt = setup_matplotlib()
    w_ol, plan_ol = open_loop()
    w_rh, plans = receding_horizon()
    g = np.array(P["goal"])
    e_ol = np.linalg.norm(w_ol.state[:2] - g)
    e_rh = np.linalg.norm(w_rh.state[:2] - g)
    print("横風 +y 0.15 m/s (モデルは知らない)")
    e_plan = np.hypot(plan_ol[0][-1] - g[0], plan_ol[1][-1] - g[1])
    print(f"(a) 開ループ (1 回だけ計画)      : 計画の上ではゴールとの距離 {e_plan:.2f} m → 実際は {w_ol.t:4.1f} 秒後に {e_ol:.2f} m")
    print(f"(b) receding horizon (毎周期計画): {w_rh.t:4.1f} 秒でゴール到着 (0.2 m 以内) = {w_rh.arrived}, 最後の距離 {e_rh:.2f} m")
    print(f"    計画し直した回数: {len(plans)} 回 (0.1 秒ごと)")

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw=dict(width_ratios=[1.35, 1]))
    ax = axes[0]
    draw_scene(ax, w_rh)
    ax.set_ylim(-1.45, 1.9)
    tr_ol = np.array(w_ol.trail)
    tr_rh = np.array(w_rh.trail)
    ax.plot(*plan_ol, color=C_MUTED, lw=1.5, ls=(0, (4, 3)), label="(a) 最初の計画 (予測)")
    ax.plot(tr_ol[:, 0], tr_ol[:, 1], color=C_OPT, lw=2.2, label="(a) 開ループで実際に通った道")
    for t, (px, py) in plans[::20]:
        ax.plot(px, py, color=C_MPC, lw=1.0, alpha=0.45)
    ax.plot([], [], color=C_MPC, lw=1.0, alpha=0.45, label="(b) 各時刻の計画 (2 秒ごと)")
    ax.plot(tr_rh[:, 0], tr_rh[:, 1], color=C_MPC, lw=2.6, label="(b) receding horizon で通った道")
    ax.annotate("", xy=(2.6, 1.6), xytext=(2.6, 1.0), arrowprops=dict(arrowstyle="-|>", color=C_INK, lw=1.5))
    ax.text(2.75, 1.3, "横風 0.15 m/s (モデルは知らない)", fontsize=9, color=C_INK, va="center")
    ax.legend(loc="lower right", fontsize=8.5, ncol=2)
    ax.set_title("通った道", fontsize=11)

    ax = axes[1]
    t_ol = np.arange(len(tr_ol)) * P["dt"]
    t_rh = np.arange(len(tr_rh)) * P["dt"]
    ax.plot(t_ol, tr_ol[:, 1], color=C_OPT, lw=2.2, label="(a) 開ループ")
    ax.plot(t_rh, tr_rh[:, 1], color=C_MPC, lw=2.6, label="(b) receding horizon")
    ax.set_xlabel("時刻 [s]")
    ax.set_ylabel("横方向のずれ $p_y$ [m]")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("ゴールの線 ($p_y = 0$) からのずれ", fontsize=11)
    fig.tight_layout()
    out = fig_path("ex01_receding_horizon.png")
    fig.savefig(out)
    print("図を保存しました:", out)


if __name__ == "__main__":
    main()
