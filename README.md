# study_mpc_mppi

勾配法の MPC（ガウス・ニュートン法、非線形 MPC）と、サンプリングで解く MPPI を、数式とアルゴリズムの左右対比で整理した学習用の資料（大学学部レベル）。

- 解説ページ：[index.html](index.html)
- 公開ページ：https://mamoru1126.github.io/study_mpc_mppi/

## 見方

`index.html` をブラウザで開く。GitHub Pages（master ブランチのルート）を有効にすると、上の URL で見られる。

## 中身

- 共通の最適制御問題（OCP）と receding horizon、差動 2 輪のモデルとコスト
- 定式化の対比：MPC（LQ の閉形式・QP）と MPPI（KL 正則化、重点サンプリングによる更新式）
- アルゴリズムの対比：NMPC（SQP / ガウス・ニュートン）と MPPI の手順・擬似コード・計算量
- ガウス・ニュートン法：導出、ニュートン法・LM 法との比較、MPC での残差とヤコビアン
- 非線形 MPC：single / multiple shooting、SQP、Real-Time Iteration、障害物制約と局所解
- MPPI の λ（Nav2 の `temperature`）の意味
- 2 つの更新の関係：K→∞ の MPPI は平滑化コストへの前処理つき勾配法、2 次コストでは減衰 λΣ⁻¹ の LM 法
- 得意・苦手の対比、Nav2 MPPI のパラメータとの対応
- 動く図：MPPI の重みと λ、NMPC（ガウス・ニュートン）と MPPI を同じコストで並べて動かすデモ

図とデモはすべてこの資料のために作ったもので、論文の図は転載していない。

## ファイル

- `index.html`：解説ページ（CSS と JavaScript を含む 1 ファイル）
- `assets/katex/`：数式の表示に使う [KaTeX](https://katex.org/) 0.16.47（MIT License、`assets/katex/LICENSE`）
