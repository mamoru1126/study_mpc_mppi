"""演習 3: 線形 MPC。コストを入力列の 2 次関数に直して解く。制約があると QP になる

実行: python exercises/ex03_linear_mpc.py
出力: docs/figures/ex03_linear_mpc.png

(1) 手計算できる例: x_{t+1} = x_t + u_t, N = 2, Q = R = P = 1
    H, F を作り、U* = -H^{-1} F x_0 = (-0.6, -0.2) x_0 を確かめる
(2) 台車 (位置 p, 速度 v, 入力は加速度 a) を p = 1 から p = 0 へ止める
    - 制約なしの MPC        : 答えは状態の 1 次式 u = -K x (線形フィードバック)
    - 加速度に上限 |a| <= 0.5:
        (a) 制約なしの答えを上限で切る (クリップ)
        (b) 上限を制約として QP を解く
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from common import C_INK, C_MPC, C_MUTED, C_OPT, fig_path, setup_matplotlib


def condense(A, B, Q, R, Pf, N):
    """X = Φ x_0 + Γ U と書き、J = U^T H U + 2 x_0^T F^T U + 定数 の H, F を返す"""
    nx, nu = B.shape
    Phi = np.zeros((N * nx, nx))
    Gam = np.zeros((N * nx, N * nu))
    for t in range(N):                       # 行ブロック t は x_{t+1}
        Phi[t * nx:(t + 1) * nx] = np.linalg.matrix_power(A, t + 1)
        for s in range(t + 1):               # x_{t+1} は u_0..u_t に依存する
            Gam[t * nx:(t + 1) * nx, s * nu:(s + 1) * nu] = np.linalg.matrix_power(A, t - s) @ B
    Qb = np.kron(np.eye(N), Q)
    Qb[-nx:, -nx:] = Pf                      # 最後の状態だけ重み P
    Rb = np.kron(np.eye(N), R)
    H = Gam.T @ Qb @ Gam + Rb
    F = Gam.T @ Qb @ Phi
    return H, F


def solve_qp_box(H, f, lo, hi, U0):
    """min U^T H U + 2 f^T U  s.t. lo <= U <= hi (箱型の制約だけの QP)"""
    res = minimize(lambda U: (U @ H @ U + 2 * f @ U, 2 * H @ U + 2 * f), np.clip(U0, lo, hi), jac=True,
                   method="L-BFGS-B", bounds=[(lo, hi)] * len(U0),
                   options=dict(ftol=1e-15, gtol=1e-11, maxiter=2000))
    return res.x


def main():
    np.set_printoptions(precision=3, suppress=True)

    print("(1) x_{t+1} = x_t + u_t, N = 2, Q = R = P = 1")
    H, F = condense(np.array([[1.0]]), np.array([[1.0]]), np.eye(1), np.eye(1), np.eye(1), 2)
    print("  H =\n", H)
    print("  F =", F.ravel())
    print("  U* = -H^{-1} F x0 =", -np.linalg.solve(H, F).ravel(), "× x0")

    print("\n(2) 台車: Δt = 0.1 s, N = 20, Q = diag(1, 0.1), R = 0.001, P = Q, 加速度の上限 0.5")
    dt, N, amax = 0.1, 20, 0.5
    A = np.array([[1.0, dt], [0.0, 1.0]])
    B = np.array([[dt * dt / 2], [dt]])
    Q, R = np.diag([1.0, 0.1]), np.array([[0.001]])
    H, F = condense(A, B, Q, R, Q, N)
    K = np.linalg.solve(H, F)[0]
    print(f"  制約なしの答えの最初の入力: u_0 = -K x,  K = {K}")

    def simulate(mode, steps=60):
        x = np.array([1.0, 0.0])
        xs, us = [x.copy()], []
        U = np.zeros(N)
        for _ in range(steps):
            if mode == "free":
                u = -(K @ x)
            elif mode == "clip":
                u = float(np.clip(-(K @ x), -amax, amax))
            else:
                U = solve_qp_box(H, F @ x, -amax, amax, U)
                u = U[0]
                U = np.append(U[1:], U[-1])       # ずらして次の初期値に
            x = A @ x + B[:, 0] * u
            xs.append(x.copy())
            us.append(u)
        return np.array(xs), np.array(us)

    res = {m: simulate(m) for m in ("free", "clip", "qp")}
    names = {"free": "制約なし", "clip": "(a) 切る", "qp": "(b) QP"}
    for m, (xs, us) in res.items():
        print(f"  {names[m]:6s}: 最初の入力 {us[0]:+7.2f}, 入力の最大 {np.abs(us).max():5.2f}, "
              f"行き過ぎ (p の最小) {xs[:, 0].min():+.3f}, 3 秒後の p {xs[30, 0]:+.3f}")

    plt = setup_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    t = np.arange(61) * dt
    style = {"free": dict(color=C_MUTED, ls=(0, (2, 2)), lw=2),
             "clip": dict(color=C_OPT, lw=2.2),
             "qp": dict(color=C_MPC, lw=2.6)}
    label = {"free": "制約なし (上限を無視)", "clip": "(a) 制約なしの答えを上限で切る", "qp": "(b) 上限を制約にした QP"}
    for m, (xs, us) in res.items():
        axes[0].plot(t, xs[:, 0], label=label[m], **style[m])
        axes[1].step(t[:-1], us, where="post", label=label[m], **style[m])
    axes[0].axhline(0, color=C_INK, lw=0.8)
    axes[0].set_xlabel("時刻 [s]")
    axes[0].set_ylabel("位置 p [m]")
    axes[0].set_title("位置 (目標は p = 0)", fontsize=11)
    axes[0].legend(fontsize=8.5)
    axes[1].axhspan(-amax, amax, color="#eef3fb", lw=0)
    axes[1].set_ylim(-1.6, 1.0)
    axes[1].set_xlabel("時刻 [s]")
    axes[1].set_ylabel("加速度 a [m/s²]")
    axes[1].set_title("入力 (水色の帯が上限 |a| ≤ 0.5)", fontsize=11)
    axes[1].annotate(f"制約なしは最初 {res['free'][1][0]:.0f} (枠の外)", xy=(0.05, -1.6), xytext=(0.6, -1.35),
                     fontsize=8.5, color=C_MUTED, arrowprops=dict(arrowstyle="->", color=C_MUTED))
    fig.tight_layout()
    out = fig_path("ex03_linear_mpc.png")
    fig.savefig(out)
    print("\n図を保存しました:", out)


if __name__ == "__main__":
    main()
