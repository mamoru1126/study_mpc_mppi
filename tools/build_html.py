"""docs/*.md から HTML 版 (html/) を生成する

使い方:
    pip install markdown pymdown-extensions
    python tools/build_html.py

- Markdown の数式 ($...$, ```math) は KaTeX で表示します (tools/site/katex に同梱。オフラインでも表示できます)
- <!-- demo:NAME --> の位置にインタラクティブデモを埋め込みます (tools/site/demos.js)
  <!-- demo:NAME:MODE --> とすると、最初に選ばれているモードを指定できます
- 図 (docs/figures) と共通アセット (tools/site) を html/ にコピーします
"""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

import markdown
from pymdownx import arithmatex, slugs

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "html"
SITE = Path(__file__).resolve().parent / "site"

SITE_NAME = "MPC × MPPI 学習ノート"
REPO_URL = "https://github.com/mamoru1126/study_mpc_mppi"
NAV2_URL = "https://docs.nav2.org/configuration/packages/configuring-mppic.html"
PAPER_URL = "https://homes.cs.washington.edu/~bboots/files/InformationTheoreticMPC.pdf"

# (ファイル名の stem, 短いタイトル, 要約, タグ, 目安時間)
CHAPTERS = [
    ("00_roadmap", "学習ロードマップ", "MPC と MPPI をひとことで。共通の問題と、必要な知識の地図。", [], "15 分"),
    ("01_optimal_control", "最適制御問題と receding horizon", "モデル・コスト・ホライズン。最初の 1 手だけ実行して、毎周期解き直す理由。", ["mpc", "mppi"], "1 時間"),
    ("02_least_squares_gauss_newton", "最小二乗とガウス・ニュートン法", "残差とヤコビアン、接線で 0 を探すニュートン法、ガウス・ニュートン法、LM 法。", ["math", "opt"], "2 時間"),
    ("03_linear_mpc", "線形 MPC", "未来の状態を入力の列の 1 次式に。コストを 2 次関数に直して解く。制約と QP。", ["mpc"], "1.5 時間"),
    ("04_nonlinear_mpc", "非線形 MPC", "連鎖律でヤコビアン。shooting、SQP、RTI。局所解と、微分できないコスト。", ["mpc", "opt"], "2 時間"),
    ("05_mppi_basics", "MPPI の考え方", "試す・評価する・重みをつける・平均する。λ と実効サンプル数。", ["mppi"], "1.5 時間"),
    ("06_mppi_theory", "MPPI の理論", "理想の分布、重点サンプリング、ぼかしたコストの坂。LM 法との対応。", ["mppi", "math"], "2 時間"),
    ("07_comparison", "MPC と MPPI の比較", "式とアルゴリズムの対応、得意・苦手。同じ場面を両方で解くデモ。", ["mpc", "mppi"], "1 時間"),
    ("08_nav2_mppi", "Nav2 の MPPI", "パラメータと式の対応、critic、調整の考え方。", ["mppi", "nav2"], "1 時間"),
    ("09_glossary", "用語集", "日本語と英語の対応、ひとことでの説明。", [], "辞書として"),
]
TAG_LABEL = {
    "mpc": ("mpc", "MPC"),
    "mppi": ("mppi", "MPPI"),
    "opt": ("opt", "最適化"),
    "math": ("math", "数学"),
    "nav2": ("nav2", "Nav2"),
}

MATH = """<link rel="stylesheet" href="assets/katex/katex.css">
<script defer src="assets/katex/katex.min.js"></script>
<script defer src="assets/katex/auto-render.min.js"></script>"""

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700'
    '&family=IBM+Plex+Mono:wght@400;500&family=Zen+Kaku+Gothic+New:wght@500;700&display=swap">'
)

BRAND_MARK = (
    '<svg class="brand-mark" viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M5 12 Q 12 12 20 4" fill="none" stroke="var(--mppi)" stroke-width="1.6" stroke-linecap="round" opacity=".5"/>'
    '<path d="M5 12 Q 12 12 20 20" fill="none" stroke="var(--mppi)" stroke-width="1.6" stroke-linecap="round" opacity=".5"/>'
    '<path d="M5 12 H 20" fill="none" stroke="var(--mpc)" stroke-width="2.4" stroke-linecap="round"/>'
    '<circle cx="5" cy="12" r="3" fill="var(--ink)"/>'
    "</svg>"
)


def md_converter():
    return markdown.Markdown(
        extensions=[
            "tables",
            "md_in_html",
            "attr_list",
            "sane_lists",
            "toc",
            "pymdownx.arithmatex",
            "pymdownx.superfences",
            "pymdownx.tasklist",
        ],
        extension_configs={
            "toc": {"slugify": slugs.slugify(case="lower"), "permalink": False},
            "pymdownx.arithmatex": {"generic": True},
            "pymdownx.superfences": {
                "custom_fences": [
                    {"name": "math", "class": "arithmatex", "format": arithmatex.arithmatex_fenced_format(which="generic")}
                ]
            },
            "pymdownx.tasklist": {"custom_checkbox": False},
        },
    )


CJK_END = re.compile(r"[\u3000-\u303f\u3040-\u30ff\u4e00-\u9fff\uff00-\uffef]$")
BLOCK_START = re.compile(r"\s|[-*+] |\d+\. |\||>|#|<|```|\$\$")


def join_cjk_lines(text: str) -> str:
    """段落の途中の改行のうち、日本語の文字で終わる行のものをつなぐ

    HTML では段落内の改行が空白として表示され、「。 次の文」のように日本語の文の間にすき間ができるため。
    コードブロック・数式ブロック・表・リスト・見出し・HTML の行はそのままにする。
    """
    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or not out or not line:
            out.append(line)
            continue
        prev = out[-1]
        if prev.startswith("> ") and line.startswith("> "):
            if CJK_END.search(prev) and not BLOCK_START.match(line[2:]):
                out[-1] = prev + line[2:]
                continue
        elif prev and not BLOCK_START.match(prev) and CJK_END.search(prev) and not BLOCK_START.match(line):
            out[-1] = prev + line
            continue
        out.append(line)
    return "\n".join(out)


def preprocess(text: str) -> str:
    # 末尾の「前へ / 次へ」ナビゲーションはテンプレート側で作るので取り除く
    idx = text.rfind("\n---\n")
    if idx >= 0 and re.search(r"(前へ|次へ|目次)", text[idx:]):
        text = text[:idx] + "\n"
    # GitHub で読む人向けの「HTML 版では…」の注記は、HTML では不要
    text = re.sub(r"^> \*\*HTML 版\*\*.*\n(?:>.*\n)*", "", text, flags=re.M)
    # デモの埋め込み位置
    text = re.sub(r"<!-- demo:(\w+):(\w+) -->", r'<div data-demo="\1" data-mode="\2"></div>', text)
    text = re.sub(r"<!-- demo:(\w+) -->", r'<div data-demo="\1"></div>', text)
    # リンクの書き換え
    text = re.sub(r"\]\((\d\d_[\w]+)\.md(#[^)]*)?\)", lambda m: f"]({m.group(1)}.html{m.group(2) or ''})", text)
    text = text.replace("](../README.md)", "](index.html)")
    text = re.sub(r"\]\(\.\./exercises/[^)]*\)", lambda m: m.group(0).replace("../", REPO_URL + "/blob/master/"), text)
    return join_cjk_lines(text)


def chips(tags, time_label=None):
    out = []
    for t in tags:
        cls, label = TAG_LABEL[t]
        out.append(f'<span class="chip {cls}">{label}</span>')
    if time_label:
        out.append(f'<span class="chip time">目安 {html.escape(time_label)}</span>')
    return "".join(out)


def rail(current: str | None) -> str:
    items = []
    for stem, title, _, _, _ in CHAPTERS:
        num = stem[:2]
        cur = ' aria-current="page"' if stem == current else ""
        items.append(
            f'<li><a href="{stem}.html"{cur}><span class="num">{num}</span><span>{html.escape(title)}</span>'
            f'<span class="done" data-done-slug="{stem}" title="読了"></span></a></li>'
        )
    home_cur = ' aria-current="page"' if current is None else ""
    return (
        '<nav class="rail" aria-label="章の一覧">'
        '<h2>目次</h2>'
        f'<ul class="toc"><li><a href="index.html"{home_cur}>'
        '<span class="num">◆</span><span>はじめに</span><span></span></a></li>' + "".join(items) + "</ul>"
        '<h2>リンク</h2>'
        f'<p class="rail-note"><a href="{REPO_URL}" target="_blank" rel="noopener">このリポジトリ</a><br>'
        f'<a href="{NAV2_URL}" target="_blank" rel="noopener">Nav2 の MPPI の設定ガイド</a><br>'
        f'<a href="{PAPER_URL}" target="_blank" rel="noopener">MPPI の論文 (Williams et al. 2017)</a></p>'
        '<p class="rail-note">各章の最後で「この章を読んだ」にチェックすると、ここに印が付きます (このブラウザにだけ保存)。</p>'
        "</nav>"
    )


def page(title: str, body: str, current: str | None) -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
{FONTS}
<link rel="stylesheet" href="assets/style.css">
{MATH}
</head>
<body>
<header class="topbar">
  <a class="brand" href="index.html">{BRAND_MARK}<span>{SITE_NAME}</span></a>
  <button class="menu-btn" type="button" aria-expanded="false" aria-label="目次を開く">目次</button>
</header>
<div class="layout">
{rail(current)}
<main>
{body}
</main>
</div>
<script src="assets/app.js"></script>
<script src="assets/ctrl.js"></script>
<script src="assets/demos.js"></script>
</body>
</html>
"""


def build_chapter(i: int):
    stem, title, summary, tags, time_label = CHAPTERS[i]
    text = (DOCS / f"{stem}.md").read_text(encoding="utf-8")
    md = md_converter()
    content = md.convert(preprocess(text))
    if i > 0:
        p = CHAPTERS[i - 1]
        prev_link = f'<a class="prev" href="{p[0]}.html"><small>前へ</small>{p[0][:2]} {html.escape(p[1])}</a>'
    else:
        prev_link = '<a class="prev" href="index.html"><small>前へ</small>はじめに</a>'
    next_link = ""
    if i < len(CHAPTERS) - 1:
        n = CHAPTERS[i + 1]
        next_link = f'<a class="next" href="{n[0]}.html"><small>次へ</small>{n[0][:2]} {html.escape(n[1])}</a>'
    body = f"""<article class="article">
<div class="chapter-meta"><span class="chip time">第 {stem[:2]} 章</span>{chips(tags, time_label)}</div>
{content}
<label class="read-toggle"><input type="checkbox" id="read-toggle" data-slug="{stem}"> この章を読んだ</label>
<nav class="pager" aria-label="前後の章">{prev_link}{next_link}</nav>
</article>"""
    out = page(f"{title} | {SITE_NAME}", body, stem)
    (OUT / f"{stem}.html").write_text(out, encoding="utf-8")


def build_index():
    cards = []
    for stem, title, summary, tags, time_label in CHAPTERS:
        cards.append(
            f'<a class="card" href="{stem}.html"><span class="n"><span>CHAPTER {stem[:2]}</span>'
            f'<span class="done-badge" data-done-badge="{stem}" hidden>読了</span></span>'
            f'<span class="ttl">{html.escape(title)}</span><span class="sum">{html.escape(summary)}</span>'
            f'<span class="chips">{chips(tags, time_label)}</span></a>'
        )
    body = f"""<div class="article" style="max-width:none">
<section class="hero">
  <div>
    <div class="eyebrow">モデル予測制御を数式から理解する学習ノート</div>
    <h1>MPC と MPPI は、同じ問題の 2 つの解き方</h1>
    <p>どちらも「少し先までの動きを予測し、コストがいちばん小さい入力の列を選び、最初の 1 手だけ実行する」をくり返します。違うのは、いちばん良い入力の列の探し方だけです。MPC は微分を使って直し、MPPI はたくさん試して平均します。</p>
    <p>この教材では、共通の問題から始めて、ガウス・ニュートン法、線形・非線形 MPC、MPPI の重みとその理論、Nav2 のパラメータまでを順に積み上げます。各章に numpy だけで動く演習と、ブラウザで動かせるデモがあります。</p>
    <div class="paper-card">
      <div class="t">対象と前提</div>
      <div class="a">大学 1〜2 年の微分と線形代数、確率の基本 (正規分布と期待値)。ROS や GPU は不要です。</div>
      <div><a href="00_roadmap.html">ロードマップから始める</a> ・ <a href="07_comparison.html">先にデモを見る</a></div>
    </div>
  </div>
  <div class="scan-hero">
    <canvas id="hero-mppi" aria-label="MPPI のアニメーション。ロボットが 2 人をよけながらゴールへ向かう。オレンジの線が試しているサンプルで、濃いほど重みが大きい"></canvas>
    <p>MPPI が 2 人をよけながら進む様子。オレンジの細い線が毎周期試している 300 本のサンプル (濃いほど重い)、黒い太線が重みつき平均で作った計画。</p>
  </div>
</section>

<section class="section">
  <h2>中心にある 1 つの問題</h2>
  <p class="lead">制御の周期ごとに、今の状態から N ステップ先までの入力の列を選び、コストの合計を最小にします。</p>
  <div class="arithmatex">\\[
\\min_{{u_0, \\dots, u_{{N-1}}}} \\ \\sum_{{t=0}}^{{N-1}} \\ell(x_t, u_t) + \\phi(x_N)
\\quad \\text{{s.t.}} \\quad x_{{t+1}} = f(x_t, u_t), \\ \\ x_0 = \\hat x, \\ \\ u_{{\\min}} \\le u_t \\le u_{{\\max}}
\\]</div>
  <div class="term-grid">
    <div class="term" style="--c:var(--opt)"><b>モデルとコスト</b>次の状態を計算する式 f と、悪さを表す ℓ, φ。最初の 1 手だけ実行して毎周期解き直す。→ 01 章</div>
    <div class="term" style="--c:var(--mpc)"><b>MPC: 微分で解く</b>残差の 2 乗和と見て、ガウス・ニュートン法や SQP で入力の列を直す。→ 02〜04 章</div>
    <div class="term" style="--c:var(--mppi)"><b>MPPI: 試して解く</b>ゆらぎを足した列を K 本試し、重み e<sup>−S/λ</sup> で平均する。→ 05・06 章</div>
    <div class="term" style="--c:var(--nav2)"><b>比べて使う</b>得意・苦手をデモで確かめ、Nav2 のパラメータに結びつける。→ 07・08 章</div>
  </div>
</section>

<section class="section">
  <h2>進め方</h2>
  <ol class="steps">
    <li>00 章のロードマップで全体像をつかみ、01 章で「解きたい問題」を固める。</li>
    <li>MPC の列 (02 → 03 → 04 章) を読み、演習で数値を確かめる。</li>
    <li>MPPI の列 (05 → 06 章) を読む。06 章では 02 章の LM 法と同じ形の式が出てくる。</li>
    <li>07 章のデモで 2 つを比べ、08 章で Nav2 の設定に結びつける。</li>
  </ol>
</section>

<section class="section">
  <h2>章の一覧</h2>
  <p class="lead">色の印は、その章で主に扱うものです。MPC は青、MPPI はオレンジ、最適化は紫、Nav2 は緑。</p>
  <div class="cards">{''.join(cards)}</div>
</section>

<section class="section">
  <h2>演習の環境</h2>
  <p class="lead">Python 3.9 以上と numpy / scipy / matplotlib があれば全部動きます。</p>
<pre><code>git clone {REPO_URL}.git
cd study_mpc_mppi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python exercises/check_env.py
python exercises/ex05_mppi.py</code></pre>
</section>

<footer class="site">
  Markdown 版は <a href="{REPO_URL}/tree/master/docs" target="_blank" rel="noopener">docs/</a> にあります。この HTML は <code>python tools/build_html.py</code> で docs/ から生成しています。
</footer>
</div>"""
    out = page(SITE_NAME, body, None)
    (OUT / "index.html").write_text(out, encoding="utf-8")


def main():
    OUT.mkdir(exist_ok=True)
    if (OUT / "assets").exists():
        shutil.rmtree(OUT / "assets")
    shutil.copytree(SITE, OUT / "assets")
    if (OUT / "figures").exists():
        shutil.rmtree(OUT / "figures")
    shutil.copytree(DOCS / "figures", OUT / "figures")
    for i in range(len(CHAPTERS)):
        build_chapter(i)
    build_index()
    print(f"HTML を生成しました: {OUT / 'index.html'} ({len(CHAPTERS)} 章)")


if __name__ == "__main__":
    main()
