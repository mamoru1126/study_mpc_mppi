# 学習環境の便利コマンド
PY ?= python3

.PHONY: setup check exercises figures html all

setup:
	$(PY) -m pip install -r requirements.txt

check:
	$(PY) exercises/check_env.py

exercises:
	$(PY) exercises/ex01_receding_horizon.py
	$(PY) exercises/ex02_gauss_newton.py
	$(PY) exercises/ex03_linear_mpc.py
	$(PY) exercises/ex04_nmpc.py
	$(PY) exercises/ex05_mppi.py
	$(PY) exercises/ex06_mppi_theory.py

figures:
	$(PY) tools/make_diagrams.py

html:
	$(PY) tools/build_html.py

all: exercises figures html
