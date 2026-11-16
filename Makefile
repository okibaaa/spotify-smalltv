# よく使うコマンド集
# 使い方: make help
PYTHON ?= python3
UPLOAD_PORT ?= /dev/ttyUSB0
MONITOR_PORT ?= /dev/ttyUSB0

.PHONY: help setup build flash monitor test smoke demo daemon login clean

help:
	@echo "make setup      依存関係と config.h を準備"
	@echo "make build      ファームウェアをビルド"
	@echo "make flash      ファームウェアを書き込み (UPLOAD_PORT=/dev/ttyUSB0)"
	@echo "make monitor    シリアルモニタ (MONITOR_PORT=/dev/ttyUSB0)"
	@echo "make test       デーモンのテスト"
	@echo "make smoke      --demo で API スモークテスト"
	@echo "make demo       Spotify なしでデーモンを起動"
	@echo "make login      Spotify OAuth 初回ログイン (.env を読み込む)"
	@echo "make daemon     Spotify 連携でデーモンを起動 (.env を読み込む)"
	@echo "make clean      ビルド成果物を削除"

setup:
	cd daemon && $(PYTHON) -m venv .venv && .venv/bin/pip install -q -e ".[dev]"
	@if [ ! -f firmware/include/config.h ]; then \
		cp firmware/include/config.example.h firmware/include/config.h; \
		echo "firmware/include/config.h を作成しました。Wi-Fi と PC の IP を編集してください。"; \
	fi

build:
	cd firmware && pio run

flash:
	cd firmware && pio run -t upload --upload-port $(UPLOAD_PORT)

monitor:
	cd firmware && pio device monitor -b 115200 --port $(MONITOR_PORT)

test:
	cd daemon && .venv/bin/python -m pytest -q

smoke:
	PYTHON=daemon/.venv/bin/python bash scripts/smoke-test.sh

demo:
	@echo "Web simulator: http://localhost:$${SPOTIFY_TV_PORT:-8888}/sim/"
	cd daemon && .venv/bin/python -m spotify_tv --demo

login:
	set -a && . ./.env && set +a && cd daemon && .venv/bin/spotify-tv-login

daemon:
	set -a && . ./.env && set +a && cd daemon && .venv/bin/python -m spotify_tv

clean:
	cd firmware && pio run -t clean
	rm -rf daemon/.pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
