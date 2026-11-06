"""演習スクリプト共通のユーティリティ

- 図の保存先 (docs/figures) の管理
- 日本語フォントの自動設定
- 図で使う色 (教材全体で統一。MPC = 青, MPPI = オレンジ)
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = REPO_ROOT / "docs" / "figures"


def fig_path(name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    return FIG_DIR / name


# ---------------------------------------------------------------------------
# 色 (教材全体で統一)
# ---------------------------------------------------------------------------
C_INK = "#1f2733"      # 文字・真値
C_MUTED = "#8a93a3"    # 補助線・障害物
C_MPC = "#2a78d6"      # MPC (勾配を使う方法)
C_MPPI = "#eb6834"     # MPPI (サンプリングを使う方法)
C_OPT = "#6250d6"      # 3 つ目の系列
C_OK = "#1baf7a"       # 4 つ目の系列
C_SHADE = "#eceff3"    # 背景の塗り


def setup_matplotlib():
    """matplotlib を非対話モードにし、日本語フォントを探して設定する。"""
    import matplotlib

    if os.environ.get("MPLBACKEND") is None:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    candidates = [
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "IPAexGothic",
        "IPAPGothic",
        "IPAGothic",
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Yu Gothic",
        "Meiryo",
        "MS Gothic",
        "TakaoGothic",
        "VL Gothic",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    else:
        print(
            "[注意] 日本語フォントが見つかりませんでした。図の日本語が□になる場合は\n"
            "  Ubuntu: sudo apt install fonts-noto-cjk  を実行してください。"
        )
    plt.rcParams.update(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#e3e6eb",
            "grid.linewidth": 0.6,
            "axes.edgecolor": "#9aa3b0",
            "axes.labelcolor": C_INK,
            "xtick.color": "#4a5260",
            "ytick.color": "#4a5260",
            "figure.dpi": 110,
            "savefig.dpi": 130,
            "savefig.bbox": "tight",
            "legend.frameon": False,
            "lines.linewidth": 2.0,
            "axes.unicode_minus": False,
            "mathtext.fontset": "cm",
        }
    )
    return plt
