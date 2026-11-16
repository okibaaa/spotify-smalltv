#!/usr/bin/env bash
# devcontainer 作成後に一度だけ実行されるセットアップ
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [ ! -f firmware/include/config.h ]; then
  cp firmware/include/config.example.h firmware/include/config.h
  echo "firmware/include/config.h を作成しました（Wi-Fi / IP を編集してください）"
fi

cd daemon
python -m pip install -q -e ".[dev]"
echo "daemon の依存関係をインストールしました"
