#!/usr/bin/env bash
# デーモンを --demo で起動し、API と画像サイズを検証するスモークテスト。
# 依存関係がインストール済みであること (pip install -e ".[dev]")。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8899}"
PYTHON="${PYTHON:-python3}"

export PYTHONPATH="${ROOT}/daemon${PYTHONPATH:+:${PYTHONPATH}}"

cd "${ROOT}/daemon"
"${PYTHON}" -m spotify_tv --demo --port "${PORT}" --log-level warning &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

BASE="http://127.0.0.1:${PORT}"

echo "waiting for daemon on ${BASE} ..."
for _ in $(seq 1 50); do
  if curl -fsS "${BASE}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
  echo "daemon failed to start (port ${PORT} already in use?)" >&2
  exit 1
fi

HEALTH=$(curl -fsS "${BASE}/api/health")
echo "health: ${HEALTH}"
[[ "${HEALTH}" == *'"ok"'* ]]

NOW=$(curl -fsS "${BASE}/api/now")
echo "now: ${NOW}"
ART_ID=$("${PYTHON}" -c 'import json,sys; print(json.load(sys.stdin)["art_id"])' <<<"${NOW}")

TMP_FILE=$(mktemp)
trap 'kill "${SERVER_PID}" 2>/dev/null || true; rm -f "${TMP_FILE}"' EXIT

curl -fsS -o "${TMP_FILE}" "${BASE}/api/art/${ART_ID}.bin"
SIZE=$(wc -c <"${TMP_FILE}")
echo "art bytes: ${SIZE}"
[[ "${SIZE}" -eq 115200 ]]

echo "SMOKE TEST OK"
