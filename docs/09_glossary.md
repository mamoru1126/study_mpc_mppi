# 09. 用語集

教材に出てくる言葉を、日本語・英語・ひとことの説明・主に出てくる章で並べました。辞書として使ってください。

## 最適制御と MPC

| 日本語 | 英語 | ひとことで | 章 |
| --- | --- | --- | --- |
| 状態 | state | ロボットの今の様子を表す数 (位置と向きなど) | [01](01_optimal_control.md) |
| 入力 | input, control | ロボットに与える指令 (速度と角速度など) | [01](01_optimal_control.md) |
| モデル | model, dynamics | 今の状態と入力から次の状態を計算する式 $x_{t+1} = f(x_t, u_t)$ | [01](01_optimal_control.md) |
| ロールアウト | rollout | 入力の列をモデルに順に入れて、未来の状態を計算すること | [01](01_optimal_control.md) |
| コスト | cost, objective | 動きの悪さを表す数。小さいほど良い | [01](01_optimal_control.md) |
| 段コスト | stage cost | 各時刻のコスト $\ell(x_t, u_t)$ | [01](01_optimal_control.md) |
| 終端コスト | terminal cost | 最後の時刻のコスト $\phi(x_N)$。ホライズンの外の代わり | [01](01_optimal_control.md) |
| ホライズン | horizon | 何ステップ先まで予測して考えるか ($N$、または時間 $N\Delta t$) | [01](01_optimal_control.md) |
| 有限ホライズン最適制御問題 | finite-horizon optimal control problem (OCP) | $N$ ステップ先までのコストを最小にする入力の列を求める問題 | [01](01_optimal_control.md) |
| モデル予測制御 | model predictive control (MPC) | 予測して最適な入力の列を求め、最初の 1 手だけ実行する、をくり返す制御 | [01](01_optimal_control.md) |
| receding horizon | receding horizon | 考える範囲が時間とともに後ろへ下がっていくこと。毎周期解き直す | [01](01_optimal_control.md) |
| ウォームスタート | warm start | 前回の答えを 1 ステップずらして、次の計算の出発点にすること | [01](01_optimal_control.md) |
| 開ループ / 閉ループ | open loop / closed loop | 測り直さずに実行する / 測り直して直しながら実行する | [01](01_optimal_control.md) |
| 制約 | constraint | 守るべき条件 (入力の上下限、障害物から離れるなど) | [01](01_optimal_control.md) |
| ソフト制約 / ハード制約 | soft / hard constraint | 破ると罰がつく / 絶対に守る | [01](01_optimal_control.md), [07](07_comparison.md) |
| 罰 (ペナルティ) | penalty | 望ましくない状態にコストを足すこと | [01](01_optimal_control.md) |

## 最適化

| 日本語 | 英語 | ひとことで | 章 |
| --- | --- | --- | --- |
| 最小二乗 | least squares | 残差の 2 乗和を最小にすること | [02](02_least_squares_gauss_newton.md) |
| 残差 | residual | 0 にしたい「ずれ」 | [02](02_least_squares_gauss_newton.md) |
| 正規方程式 | normal equations | 残差が 1 次式のときの最小二乗の答えの式 $A^\top A z = A^\top b$ | [02](02_least_squares_gauss_newton.md) |
| ヤコビアン | Jacobian | 各残差を各変数で微分した値を並べた行列 $J$ | [02](02_least_squares_gauss_newton.md) |
| 勾配 | gradient | コストが最も増える向き。最小二乗では $J^\top r$ | [02](02_least_squares_gauss_newton.md) |
| ヘッセ行列 | Hessian | コストの 2 階微分を並べた行列。曲がり具合 | [02](02_least_squares_gauss_newton.md) |
| 最急降下法 | steepest descent, gradient descent | 勾配の逆向きに進む方法 | [02](02_least_squares_gauss_newton.md) |
| ニュートン法 | Newton's method | 接線 (2 次近似) を使って答えに近づく方法 | [02](02_least_squares_gauss_newton.md) |
| ガウス・ニュートン法 | Gauss–Newton method | 残差を 1 次近似して $J^\top J \Delta = -J^\top r$ を解く方法 | [02](02_least_squares_gauss_newton.md) |
| LM 法 | Levenberg–Marquardt method | ガウス・ニュートン法に減衰 $\mu$ を足して慎重にした方法 | [02](02_least_squares_gauss_newton.md) |
| 減衰 | damping | 歩幅を小さくするために足す項 ($\mu D$) | [02](02_least_squares_gauss_newton.md) |
| 2 次収束 | quadratic convergence | 答えの近くで、合っている桁数がおよそ倍々に増える収束 | [02](02_least_squares_gauss_newton.md) |
| 射影 | projection | 上下限からはみ出した値を、範囲の中に戻すこと | [02](02_least_squares_gauss_newton.md) |
| 2 次計画問題 | quadratic program (QP) | 2 次関数を 1 次の制約のもとで最小にする問題 | [03](03_linear_mpc.md) |
| 凸 | convex | 局所解がそのまま最適解になる性質 | [03](03_linear_mpc.md) |
| 能動集合法 | active-set method | どの制約が効くかを推定しながら QP を解く方法 | [03](03_linear_mpc.md) |
| 内点法 | interior-point method | 制約の内側から境界に近づきながら解く方法 | [03](03_linear_mpc.md) |
| 線形フィードバック | linear feedback | 入力を状態の定数倍 $u = -Kx$ で決める制御 | [03](03_linear_mpc.md) |
| LQR | linear quadratic regulator | 線形モデル・2 次コストで、ホライズン無限の最適なフィードバック | [03](03_linear_mpc.md) |
| 局所解 | local minimum | 近くでいちばん良いが、全体でいちばんとは限らない答え | [04](04_nonlinear_mpc.md) |

## 非線形 MPC

| 日本語 | 英語 | ひとことで | 章 |
| --- | --- | --- | --- |
| 非線形 MPC | nonlinear MPC (NMPC) | 非線形モデルを使う MPC | [04](04_nonlinear_mpc.md) |
| 線形化 | linearization | 今の案のまわりで 1 次式に近似すること ($A_t$, $B_t$) | [04](04_nonlinear_mpc.md) |
| 連鎖律 | chain rule | 合成関数の微分の規則。$\partial x_t / \partial u_s = A_{t-1} \cdots A_{s+1} B_s$ | [04](04_nonlinear_mpc.md) |
| 感度 | sensitivity | 入力を少し変えたとき、後の状態がどれだけ変わるか | [03](03_linear_mpc.md), [04](04_nonlinear_mpc.md) |
| single shooting | single shooting | 入力だけを変数にし、状態はモデルで順に計算する置き方 | [04](04_nonlinear_mpc.md) |
| multiple shooting | multiple shooting | 区間の始点の状態も変数にし、つなぎ目の一致を制約にする置き方 | [04](04_nonlinear_mpc.md) |
| 逐次 2 次計画法 | sequential quadratic programming (SQP) | 近似した QP を解いて直す、をくり返す方法 | [04](04_nonlinear_mpc.md) |
| RTI | real-time iteration | SQP の反復を 1 周期に 1 回だけ行う方法 | [04](04_nonlinear_mpc.md) |

## MPPI

| 日本語 | 英語 | ひとことで | 章 |
| --- | --- | --- | --- |
| MPPI | model predictive path integral | 入力の列を試して、コストの低いものほど重くして平均する MPC | [05](05_mppi_basics.md) |
| サンプル | sample | ゆらぎを足して作った入力の列の 1 本 | [05](05_mppi_basics.md) |
| ゆらぎ | perturbation, noise | 今の案に足すランダムな値 $\varepsilon \sim \mathcal N(0, \Sigma)$ | [05](05_mppi_basics.md) |
| 共分散行列 | covariance matrix | ゆらぎの大きさと相関を表す行列 $\Sigma$ | [05](05_mppi_basics.md) |
| 重み | weight | サンプルの重要度 $w_k \propto e^{-S_k/\lambda}$ | [05](05_mppi_basics.md) |
| $\lambda$ (Nav2 では temperature) | lambda, temperature | コスト差の目盛り。どれくらいの差を大きな差とみなすか | [05](05_mppi_basics.md) |
| 実効サンプル数 | effective sample size (ESS) | 実質的に何本分のサンプルを平均しているか $1 / \sum_k w_k^2$ | [05](05_mppi_basics.md) |
| KL ダイバージェンス | Kullback–Leibler divergence | 2 つの分布の違いの大きさ | [06](06_mppi_theory.md) |
| 重点サンプリング | importance sampling | 引きやすい分布から引いて、重みで補正して平均を求める方法 | [06](06_mppi_theory.md) |
| 自由エネルギー | free energy | ぼかしたコスト $F_\lambda = -\lambda \log \mathbb E[e^{-S/\lambda}]$ | [06](06_mppi_theory.md) |
| Savitzky–Golay フィルタ | Savitzky–Golay filter | 近くの点に多項式を当てはめてなめらかにするフィルタ | [05](05_mppi_basics.md), [08](08_nav2_mppi.md) |

## Nav2

| 日本語 | 英語 | ひとことで | 章 |
| --- | --- | --- | --- |
| Nav2 | Navigation2 | ROS 2 のナビゲーションスタック | [08](08_nav2_mppi.md) |
| コストマップ | costmap | 地図の各マスに、障害物への近さなどのコストを書いた格子 | [08](08_nav2_mppi.md) |
| critic | critic | Nav2 の MPPI で、コストの項を計算するプラグイン | [08](08_nav2_mppi.md) |
| コントローラ | controller | 経路に沿って速度指令を出す部分 (局所的な計画器) | [08](08_nav2_mppi.md) |

---

前へ: [08 Nav2 の MPPI](08_nav2_mppi.md) ｜ 目次: [README](../README.md)
