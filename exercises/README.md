# 演習

各章の内容を、numpy / scipy / matplotlib だけで確かめるスクリプトです。リポジトリのトップから実行してください。図は `docs/figures/` に保存されます。

```bash
python exercises/check_env.py            # 環境の確認
python exercises/ex01_receding_horizon.py
```

| ファイル | 章 | 内容 | 出力する図 |
| --- | --- | --- | --- |
| `check_env.py` | - | 必要なパッケージと日本語フォントの確認 | - |
| `ex01_receding_horizon.py` | [01](../docs/01_optimal_control.md) | モデルが知らない横風の中で、開ループと receding horizon を比べる | `ex01_receding_horizon.png` |
| `ex02_gauss_newton.py` | [02](../docs/02_least_squares_gauss_newton.md) | ニュートン法の表、ガウス・ニュートン法の 1 回目の数値、最急降下法・LM 法との比較 | `ex02_gauss_newton.png` |
| `ex03_linear_mpc.py` | [03](../docs/03_linear_mpc.md) | $H$, $F$, $U^*$ の手計算との照合、上限で切る制御と QP の比較 | `ex03_linear_mpc.png` |
| `ex04_nmpc.py` | [04](../docs/04_nonlinear_mpc.md) | ヤコビアンの確認、反復ごとの計画、3 つの場面での NMPC | `ex04_nmpc_iterations.png`, `ex04_nmpc_closed_loop.png` |
| `ex05_mppi.py` | [05](../docs/05_mppi_basics.md) | 重みの手計算、1 回の更新、λ の効果 | `ex05_mppi_samples.png`, `ex05_mppi_lambda.png` |
| `ex06_mppi_theory.py` | [06](../docs/06_mppi_theory.md) | ぼかしたコストの坂、サンプル数による誤差、2 次のコストでの式 (5) の確認、理想の分布 | `ex06_mppi_theory.png`, `ex06_distributions.png` |

共通のコード:

| ファイル | 内容 |
| --- | --- |
| `common.py` | 図の保存先、日本語フォントの設定、教材で統一した色 |
| `robot2d.py` | 2 輪ロボットの場面 (人・壁・ゴール)、コスト、NMPC (single shooting + ガウス・ニュートン法)、MPPI。HTML 版のデモ (`tools/site/ctrl.js`) を numpy に移したもので、パラメータも同じ |

所要時間の目安は、全部で 10 秒ほどです。
