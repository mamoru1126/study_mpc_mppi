"""演習 4: 非線形 MPC (single shooting + ガウス・ニュートン法)

実行: python exercises/ex04_nmpc.py
出力: docs/figures/ex04_nmpc_iterations.png, docs/figures/ex04_nmpc_closed_loop.png

(1) 連鎖律で作ったヤコビアン J が、数値微分と一致することを確かめる
(2) 1 回の最適化の中で、反復ごとに計画がどう良くなるかを見る (少しずれて立つ人)
(3) 毎周期 3 回だけ反復して動かす (RTI に近い使い方)
    - 少しずれて立つ人・なめらかな罰 → よけてゴールへ
    - 真正面に立つ人・なめらかな罰   → 手前で止まる (局所解)
    - 少しずれて立つ人・接触だけ罰   → 罰の傾きが 0 なので気づかず接触する
"""

from __future__ import annotations

import numpy as np

from common import C_INK, C_MPC, C_MUTED, fig_path, setup_matplotlib
from robot2d import NMPC, P, World, cost, draw_scene, make_ref, residual_and_jacobian, run


def check_jacobian():
    world = World("offset")
    rng = np.random.default_rng(0)
    N = P["N"]
    V, W = rng.uniform(0.2, 0.9, N), rng.uniform(-0.5, 0.5, N)
    ref = make_ref(world.state)
    r, J, _ = residual_and_jacobian(world, "smooth", ref, V, W)
    z = np.concatenate([V, W])
    Jn = np.zeros_like(J)
    eps = 1e-6
    for i in range(2 * N):
        zp = z.copy()
        zp[i] += eps
        rp, _, _ = residual_and_jacobian(world, "smooth", ref, zp[:N], zp[N:])
        Jn[:, i] = (rp - r) / eps
    print(f"(1) J の大きさ {J.shape[0]} 行 × {J.shape[1]} 列 (残差の数 × 変数の数 2N)")
    print(f"    連鎖律の J と数値微分の差の最大: {np.abs(J - Jn).max():.1e}")
    print(f"    S = ||r||^2 = {r @ r:.4f},  cost() で計算した S = {cost(world, 'smooth', ref, V, W):.4f}")


def iterations_from_straight(N=50):
    """人の 2.5 m 手前で、まっすぐ進む案から、ガウス・ニュートン法 (LM) を 1 回ずつ進める

    人の向こう側まで見えるように、この図だけホライズンを 5 秒 (N = 50) にする
    """
    world = World("offset")
    world.state = np.array([2.5, 0.0, 0.0])
    ref = make_ref(world.state, N)
    V, W = np.full(N, 0.8), np.zeros(N)
    mu = 1e-3
    paths, costs = [], []
    for it in range(10):
        S, xs, ys = cost(world, "smooth", ref, V, W, return_traj=True)
        paths.append((xs, ys))
        costs.append(S)
        r, J, _ = residual_and_jacobian(world, "smooth", ref, V, W)
        H, g = J.T @ J, J.T @ r
        for _ in range(20):
            dz = np.linalg.solve(H + np.diag(mu * (np.diag(H) + 1e-3)), -g)
            Vn = np.clip(V + dz[:N], P["v_min"], P["v_max"])
            Wn = np.clip(W + dz[N:], -P["w_max"], P["w_max"])
            if cost(world, "smooth", ref, Vn, Wn) < S:
                V, W, mu = Vn, Wn, max(mu / 3, 1e-7)
                break
            mu *= 4
    return world, paths, costs


def main():
    check_jacobian()

    world, paths, costs = iterations_from_straight()
    print("\n(2) 人の 2.5 m 手前で、まっすぐ進む案から始めたときのコスト S (反復ごと、N = 50)")
    print("    " + "  ".join(f"{c:.2f}" for c in costs))

    print("\n(3) 毎周期 3 回反復して動かす")
    cases = [("offset", "smooth", "少しずれて立つ人・なめらかな罰"),
             ("headon", "smooth", "真正面に立つ人・なめらかな罰"),
             ("offset", "cliff", "少しずれて立つ人・接触だけ罰")]
    results = []
    for scene, mode, title in cases:
        ctrl = NMPC(scene, mode, iters=3)
        out = run(ctrl)
        out["ctrl"] = ctrl
        results.append(out)
        state = "ゴール到着" if out["arrived"] else "時間切れ"
        print(f"    {title:18s}: {state} {out['t']:4.1f} 秒, 接触 {out['contacts']} 回, "
              f"人との最小のすき間 {out['min_clear']:+.2f} m, 最後の評価回数 {ctrl.evals} 回/周期")

    plt = setup_matplotlib()
    # ---- 図 1: 反復ごとの計画
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), gridspec_kw=dict(width_ratios=[1.6, 1]))
    ax = axes[0]
    draw_scene(ax, world)
    ax.set_ylim(-1.6, 1.6)
    ax.set_xlim(2.0, 7.0)
    show = [0, 1, 2, 3, 5]
    for i, k in enumerate(show):
        a = 0.25 + 0.75 * i / (len(show) - 1)
        if k == 0:
            ax.plot(*paths[k], color=C_INK, lw=1.3, ls=(0, (4, 3)), label="0 回目 (まっすぐ)", zorder=3)
        else:
            ax.plot(*paths[k], color=C_MPC, alpha=a, lw=2.4 if k == show[-1] else 1.4, label=f"{k} 回目", zorder=3)
    ax.plot(*make_ref(world.state, 50), ".", color=C_MUTED, ms=2.5, label="目標点の列", zorder=2)
    ax.plot([world.state[0]], [world.state[1]], "o", color=C_INK, ms=6)
    ax.legend(fontsize=8.5, loc="lower left", ncol=2)
    ax.set_title("反復ごとの計画 (この図だけ 5 秒先まで)", fontsize=11)
    ax = axes[1]
    ax.plot(range(len(costs)), costs, "o-", color=C_MPC)
    ax.set_ylim(0, 300)
    ax.set_xlabel("反復回数")
    ax.set_ylabel("コスト S")
    ax.set_title("反復ごとのコスト", fontsize=11)
    fig.tight_layout()
    out1 = fig_path("ex04_nmpc_iterations.png")
    fig.savefig(out1)

    # ---- 図 2: 閉ループ
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 2.9))
    for ax, (scene, mode, title), out in zip(axes, cases, results):
        ctrl = out["ctrl"]
        draw_scene(ax, ctrl.world, mode)
        ax.set_ylim(-1.7, 1.7)
        tr = out["trail"]
        ax.plot(tr[:, 0], tr[:, 1], color=C_MPC, lw=2.4)
        x, y, th = ctrl.world.state
        ax.add_patch(plt.Circle((x, y), P["r_robot"], fc="white", ec=C_INK, lw=1.5))
        ax.plot([x, x + 0.35 * np.cos(th)], [y, y + 0.35 * np.sin(th)], color=C_INK, lw=1.5)
        state = "ゴール到着" if out["arrived"] else "止まったまま時間切れ"
        if out["contacts"]:
            state += f"・接触 {out['contacts']} 回"
        ax.set_title(f"{title}\n→ {state}", fontsize=10)
    fig.tight_layout()
    out2 = fig_path("ex04_nmpc_closed_loop.png")
    fig.savefig(out2)
    print("\n図を保存しました:", out1, out2)


if __name__ == "__main__":
    main()
