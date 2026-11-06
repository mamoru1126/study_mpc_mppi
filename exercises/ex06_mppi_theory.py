"""演習 6: MPPI の更新は「ぼかしたコスト」の坂を下っている

実行: python exercises/ex06_mppi_theory.py
出力: docs/figures/ex06_mppi_theory.png

入力が 1 つ (u) の例で確かめる。ゆらぎ ε ~ N(0, σ²)
(1) 段差のコスト S(u) = 4 (u < 0: 接触する側), 0 (u >= 0)
    ぼかしたコスト F_λ(ū) = -λ log E[exp(-S(ū+ε)/λ)] を数値積分で求め、
    理論の更新量 Δu = -(σ²/λ) F_λ'(ū) と、サンプル K 本の MPPI の更新量を比べる
(2) 2 次のコスト S(u) = 2 (u - 2)^2 + 8 (曲がり具合 a = 4, 最小点 c = 2)
    理論の更新量 Δu = -(a + λ/σ²)^{-1} S'(ū) と比べる (LM 法と同じ形)
(3) 理想の分布 q* ∝ p e^{-S/λ} を描き、その平均が MPPI の新しい平均になることを見る
    出力: docs/figures/ex06_distributions.png
"""

from __future__ import annotations

import numpy as np

from common import C_INK, C_MPPI, C_MUTED, fig_path, setup_matplotlib

trapezoid = getattr(np, "trapezoid", None) or np.trapz  # numpy 2 では trapezoid、1.x では trapz


def step_cost(u):
    return np.where(u < 0, 4.0, 0.0)


def quad_cost(u):
    return 2.0 * (u - 2.0) ** 2 + 8.0


def smoothed(S, ubar, sigma, lam):
    """F_λ(ū) = -λ log ∫ N(v; ū, σ²) exp(-S(v)/λ) dv (台形公式)

    v (= ū + ε) の格子を固定して積分するので、S に段差があっても ū について滑らかに計算できる
    """
    v = np.linspace(-12.0, 12.0, 48001)
    ubar = np.atleast_1d(ubar)
    pdf = np.exp(-0.5 * ((v[None, :] - ubar[:, None]) / sigma) ** 2) / (np.sqrt(2 * np.pi) * sigma)
    vals = pdf * np.exp(-S(v) / lam)[None, :]
    return -lam * np.log(trapezoid(vals, v, axis=1))


def theory_step(S, ubar, sigma, lam, h=1e-4):
    dF = (smoothed(S, ubar + h, sigma, lam) - smoothed(S, ubar - h, sigma, lam)) / (2 * h)
    return float(-(sigma**2 / lam) * dF[0])


def mppi_step(S, ubar, sigma, lam, K, rng):
    eps = sigma * rng.standard_normal(K)
    s = S(ubar + eps)
    w = np.exp(-(s - s.min()) / lam)
    w /= w.sum()
    return w @ eps, 1.0 / np.sum(w**2)


def main():
    rng = np.random.default_rng(0)
    sigma, lam, ubar = 0.5, 1.0, -0.6
    print(f"(1) 段差のコスト, σ = {sigma}, λ = {lam}, ū = {ubar}")
    F0 = smoothed(step_cost, ubar, sigma, lam)[0]
    th = theory_step(step_cost, ubar, sigma, lam)
    print(f"    S(ū) = {float(step_cost(ubar)):.1f}, S'(ū) = 0 (平らな所)  /  F_λ(ū) = {F0:.3f}")
    print(f"    理論の更新量 Δu = -(σ²/λ) F_λ'(ū) = {th:+.3f}  → 更新後 ū = {ubar + th:+.3f} (接触しない側へ)")
    errs = {}
    for K in (10, 100, 1000, 10000):
        steps = np.array([mppi_step(step_cost, ubar, sigma, lam, K, rng)[0] for _ in range(300)])
        errs[K] = np.sqrt(np.mean((steps - th) ** 2))
        print(f"    MPPI K = {K:5d}: 更新量の平均 {steps.mean():+.3f}, ばらつき (標準偏差) {steps.std():.3f}")

    print("\n(2) 2 次のコスト S = 2 (u - 2)^2 + 8, ū = 0")
    for sig, lm in ((1.0, 1.0), (2.0, 1.0), (1.0, 4.0)):
        a, grad = 4.0, 4.0 * (0.0 - 2.0)
        closed = -grad / (a + lm / sig**2)
        mc = np.mean([mppi_step(quad_cost, 0.0, sig, lm, 10000, rng)[0] for _ in range(50)])
        print(f"    σ = {sig}, λ = {lm}: 式 -(a + λ/σ²)^(-1) S'(ū) = {closed:.3f},  MPPI (K = 10000) の平均 {mc:.3f}"
              f"   (ニュートン法なら一気に {-grad / a:.0f})")

    # ---------------------------------------------------------------- 図
    plt = setup_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw=dict(width_ratios=[1.3, 1]))
    ax = axes[0]
    u = np.linspace(-2.5, 2.5, 501)
    ax.plot(u, step_cost(u), color=C_INK, lw=2.2, label="段差のコスト S (接触すると 4)")
    for sig, alpha in ((0.25, 0.45), (0.5, 1.0), (1.0, 0.7)):
        ax.plot(u, smoothed(step_cost, u, sig, lam), color=C_MPPI, alpha=alpha, lw=2 if sig == 0.5 else 1.4,
                ls="-" if sig != 1.0 else (0, (4, 2)), label=f"ぼかしたコスト $F_\\lambda$ (σ = {sig})")
    Fb = smoothed(step_cost, ubar, sigma, lam)[0]
    ax.plot([ubar], [Fb], "o", color=C_MPPI, ms=7)
    ax.annotate("", xy=(ubar + th, Fb), xytext=(ubar, Fb),
                arrowprops=dict(arrowstyle="-|>", color=C_MPPI, lw=2))
    ax.text(ubar + th / 2 + 0.15, Fb + 0.35, f"MPPI の更新 Δu = {th:+.2f}", color=C_MPPI, ha="left", fontsize=9,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.0))
    ax.plot([ubar], [4.0], "o", color=C_INK, ms=7)
    ax.text(ubar, 4.25, "S の傾きは 0", ha="center", fontsize=9, color=C_INK)
    ax.set_xlabel("入力 u")
    ax.set_ylabel("コスト")
    ax.set_ylim(-0.3, 4.9)
    ax.set_title(f"段差をぼかすと坂ができる (λ = {lam:g})", fontsize=11)
    ax.legend(fontsize=8, loc="lower left")
    ax = axes[1]
    Ks = np.array(sorted(errs))
    ax.loglog(Ks, [errs[k] for k in Ks], "o-", color=C_MPPI, label="MPPI の更新量の誤差 (RMS)")
    ax.loglog(Ks, errs[10] * np.sqrt(10 / Ks), "--", color=C_MUTED, lw=1.2, label=r"$\propto 1/\sqrt{K}$")
    ax.set_xlabel("サンプル数 K")
    ax.set_ylabel("理論値との差")
    ax.set_title("サンプルを 100 倍にすると誤差は 1/10", fontsize=11)
    ax.legend(fontsize=9)
    fig.tight_layout()
    out = fig_path("ex06_mppi_theory.png")
    fig.savefig(out)
    print("\n図を保存しました:", out)

    # ---- 図 2: 理想の分布 q* と重点サンプリング (2 次のコスト, σ = 1, λ = 1, ū = 0)
    sig, lm = 1.0, 1.0
    u = np.linspace(-3.2, 4.2, 600)
    p = np.exp(-0.5 * (u / sig) ** 2) / (np.sqrt(2 * np.pi) * sig)
    boltz = np.exp(-(quad_cost(u) - 8.0) / lm)
    q = p * boltz
    q /= trapezoid(q, u)
    mean_q = trapezoid(u * q, u)
    print(f"\n(3) q* の平均 = {mean_q:.3f} (式では 4c/(a + λ/σ²) = {8 / (4 + lm / sig**2):.3f})")
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    ax.plot(u, p, color=C_MUTED, lw=2, label=r"いまの分布 $p$ = N(ū = 0, σ² = 1): ここからサンプルを引く")
    ax.plot(u, boltz * p.max(), color=C_INK, lw=1.2, ls=(0, (4, 3)), label=r"$e^{-S/\lambda}$ (コストが低いほど大きい。高さは調整)")
    ax.plot(u, q, color=C_MPPI, lw=2.4, label=r"理想の分布 $q^* \propto p\, e^{-S/\lambda}$")
    ax.axvline(0, color=C_MUTED, lw=1, ls=":")
    ax.axvline(mean_q, color=C_MPPI, lw=1, ls=":")
    ax.axvline(2.0, color=C_INK, lw=1, ls=":")
    ax.annotate("", xy=(mean_q, 0.95), xytext=(0, 0.95), arrowprops=dict(arrowstyle="-|>", color=C_MPPI, lw=2))
    ax.text(mean_q / 2, 1.0, f"新しい平均 = q* の平均 = {mean_q:.2f}", color=C_MPPI, ha="center", fontsize=9)
    ax.text(2.05, 0.75, "S の最小点 c = 2", fontsize=9, color=C_INK)
    rng2 = np.random.default_rng(5)
    eps = sig * rng2.standard_normal(40)
    w = np.exp(-(quad_cost(eps) - quad_cost(eps).min()) / lm)
    w /= w.sum()
    ax.scatter(eps, np.full_like(eps, -0.06), s=8 + 600 * w, color=C_MPPI, alpha=0.6, lw=0,
               label=f"p から引いたサンプル 40 本 (点の大きさ = 重み)。重みつき平均 {w @ eps:.2f}")
    ax.set_ylim(-0.12, 1.1)
    ax.set_xlabel("入力 u")
    ax.set_ylabel("確率密度")
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title("2 次のコスト S = 2 (u - 2)² + 8 のとき (λ = 1)", fontsize=11)
    fig.tight_layout()
    out2 = fig_path("ex06_distributions.png")
    fig.savefig(out2)
    print("図を保存しました:", out2)


if __name__ == "__main__":
    main()
