# study_mpc_mppi

モデル予測制御（MPC）と MPPI の数式を、高校数学（漸化式・平方完成・微分・指数関数・正規分布）で読み解くための解説資料。

- 解説ページ：[index.html](index.html)
- 公開ページ：https://mamoru1126.github.io/study_mpc_mppi/

## 見方

`index.html` をブラウザで開く。GitHub Pages（master ブランチのルート）を有効にすると、上の URL で見られる。

## 中身

- MPC と MPPI に共通する枠組み（モデル＝漸化式、コスト関数、Receding horizon）
- MPC：1 手先・2 手先の例を平方完成で解く、P 制御との関係、等比数列での収束、入力の上限（定義域つきの最小値）
- 2 輪ロボットのモデル、勾配降下法と局所解
- MPPI：正規分布でばらまき、指数関数の重みで平均する更新式、手計算の例、温度 λ の役割、擬似コード
- 動く図：入力の上限、MPPI の重み、2 輪ロボットで人をよける MPPI のデモ
- 発展：なぜ指数関数の重みなのか（log x ≤ x − 1 による証明）、MPPI の更新と勾配降下法のつながり
- MPC と MPPI の比較、Nav2 の MPPI パラメータとの対応、記号の一覧、用語集、参考文献

数値例・図・デモはすべてこの資料のために作ったもので、論文の図は転載していない。

## ファイル

- `index.html`：解説ページ（CSS と JavaScript を含む 1 ファイル）
- `assets/katex/`：数式の表示に使う [KaTeX](https://katex.org/) 0.16.47（MIT License、`assets/katex/LICENSE`）
