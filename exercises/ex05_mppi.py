"""演習 5: MPPI。ランダムに試して、コストの低いものほど重くして平均する

実行: python exercises/ex05_mppi.py
出力: docs/figures/ex05_mppi_samples.png, docs/figures/ex05_mppi_lambda.png

(1) 手計算できる例: サンプル 3 本 (ゆらぎ ε = +0.5, 0, -0.5、コスト 10, 11, 14) の重みと更新量
(2) 2 輪ロボットで 1 回だけ更新して、サンプルと重みを見る
(3) λ を変えて動かす: 小さすぎるとガタつき、大きすぎると更新が進まない
"""

from __future__ import annotations

import numpy as np

from common import C_INK, C_MPPI, C_MUTED, C_OK, C_OPT, fig_path, setup_matplotlib
from robot2d import MPPI, P, World, draw_scene


def weights(S, lam):
    w = np.exp(-(np.asarray(S) - np.min(S)) / lam)
    return w / w.sum()


def worked_example():
    eps = np.array([0.5, 0.0, -0.5])
    S = np.array([10.0, 11.0, 14.0])
    print("(1) サンプル 3 本: ゆらぎ ε =", eps, " コスト S =", S)
    for lam in (0.3, 1.0, 10.0):
        w = weights(S, lam)
        print(f"    λ = {lam:4.1f}: 重み w = ({w[0]:.3f}, {w[1]:.3f}, {w[2]:.3f}), "
              f"更新量 Σ w ε = {w @ eps:+.3f}, ESS = 1/Σw² = {1 / np.sum(w**2):.2f}")


def one_update():
    """人の 2.5 m 手前で、まっすぐ進む案から 1 回だけ更新する"""
    world = World("offset")
    world.state = np.array([2.5, 0.0, 0.0])
    m = MPPI(world=world, lam=1.0, K=300, seed=3)
    N = P["N"]
    m.V, m.W = np.full(N, 0.8), np.zeros(N)
    from robot2d import cost, make_ref
    S0, x0, y0 = cost(world, "smooth", make_ref(world.state), m.V, m.W, return_traj=True)
    m.optimize()
    return world, m, (S0, x0, y0)


def run_lambda(lam, scene="offset", seed=2):
    m = MPPI(scene, "smooth", lam=lam, K=300, seed=seed)
    omegas, ess = [], []
    while not m.world.finished():
        omegas.append(m.W[0])
        ess.append(m.ess)
        m.step()
    return m, np.array(omegas), np.array(ess)


def main():
    worked_example()

    world, m, (S0, x0, y0) = one_update()
    s = m.samples
    print("\n(2) 1 回の更新 (K = 300, λ = 1)")
    print(f"    更新前の案のコスト {S0:.1f} → 更新後の案のコスト {m.S:.1f}")
    print(f"    サンプルのコスト: 最小 {s['S'].min():.1f}, 中央値 {np.median(s['S']):.1f}, 最大 {s['S'].max():.1f}")
    print(f"    いちばん重いサンプルの重み {s['w'].max():.3f}, 重み 0.01 以上のサンプル {np.sum(s['w'] >= 0.01)} 本, ESS = {m.ess:.1f}")

    print("\n(3) λ を変えて動かす (少しずれて立つ人, K = 300)")
    runs = {}
    for lam in (0.01, 1.0, 100.0):
        mm, om, ess = run_lambda(lam)
        runs[lam] = (mm, om, ess)
        print(f"    λ = {lam:6.2f}: ゴール到着 {mm.world.arrived} ({mm.world.t:4.1f} 秒), ESS の平均 {ess.mean():6.1f}, "
              f"ω の 1 ステップごとの変化の平均 {np.abs(np.diff(om)).mean():.2f} rad/s")

    plt = setup_matplotlib()
    # ---- 図 1: 1 回の更新
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5), gridspec_kw=dict(width_ratios=[1.55, 1]))
    ax = axes[0]
    draw_scene(ax, world)
    ax.set_xlim(2.0, 6.2)
    ax.set_ylim(-1.6, 1.6)
    w = s["w"]
    order = np.argsort(w)
    wmax = w.max()
    for k in order:
        t = w[k] / wmax
        if t < 0.01:
            ax.plot(s["xs"][k], s["ys"][k], color=C_MUTED, lw=0.5, alpha=0.25)
        else:
            ax.plot(s["xs"][k], s["ys"][k], color=C_MPPI, lw=0.6 + 1.6 * t, alpha=0.25 + 0.75 * t)
    ax.plot(x0, y0, color=C_INK, lw=1.3, ls=(0, (4, 3)), label="更新前の案 (まっすぐ)")
    ax.plot(m.plan_x, m.plan_y, color=C_INK, lw=2.6, label="更新後の案 (重みつき平均)")
    ax.plot([], [], color=C_MPPI, lw=2, label="サンプル (濃く太いほど重い)")
    ax.plot([], [], color=C_MUTED, lw=1, alpha=0.6, label="サンプル (重み ≈ 0)")
    ax.legend(fontsize=8, loc="lower left", ncol=2)
    ax.set_title("1 回の更新: K = 300 本を試して重みつき平均", fontsize=11)
    ax = axes[1]
    ax.scatter(s["S"], w, s=10, color=C_MPPI, alpha=0.7)
    Sg = np.linspace(s["S"].min(), s["S"].min() + 8, 100)
    ax.plot(Sg, np.exp(-(Sg - s["S"].min()) / m.lam) * wmax, color=C_INK, lw=1, label=r"$\propto e^{-(S-S_{\min})/\lambda}$")
    ax.set_xlim(s["S"].min() - 0.5, s["S"].min() + 8)
    ax.set_xlabel("サンプルのコスト S")
    ax.set_ylabel("重み w")
    ax.set_title("コストが 1 増えるごとに重みは 1/e 倍 (λ = 1)", fontsize=11)
    ax.legend(fontsize=9)
    fig.tight_layout()
    out1 = fig_path("ex05_mppi_samples.png")
    fig.savefig(out1)

    # ---- 図 2: λ の効果
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), gridspec_kw=dict(width_ratios=[1.45, 1]))
    colors = {0.01: C_OPT, 1.0: C_MPPI, 100.0: C_OK}
    ax = axes[0]
    draw_scene(ax, runs[1.0][0].world)
    ax.set_ylim(-1.7, 1.7)
    for lam, (mm, om, ess) in runs.items():
        tr = np.array(mm.world.trail)
        ax.plot(tr[:, 0], tr[:, 1], color=colors[lam], lw=2,
                label=f"λ = {lam:g}  ({mm.world.t:.1f} 秒, ESS の平均 {ess.mean():.0f})")
    ax.legend(fontsize=8.5, loc="lower left")
    ax.set_title("通った道 (かっこ内はゴールまでの時間)", fontsize=11)
    ax = axes[1]
    for lam, (mm, om, ess) in runs.items():
        ax.plot(np.arange(len(om)) * P["dt"], om, color=colors[lam], lw=1.2 if lam == 0.01 else 1.8)
    ax.set_xlim(0, 16.5)
    ax.set_xlabel("時刻 [s]")
    ax.set_ylabel("角速度 ω [rad/s]")
    ax.set_title("実行した ω (λ が小さいとガタガタ)", fontsize=11)
    fig.tight_layout()
    out2 = fig_path("ex05_mppi_lambda.png")
    fig.savefig(out2)
    print("\n図を保存しました:", out1, out2)


if __name__ == "__main__":
    main()
