"""演習 2: ガウス・ニュートン法と LM 法

実行: python exercises/ex02_gauss_newton.py
出力: docs/figures/ex02_gauss_newton.png

(1) 残差が 1 つ: r(z) = z^2 - 2 = 0 を接線で解く (ニュートン法)
(2) 残差が複数: モーターの速度の立ち上がり y = a (1 - e^{-b t}) を 6 点のデータに当てはめる
    - ガウス・ニュートン法の 1 回目のステップを数値で確かめる
    - 最急降下法・ガウス・ニュートン法・LM 法の収束を比べる
    - 出発点が悪いと、ガウス・ニュートン法は暴れ、LM 法は安定する
"""

from __future__ import annotations

import numpy as np

from common import C_INK, C_MPC, C_MPPI, C_MUTED, C_OPT, fig_path, setup_matplotlib

# データ (真の値 a = 1.2, b = 1.5 に小さなノイズを足したもの)
T = np.array([0.25, 0.5, 1.0, 1.5, 2.0, 3.0])
Y = np.array([0.416, 0.582, 0.941, 1.062, 1.131, 1.182])


def residual_and_jacobian(z):
    """残差 r_i = a (1 - e^{-b t_i}) - y_i と J = ∂r/∂(a, b)"""
    a, b = z
    e = np.exp(-b * T)
    r = a * (1.0 - e) - Y
    J = np.stack([1.0 - e, a * T * e], axis=1)
    return r, J


def F(z):
    r, _ = residual_and_jacobian(z)
    return 0.5 * r @ r


def gauss_newton(z0, iters=8):
    z, path = np.array(z0, float), [np.array(z0, float)]
    for _ in range(iters):
        r, J = residual_and_jacobian(z)
        z = z + np.linalg.solve(J.T @ J, -J.T @ r)   # J^T J Δ = -J^T r
        path.append(z.copy())
        if not np.isfinite(F(z)):
            break
    return np.array(path)


def levenberg_marquardt(z0, iters=12, mu=1e-2):
    z, path = np.array(z0, float), [np.array(z0, float)]
    for _ in range(iters):
        r, J = residual_and_jacobian(z)
        H, g = J.T @ J, J.T @ r
        for _ in range(30):                              # 下がるまで慎重にする
            dz = np.linalg.solve(H + mu * np.diag(np.diag(H)), -g)
            if F(z + dz) < F(z):
                z, mu = z + dz, mu / 3                  # 下がった → 大胆に
                break
            mu *= 4                                      # 上がった → 慎重に
        path.append(z.copy())
    return np.array(path)


def gradient_descent(z0, iters=50, alpha=0.5):
    z, path = np.array(z0, float), [np.array(z0, float)]
    for _ in range(iters):
        r, J = residual_and_jacobian(z)
        z = z - alpha * J.T @ r
        path.append(z.copy())
    return np.array(path)


def main():
    np.set_printoptions(precision=4, suppress=True)

    print("(1) r(z) = z^2 - 2 をニュートン法で解く (答え √2 = 1.414214)")
    z = 2.0
    for k in range(4):
        print(f"  z_{k} = {z:.6f}   r = {z * z - 2:+.6f}")
        z = z - (z * z - 2) / (2 * z)

    print("\n(2) y = a (1 - e^{-b t}) の当てはめ。出発点 (a, b) = (1, 1)")
    z0 = np.array([1.0, 1.0])
    r, J = residual_and_jacobian(z0)
    print("  r       =", r)
    print("  J       =\n", J)
    print("  J^T J   =\n", J.T @ J)
    print("  J^T r   =", J.T @ r)
    d = np.linalg.solve(J.T @ J, -J.T @ r)
    print("  Δ       =", d, " → z_1 =", z0 + d)

    gn = gauss_newton(z0)
    lm = levenberg_marquardt(z0)
    gd = gradient_descent(z0)
    print("\n  反復ごとのコスト F = ||r||^2 / 2")
    print("  ガウス・ニュートン:", " ".join(f"{F(z):.2e}" for z in gn[:5]))
    print("  LM               :", " ".join(f"{F(z):.2e}" for z in lm[:5]))
    print("  最急降下 (α=0.5) :", " ".join(f"{F(z):.2e}" for z in gd[[0, 1, 2, 5, 10, 20, 50]]), "(0,1,2,5,10,20,50 回目)")
    zs = gn[-1]
    print(f"  答え: a = {zs[0]:.4f}, b = {zs[1]:.4f}, F = {F(zs):.3e}")

    # 捨てた 2 階微分の項の大きさ (答えの近く)
    r, J = residual_and_jacobian(zs)
    a, b = zs
    e = np.exp(-b * T)
    # r_i のヘッセ行列: ∂²r/∂a² = 0, ∂²r/∂a∂b = t e, ∂²r/∂b² = -a t² e
    S2 = np.array([[0.0, np.sum(r * T * e)], [np.sum(r * T * e), np.sum(-r * a * T**2 * e)]])
    print("\n  答えの近くでの J^T J      =\n", J.T @ J)
    print("  捨てた項 Σ r_i ∇²r_i     =\n", S2, " (小さい)")

    z_bad = np.array([0.5, 0.3])
    gn_bad = gauss_newton(z_bad)
    lm_bad = levenberg_marquardt(z_bad)
    print("\n  出発点 (0.5, 0.3) から")
    print("  ガウス・ニュートン:", " ".join(f"{F(z):.1e}" for z in gn_bad[:6]), "… (暴れる)")
    print("  LM               :", " ".join(f"{F(z):.1e}" for z in lm_bad[:6]))

    # ---------------------------------------------------------------- 図
    plt = setup_matplotlib()
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.9), gridspec_kw=dict(width_ratios=[1, 1.05, 1]))

    ax = axes[0]
    tt = np.linspace(0, 3.2, 200)
    for k, (z, alpha) in enumerate(zip(gn[:3], [0.35, 0.65, 1.0])):
        ax.plot(tt, z[0] * (1 - np.exp(-z[1] * tt)), color=C_MPC, alpha=alpha, lw=2,
                label=f"{k} 回目  a={z[0]:.2f}, b={z[1]:.2f}")
    ax.plot(T, Y, "o", color=C_INK, ms=6, label="データ")
    ax.set_xlabel("時刻 t [s]")
    ax.set_ylabel("速度 y")
    ax.set_title("ガウス・ニュートン法で当てはめ (2 回で収束)", fontsize=11)
    ax.legend(fontsize=8.5, loc="lower right")

    ax = axes[1]
    A, B = np.meshgrid(np.linspace(0.2, 2.2, 220), np.linspace(0.05, 3.2, 220))
    FF = np.vectorize(lambda a, b: F(np.array([a, b])))(A, B)
    ax.contour(A, B, np.log10(FF), levels=14, colors=C_MUTED, linewidths=0.6, linestyles="solid")
    ax.plot(*gd[:51].T, "-", color=C_OPT, lw=1.2, label="最急降下 (1, 1) から 50 回")
    ax.plot(*gn[:3].T, "o-", color=C_MPC, lw=2, ms=4, label="ガウス・ニュートン (1, 1) から")
    ax.plot(*lm_bad[:6].T, "s-", color=C_MPPI, lw=1.8, ms=4, label="LM (0.5, 0.3) から")
    ax.plot(*gn_bad[:2].T, "--", color=C_MPC, lw=1.2)
    ax.text(0.24, 0.92, "ガウス・ニュートン\n(0.5, 0.3) から:\n1 回目で枠の外へ", fontsize=8.5, color=C_MPC,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
    ax.plot(*zs, "*", color=C_INK, ms=12)
    ax.set_xlim(0.2, 2.2)
    ax.set_ylim(0.05, 3.2)
    ax.set_xlabel("a")
    ax.set_ylabel("b")
    ax.set_title("コスト F(a, b) の等高線と、たどった道", fontsize=11)
    ax.legend(fontsize=8, loc="lower right", frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)

    ax = axes[2]
    ax.semilogy(range(len(gd)), [F(z) - F(zs) + 1e-12 for z in gd], color=C_OPT, label="最急降下 (1, 1) から")
    ax.semilogy(range(len(gn)), [F(z) - F(zs) + 1e-12 for z in gn], "o-", color=C_MPC, ms=4, label="ガウス・ニュートン (1, 1) から")
    ax.semilogy(range(len(lm)), [F(z) - F(zs) + 1e-12 for z in lm], "s--", color=C_MPPI, ms=4, label="LM (1, 1) から")
    ax.semilogy(range(len(lm_bad)), [F(z) - F(zs) + 1e-12 for z in lm_bad], "s-", color=C_MPPI, ms=3, alpha=0.5, label="LM (0.5, 0.3) から")
    ax.set_ylim(1e-12, 1e3)
    ax.set_xlim(0, 30)
    ax.set_xlabel("反復回数")
    ax.set_ylabel("F - F* (答えとのコストの差)")
    ax.set_title("収束の速さ", fontsize=11)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    out = fig_path("ex02_gauss_newton.png")
    fig.savefig(out)
    print("\n図を保存しました:", out)


if __name__ == "__main__":
    main()
