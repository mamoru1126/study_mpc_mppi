"""解説用の図 (docs/figures/fig_*.svg) を作る

使い方: python tools/make_diagrams.py

演習の結果の図 (ex*.png) は exercises/ が作ります。こちらは概念図だけです。
どの図も白い背景・固定の色なので、ダークモードの HTML 版でもそのまま読めます。
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "figures"

FONT = "'Noto Sans JP','Noto Sans CJK JP','Hiragino Sans','Yu Gothic','Meiryo',sans-serif"
INK, SUB, MUTED, LINE = "#1f2733", "#586273", "#8a93a3", "#c8ced8"
MPC, MPPI, OPT = "#2a78d6", "#eb6834", "#6250d6"
MPC_BG, MPPI_BG, GRAY_BG = "#eaf2fc", "#fdf0e9", "#f4f6f9"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def f(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def text(x, y, s, size=13, fill=INK, weight=400, anchor="start", extra=""):
    w = ' font-weight="700"' if weight == 700 else ""
    return (f'<text x="{f(x)}" y="{f(y)}" font-size="{size}" fill="{fill}"{w} '
            f'text-anchor="{anchor}"{extra}>{esc(s)}</text>')


def text_raw(x, y, raw, size=13, fill=INK, weight=400, anchor="start"):
    """raw は SVG の中身 (tspan を含めてよい)"""
    w = ' font-weight="700"' if weight == 700 else ""
    return f'<text x="{f(x)}" y="{f(y)}" font-size="{size}" fill="{fill}"{w} text-anchor="{anchor}">{raw}</text>'


def u_sub(i, size=10, tail=""):
    """u_i (添字つき)。tail は添字のあとに続ける文字 (基準線を元に戻して書く)"""
    out = f'u<tspan dy="4" font-size="{size}">{i}</tspan>'
    return out + (f'<tspan dy="-4">{esc(tail)}</tspan>' if tail else "")


def sub_markup(s, size=9, d=3):
    """'S_{k} を計算' のような書き方を、添字の tspan に直す (添字のあとの文字は基準線に戻す)"""
    import re

    out, shifted = [], False
    for part in re.split(r"(_\{[^}]*\})", s):
        if not part:
            continue
        if part.startswith("_{"):
            out.append(f'<tspan dy="{d}" font-size="{size}">{esc(part[2:-1])}</tspan>')
            shifted = True
        elif shifted:
            out.append(f'<tspan dy="-{d}">{esc(part)}</tspan>')
            shifted = False
        else:
            out.append(esc(part))
    return "".join(out)


def rect(x, y, w, h, fill="#ffffff", stroke=LINE, sw=1.2, rx=10, extra=""):
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{extra}/>')


def line(x1, y1, x2, y2, color=MUTED, sw=1.6, arrow=None, dash=None):
    m = f' marker-end="url(#ah-{arrow})"' if arrow else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{color}" '
            f'stroke-width="{sw}"{d}{m}/>')


def path(d, color=MUTED, sw=1.6, arrow=None, dash=None, fill="none", extra=""):
    m = f' marker-end="url(#ah-{arrow})"' if arrow else ""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}"{da}{m}{extra}/>'


def circle(cx, cy, r, fill=INK, stroke="none", sw=1.5, extra=""):
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>'


def defs():
    out = ["<defs>"]
    for name, col in (("ink", INK), ("muted", MUTED), ("mpc", MPC), ("mppi", MPPI), ("opt", OPT)):
        out.append(f'<marker id="ah-{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                   f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
    out.append("</defs>")
    return "\n".join(out)


def svg(name, w, h, body, title):
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
         f'font-family="{FONT}" role="img" aria-label="{esc(title)}">\n<title>{esc(title)}</title>\n{defs()}\n'
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>\n' + "\n".join(body) + "\n</svg>\n")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(s, encoding="utf-8")
    print("wrote", OUT / name)


# ---------------------------------------------------------------------------
# 全体像
# ---------------------------------------------------------------------------
def fig_overview():
    b = []
    b.append(rect(150, 16, 540, 96, fill=GRAY_BG))
    b.append(text(420, 44, "共通の問題：有限ホライズン最適制御問題", 16, weight=700, anchor="middle"))
    b.append(text(420, 70, "今の状態から N ステップ先までの入力列を選び、コストの合計を最小にする", 13, SUB, anchor="middle"))
    b.append(text(420, 94, "コスト = 目標からのずれ ＋ 入力の大きさ ＋ 障害物への近さ", 12.5, SUB, anchor="middle"))
    b.append(line(330, 114, 232, 150, MPC, 1.8, "mpc"))
    b.append(line(510, 114, 608, 150, MPPI, 1.8, "mppi"))
    b.append(text(250, 128, "微分して解く", 12.5, MPC, anchor="end"))
    b.append(text(590, 128, "試して解く", 12.5, MPPI))
    # MPC
    b.append(rect(24, 152, 380, 200, fill=MPC_BG, stroke=MPC, sw=1.5, rx=12))
    b.append(text(44, 184, "MPC（勾配を使う）", 16, MPC, 700))
    b.append(path("M 300 170 Q 342 236 384 170", INK, 1.4))

    def para(t):  # 上の 2 次ベジェ曲線の点と傾き
        return 300 + 84 * t, 170 + 132 * t * (1 - t), 132 * (1 - 2 * t) / 84

    x1, y1, k1 = para(0.07)
    b.append(line(x1 - 9, y1 - 9 * k1, x1 + 20, y1 + 20 * k1, MPC, 1.3))
    for t in (0.07, 0.27, 0.43):
        x, y, _ = para(t)
        b.append(circle(x, y, 3.6, MPC))
    b.append(text(44, 218, "傾き（微分）を計算して、コストが下がる", 13))
    b.append(text(44, 240, "向きへ入力列を直す。これを数回くり返す", 13))
    b.append(text(44, 266, "道具：ガウス・ニュートン法・SQP（02〜04 章）", 12.5, SUB))
    b.append(text(44, 296, "◎ 少ない計算で正確に求まる。制約を守れる", 13))
    b.append(text(44, 322, "× 微分できないコストと局所解に弱い", 13))
    # MPPI
    b.append(rect(436, 152, 380, 200, fill=MPPI_BG, stroke=MPPI, sw=1.5, rx=12))
    b.append(text(456, 184, "MPPI（サンプリングを使う）", 16, MPPI, 700))
    for i, ye in enumerate((166, 177, 188, 199, 210)):
        b.append(path(f"M 716 188 Q 756 188 800 {ye}", MPPI, 1.2 + (1.2 if i == 2 else 0), extra=f' opacity="{0.45 + 0.55 * (i == 2)}"'))
    b.append(circle(716, 188, 4, INK))
    b.append(text(456, 218, "ゆらぎを足した入力列を K 本試し、コストが", 13))
    b.append(text(456, 240, "低いものほど重くして平均する", 13))
    b.append(text(456, 266, "道具：重み ∝ exp(−コスト / λ)（05・06 章）", 12.5, SUB))
    b.append(text(456, 296, "◎ 微分がいらない。どんなコストでも使える", 13))
    b.append(text(456, 322, "× たくさん試す必要がある。出力がガタつく", 13))
    # 共通の後半
    b.append(line(214, 352, 296, 392, MUTED, 1.6, "muted"))
    b.append(line(626, 352, 544, 392, MUTED, 1.6, "muted"))
    b.append(rect(150, 394, 540, 72, fill=GRAY_BG))
    b.append(text(420, 424, "最初の 1 手だけ実行し、状態を測り直して、また解く", 14.5, weight=700, anchor="middle"))
    b.append(text(420, 450, "receding horizon。前回の答えを 1 ステップずらして出発点にする", 12.5, SUB, anchor="middle"))
    b.append(path("M 690 430 H 826 V 64 H 692", MUTED, 1.6, "muted"))
    b.append(text(758, 422, "毎周期くり返す", 12, SUB, anchor="middle"))
    svg("fig_overview.svg", 840, 480, b, "MPC と MPPI の全体像。同じ最適制御問題を、MPC は微分で、MPPI はサンプリングで解き、最初の 1 手だけ実行して毎周期くり返す")


# ---------------------------------------------------------------------------
# 知識の地図
# ---------------------------------------------------------------------------
def fig_knowledge_map():
    b = []
    L, R, W, H = 150, 510, 320, 64

    def box(x, y, title, sub, color, bg="#ffffff", dash=None, w=W):
        out = [rect(x, y, w, H, fill=bg, stroke=LINE, sw=1.2, rx=9, extra=f' stroke-dasharray="{dash}"' if dash else "")]
        if color:
            out.append(f'<rect x="{x}" y="{y + 8}" width="5" height="{H - 16}" rx="2.5" fill="{color}"/>')
        out.append(text(x + 18, y + 27, title, 14, INK, 700))
        out.append(text(x + 18, y + 49, sub, 12, SUB))
        return out

    rows = [(24, "STEP 1", "共通の土台"), (140, "STEP 2", "道具"), (256, "STEP 3", "2 つの解き方"), (488, "STEP 4", "比べて使う")]
    for y, s1, s2 in rows:
        b.append(text(16, y + 26, s1, 12, MUTED, 700))
        b.append(text(16, y + 46, s2, 12, SUB))
    b.append(line(132, 18, 132, 556, "#e6e9ef", 1))
    b += box(330, 24, "01 最適制御と receding horizon", "モデル・コスト・ホライズン、毎周期解き直す", OPT)
    b += box(680, 30, "09 用語集", "いつでも辞書として", None, GRAY_BG, "4 3", w=150)
    b += box(L, 140, "02 最小二乗とガウス・ニュートン法", "残差・ヤコビアン・LM 法", MPC)
    b += box(L, 256, "03 線形 MPC", "コストを 2 次関数に直す・QP", MPC)
    b += box(R, 256, "05 MPPI の考え方", "サンプル・重み・λ の意味", MPPI)
    b += box(L, 372, "04 非線形 MPC", "ガウス・ニュートン・SQP・RTI・局所解", MPC)
    b += box(R, 372, "06 MPPI の理論", "理想の分布・重点サンプリング・勾配", MPPI)
    b += box(L, 488, "07 MPC と MPPI の比較", "得意・苦手、同じ場面でのデモ", OPT)
    b += box(R, 488, "08 Nav2 の MPPI", "パラメータと式の対応", MPPI)
    b.append(line(420, 88, 330, 138, MUTED, 1.6, "muted"))
    b.append(line(580, 88, 668, 254, MUTED, 1.6, "muted"))
    b.append(line(310, 204, 310, 254, MUTED, 1.6, "muted"))
    b.append(line(310, 320, 310, 370, MUTED, 1.6, "muted"))
    b.append(line(670, 320, 670, 370, MUTED, 1.6, "muted"))
    b.append(path("M 470 172 H 490 V 404 H 508", OPT, 1.4, "opt", "5 4"))
    b.append(line(310, 436, 310, 486, MUTED, 1.6, "muted"))
    b.append(line(600, 436, 452, 486, MUTED, 1.6, "muted"))
    b.append(line(470, 520, 508, 520, MUTED, 1.6, "muted"))
    # 凡例
    y = 582
    b.append(f'<rect x="150" y="{y - 10}" width="12" height="12" rx="2" fill="{MPC}"/>')
    b.append(text(168, y, "MPC（勾配を使う）", 12, SUB))
    b.append(f'<rect x="300" y="{y - 10}" width="12" height="12" rx="2" fill="{MPPI}"/>')
    b.append(text(318, y, "MPPI（サンプリング）", 12, SUB))
    b.append(f'<rect x="462" y="{y - 10}" width="12" height="12" rx="2" fill="{OPT}"/>')
    b.append(text(480, y, "両方に共通", 12, SUB))
    b.append(line(570, y - 4, 600, y - 4, OPT, 1.4, None, "5 4"))
    b.append(text(606, y, "06 章で 02 章の LM 法と同じ形が出てくる", 12, SUB))
    svg("fig_knowledge_map.svg", 840, 600, b, "知識の地図。01 章が土台で、MPC の列 (02, 03, 04) と MPPI の列 (05, 06) に分かれ、07 章の比較と 08 章の Nav2 で合流する")


# ---------------------------------------------------------------------------
# receding horizon
# ---------------------------------------------------------------------------
def fig_receding_horizon():
    b = []
    BW, BH, STEP = 58, 34, 66

    def bx(k):
        return 150 + STEP * k

    b.append(path(f"M {bx(0)} 50 V 44 H {bx(5) + BW} V 50", INK, 1.2))
    b.append(text((bx(0) + bx(5) + BW) / 2, 36, "ホライズン：N ステップ先まで計画する（図は N = 6）", 12.5, INK, anchor="middle"))
    for r in range(3):
        cy = 76 + 68 * r
        b.append(text(20, cy - 2, f"周期 {r}", 13, INK, 700))
        b.append(text(20, cy + 16, f"(時刻 t{'+' + str(r) if r else ''} で解く)", 11, SUB))
        for i in range(6):
            k = r + i
            x = bx(k)
            if i == 0:
                b.append(rect(x, cy - BH / 2, BW, BH, fill=MPC, stroke=MPC, rx=6))
                b.append(text_raw(x + BW / 2, cy + 4, u_sub(i), 15, "#ffffff", 700, "middle"))
                b.append(text(x + BW / 2, cy + 32, "実行", 11, MPC, 700, "middle"))
            else:
                last_new = r > 0 and i == 5
                b.append(rect(x, cy - BH / 2, BW, BH, fill=MPC_BG, stroke=MPC, sw=1.2, rx=6,
                              extra=' stroke-dasharray="4 3"' if last_new else ""))
                b.append(text_raw(x + BW / 2, cy + 4, u_sub(i), 15, MPC, 400, "middle"))
                if r < 2:
                    b.append(line(x + BW / 2, cy + BH / 2 + 2, x + BW / 2, cy + 68 - BH / 2 - 3, MUTED, 1.2, "muted"))
    nx = 712
    b.append(f'<rect x="{nx}" y="62" width="14" height="14" rx="3" fill="{MPC}"/>')
    b.append(text(nx + 22, 74, "濃い箱（最初の 1 手）だけ", 12.5))
    b.append(text(nx + 22, 94, "実行する", 12.5))
    b.append(line(nx + 7, 112, nx + 7, 136, MUTED, 1.2, "muted"))
    b.append(text(nx + 22, 124, "残りは 1 つずらして", 12.5))
    b.append(text(nx + 22, 144, "次の周期の出発点に", 12.5))
    b.append(text(nx + 22, 164, "（ウォームスタート）", 12.5, SUB))
    b.append(f'<rect x="{nx}" y="196" width="14" height="14" rx="3" fill="{MPC_BG}" stroke="{MPC}" stroke-dasharray="3 2"/>')
    b.append(text(nx + 22, 208, "点線の箱：ずらして空いた", 12.5))
    b.append(text(nx + 22, 228, "最後の 1 ステップ（前の値", 12.5))
    b.append(text(nx + 22, 248, "をコピーして埋める）", 12.5))
    cy = 290
    b.append(text_raw(20, cy - 26, "実際に実行される入力 = 各周期の " + u_sub(0, tail=" をつないだもの"), 12.5, INK, 700))
    for k in range(3):
        b.append(rect(bx(k), cy - BH / 2, BW, BH, fill=MPC, stroke=MPC, rx=6))
        b.append(text(bx(k) + BW / 2, cy + 5, f"周期 {k}", 12, "#ffffff", 700, "middle"))
    b.append(text(bx(3) + 12, cy + 5, "…", 16, MPC, 700))
    b.append(line(150, 324, 690, 324, LINE, 1.2))
    for k in range(8):
        x = bx(k) + BW / 2
        b.append(line(x, 320, x, 328, LINE, 1.2))
        b.append(text(x, 344, "t" if k == 0 else f"t+{k}", 11.5, SUB, anchor="middle"))
    b.append(text(698, 328, "時刻", 11.5, SUB))
    svg("fig_receding_horizon.svg", 900, 354, b, "receding horizon。毎周期 N ステップ先まで入力列を計画し、最初の 1 手だけ実行して、残りを 1 つずらして次の周期の出発点にする")


# ---------------------------------------------------------------------------
# ニュートン法 (接線で 0 を探す)
# ---------------------------------------------------------------------------
def fig_newton_tangent():
    def gx(z):
        return 44 + (z - 1.0) / 1.3 * 336

    def gy(r):
        return 172 - r * 40

    b = []
    b.append(line(44, gy(0), 386, gy(0), INK, 1.2))
    b.append(text(392, gy(0) + 4, "z", 13, INK, extra=' font-style="italic"'))
    zs = [1.33 + 0.97 * i / 200 for i in range(201)]
    pts = " ".join(f"{f(gx(z))},{f(gy(z * z - 2))}" for z in zs)
    b.append(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="2"/>')
    z0 = 2.0
    z1 = z0 - (z0**2 - 2) / (2 * z0)
    z2 = z1 - (z1**2 - 2) / (2 * z1)
    for za, zb in ((z0, z1), (z1, z2)):
        ra = za * za - 2
        zc = zb - 0.06
        b.append(line(gx(za + 0.05), gy(ra + 2 * za * 0.05), gx(zc), gy(ra + 2 * za * (zc - za)), MPC, 1.8))
        b.append(line(gx(zb), gy(0), gx(zb), gy(zb * zb - 2), MUTED, 1, None, "3 3"))
    for z in (z0, z1):
        b.append(circle(gx(z), gy(z * z - 2), 5, MPC))
    for z in (z0, z1, z2):
        b.append(circle(gx(z), gy(0), 4, "#ffffff", MPC, 1.6))
    def zsub(i, tail):
        return f'z<tspan dy="4" font-size="10">{i}</tspan><tspan dy="-4">{esc(tail)}</tspan>'

    b.append(text_raw(gx(z0), gy(0) + 24, zsub(0, " = 2"), 12.5, INK, anchor="middle"))
    b.append(text_raw(gx(z1) + 4, gy(0) + 24, zsub(1, " = 1.5"), 12.5, INK))
    b.append(text_raw(gx(z2) - 6, gy(0) + 24, zsub(2, " = 1.417"), 12.5, INK, anchor="end"))
    b.append(text(gx(math.sqrt(2)) - 4, gy(0) - 10, "答え √2", 11.5, SUB, anchor="end"))
    b.append(text_raw(250, 30, 'r(z) = z<tspan dy="-6" font-size="10">2</tspan><tspan dy="6"> − 2</tspan>', 13, INK))
    b.append(text(262, 128, "接線", 13, MPC, 700))
    b.append(text(22, 226, "今の点で接線を引き、接線が 0 になる所へ移る。これをくり返す", 12, SUB))
    svg("fig_newton_tangent.svg", 420, 238, b, "ニュートン法。r(z) = z² − 2 の z₀ = 2 で接線を引くと z₁ = 1.5、そこで引くと z₂ = 1.417 になり、√2 に近づく")


# ---------------------------------------------------------------------------
# single shooting と multiple shooting
# ---------------------------------------------------------------------------
def fig_shooting():
    b = []
    b.append(text(104, 22, "single shooting", 14, INK, 700, "middle"))
    b.append(text(304, 22, "multiple shooting", 14, INK, 700, "middle"))
    b.append(line(18, 164, 192, 164, LINE, 1.2))
    b.append(line(210, 164, 396, 164, LINE, 1.2))
    b.append(text(192, 178, "時刻 →", 11, SUB, anchor="end"))
    b.append(text(396, 178, "時刻 →", 11, SUB, anchor="end"))

    def state(t):  # single shooting の軌道 (なめらかな曲線)
        return 132 - 78 * (0.5 - 0.5 * math.cos(math.pi * t)) ** 1.1

    pts = " ".join(f"{f(24 + 160 * i / 80)},{f(state(i / 80))}" for i in range(81))
    b.append(f'<polyline points="{pts}" fill="none" stroke="{MPC}" stroke-width="2.2"/>')
    b.append(circle(24, state(0), 5, INK))
    for k in range(1, 5):
        b.append(circle(24 + 40 * k, state(k / 4), 4, "#ffffff", MUTED, 1.6))
    # multiple shooting: 区間ごとに始点 (変数) から伸びる線。終わりと次の始点がずれている
    starts = [(214, 132), (257, 114), (300, 84), (343, 78), (386, 66)]
    ends = [(257, 126), (300, 73), (343, 90), (386, 58)]
    ctrl = [(236, 112), (279, 80), (321, 74), (365, 62)]
    for (x0, y0), (cx, cy), (x1, y1) in zip(starts, ctrl, ends):
        b.append(path(f"M {x0} {y0} Q {cx} {cy} {x1} {y1}", MPC, 2.2))
        nx_, ny_ = next(s for s in starts if s[0] == x1)
        b.append(line(x1, y1, nx_, ny_, MPPI, 2.2, None, "3 2"))
    for (x, y) in starts:
        b.append(circle(x, y, 5, INK))
    b.append(text(262, 135, "ずれ", 11.5, MPPI, 700))
    b.append(text(104, 200, "変数：入力だけ", 12.5, INK, anchor="middle"))
    b.append(text(104, 218, "状態は順に計算する", 12.5, SUB, anchor="middle"))
    b.append(text(304, 200, "変数：入力と、区間の始点の状態", 12, INK, anchor="middle"))
    b.append(text(304, 218, "ずれ = 0 を制約にする", 12.5, SUB, anchor="middle"))
    svg("fig_shooting.svg", 410, 230, b, "single shooting では入力だけが変数で、状態は順に計算した 1 本の軌道になる。multiple shooting では区間の始点の状態も変数で、つなぎ目のずれを 0 にすることを制約にする")


# ---------------------------------------------------------------------------
# MPPI の 1 周期
# ---------------------------------------------------------------------------
def fig_mppi_loop():
    b = []
    ends = [72, 96, 120, 146, 166, 184, 200]
    S = [42, 31, 9, 6, 8, 14, 23]
    lam = 3.0
    e = [math.exp(-(s - min(S)) / lam) for s in S]
    w = [v / sum(e) for v in e]
    wmax = max(w)
    titles = [("① 試す", sub_markup("ゆらぎを足した K 本をロールアウト")),
              ("② 評価する", sub_markup("それぞれのコスト S_{k} を計算")),
              ("③ 重みをつける", sub_markup("w_{k} ∝ exp(−(S_{k} − S_{min}) / λ)")),
              ("④ 平均する", sub_markup("重みつき平均で案を更新"))]

    def curve(X0, yend):
        return f"M {X0 + 22} 146 Q {X0 + 92} 146 {X0 + 160} {yend}"

    def y_at(X0, yend, xq):
        # 2 次ベジェ曲線の x(t) = xq を二分法で解いて y を返す
        lo, hi = 0.0, 1.0
        for _ in range(40):
            t = (lo + hi) / 2
            x = (1 - t) ** 2 * (X0 + 22) + 2 * (1 - t) * t * (X0 + 92) + t * t * (X0 + 160)
            lo, hi = (t, hi) if x < xq else (lo, t)
        return 146 + t * t * (yend - 146)

    for p, (t1, t2) in enumerate(titles):
        X0 = 12 + 212 * p
        b.append(rect(X0, 50, 200, 186, fill="#fafbfc", stroke=LINE, rx=10))
        b.append(text(X0 + 100, 24, t1, 14, INK, 700, "middle"))
        b.append(text_raw(X0 + 100, 42, t2, 11.5, SUB, anchor="middle"))
        if p == 2:  # 重みの棒グラフ
            base = 210
            for k in range(7):
                x = X0 + 22 + 24 * k
                h = 132 * w[k] / wmax
                op = 0.25 + 0.75 * w[k] / wmax
                b.append(f'<rect x="{x}" y="{f(base - h)}" width="16" height="{f(max(h, 1.2))}" fill="{MPPI}" opacity="{op:.2f}"/>')
                b.append(text(x + 8, base + 16, str(S[k]), 11, SUB, anchor="middle"))
            b.append(line(X0 + 16, base, X0 + 188, base, INK, 1))
            b.append(text(X0 + 18, 70, "重み", 11, SUB))
            b.append(text(X0 + 186, 70, "S が小さいほど重い", 11, MPPI, anchor="end"))
            continue
        # 障害物 (上の 2 本の通り道に置く)
        ox = X0 + 118
        oy = (y_at(X0, ends[0], ox) + y_at(X0, ends[1], ox)) / 2
        b.append(circle(ox, oy, 15, "#c3c9d3"))
        for k, ye in enumerate(ends):
            if p == 0:
                b.append(path(curve(X0, ye), MUTED, 1.3))
            elif p == 1:
                good = (max(S) - S[k]) / (max(S) - min(S))
                col = MPPI if S[k] <= 14 else MUTED
                b.append(path(curve(X0, ye), col, 1.0 + 1.4 * good, extra=f' opacity="{0.4 + 0.6 * good:.2f}"'))
                b.append(text(X0 + 166, ye + 4, str(S[k]), 11, MPPI if S[k] <= 14 else SUB, 700 if S[k] == min(S) else 400))
            else:
                b.append(path(curve(X0, ye), MPPI, 1.0, extra=f' opacity="{0.15 + 0.6 * w[k] / wmax:.2f}"'))
        if p == 3:
            yavg = sum(wk * ye for wk, ye in zip(w, ends))
            b.append(path(curve(X0, yavg), INK, 3))
            b.append(text(X0 + 100, 226, "太線：新しい案", 11.5, INK, 700, "middle"))
        if p == 0:
            b.append(line(X0 + 22, 146, X0 + 168, 146, INK, 1.8, None, "5 4"))
            b.append(text(X0 + 100, 226, "点線：今の案（ゆらぎなし）", 11.5, SUB, anchor="middle"))
        if p == 1:
            b.append(text(X0 + 100, 226, "障害物を通るとコストが大きい", 11.5, SUB, anchor="middle"))
        b.append(circle(X0 + 22, 146, 5, INK))
    for p in range(3):
        x = 12 + 212 * p + 200
        b.append(line(x + 1, 143, x + 11, 143, MUTED, 1.4, "muted"))
    b.append(text(430, 266, "→ 最初の 1 手だけ実行し、案を 1 つずらして次の周期へ（01 章と同じ）", 13, INK, anchor="middle"))
    svg("fig_mppi_loop.svg", 860, 282, b, "MPPI の 1 周期。ゆらぎを足した入力列を試し、コストを計算し、コストが低いものほど重くして平均し、最初の 1 手を実行する")


# ---------------------------------------------------------------------------
# Nav2 の MPPI の 1 周期とパラメータ
# ---------------------------------------------------------------------------
def fig_nav2_mppi():
    b = []
    W, H = 194, 88
    MONO = "'IBM Plex Mono','SFMono-Regular',Menlo,Consolas,monospace"

    def box(x, y, title, line2, params):
        out = [rect(x, y, W, H, fill="#ffffff", stroke=LINE, rx=10)]
        out.append(text(x + 14, y + 26, title, 14, INK, 700))
        out.append(text(x + 14, y + 50, line2, 12.5, SUB))
        out.append(f'<text x="{x + 14}" y="{y + 74}" font-size="12" fill="{MPPI}" font-family="{MONO}">{esc(params)}</text>')
        return out

    xs = [16, 226, 436, 646]
    y1, y2 = 30, 168
    b += box(xs[0], y1, "① ずらす", "前回の制御列を 1 つずらす", "model_dt")
    b += box(xs[1], y1, "② ゆらぎを足す", "batch_size 本の候補", "vx_std, wz_std")
    b += box(xs[2], y1, "③ ロールアウト", "モデルで軌道を予測", "time_steps, motion_model")
    b += box(xs[3], y1, "④ コストを計算", "critic の値を足し合わせる", "critics, cost_weight")
    b += box(xs[3], y2, "⑤ 重みつき平均", "低コストの候補ほど重く平均", "temperature, gamma")
    b += box(xs[2], y2, "⑥ 平滑化", "制御列をなめらかにする", "Savitzky–Golay")
    b += box(xs[1], y2, "⑦ 指令を送る", "最初の速度指令を出す", "cmd_vel")
    for i in range(3):
        b.append(line(xs[i] + W + 2, y1 + H / 2, xs[i + 1] - 3, y1 + H / 2, MUTED, 1.6, "muted"))
    b.append(line(xs[3] + W / 2, y1 + H + 2, xs[3] + W / 2, y2 - 3, MUTED, 1.6, "muted"))
    for i in (3, 2):
        b.append(line(xs[i] - 2, y2 + H / 2, xs[i - 1] + W + 3, y2 + H / 2, MUTED, 1.6, "muted"))
    b.append(path(f"M {xs[1] - 2} {y2 + H / 2} H 112 V {y1 + H + 3}", MUTED, 1.6, "muted"))
    b.append(text(122, (y1 + H + y2) / 2 + 4, "次の周期へ (model_dt 秒ごと)", 11.5, SUB))
    b.append(text(xs[3] + W / 2 - 10, (y1 + H + y2) / 2 + 4, "②〜⑤ を iteration_count 回 (既定 1 回)", 11.5, SUB, anchor="end"))
    svg("fig_nav2_mppi.svg", 856, 272, b, "Nav2 の MPPI の 1 周期。前回の制御列をずらし、ゆらぎを足した候補を batch_size 本作り、ロールアウトして critic でコストを計算し、temperature で重みをつけて平均し、平滑化して、最初の速度指令を送る")


if __name__ == "__main__":
    fig_overview()
    fig_knowledge_map()
    fig_receding_horizon()
    fig_newton_tangent()
    fig_shooting()
    fig_mppi_loop()
    fig_nav2_mppi()
