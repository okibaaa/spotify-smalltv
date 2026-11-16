# Spotify SmallTV

[![CI](https://github.com/okibaaa/spotify-smalltv/actions/workflows/ci.yml/badge.svg)](https://github.com/okibaaa/spotify-smalltv/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

GeekMagic SmallTV-Ultra (ESP8266 + ST7789 240x240) に、
Spotify で再生中の**ジャケット写真とプログレスバー**を表示するカスタムファームウェアです。

認証・画像変換は PC 側のデーモンが担当し、デバイスは LAN 内 HTTP で受け取るだけなので、
RAM の少ない ESP8266 でも滑らかに動作します。

```
Spotify ──HTTPS──▶ PC デーモン ──HTTP (LAN)──▶ SmallTV
                   認証・ポーリング・変換        描画のみ
```

## できること

- ジャケット全画面表示 + 下部プログレスバー（1 秒ごとに更新）
- 曲変更の自動検知・自動差し替え
- 停止中 / デーモン未接続 / Wi-Fi 切断を画面表示し、自動復帰
- Spotify アカウント不要の**デモモード**内蔵

## クイックスタート

必要なもの: Python 3.10+（`python3-venv`）、PlatformIO、3.3V USB-シリアル変換。

### 1. セットアップ

```bash
git clone https://github.com/okibaaa/spotify-smalltv.git
cd spotify-smalltv
make setup
```

### 2. デモで動作確認

Spotify の設定なしで試せます。

```bash
make demo
# 別ターミナルで
curl http://localhost:8888/api/now
```

### 3. ブラウザで動くシミュレーター

実機の表示と状態遷移をブラウザで確認できるシミュレーターを、別リポジトリで公開しています。

- 公開版: <https://okibaaa.github.io/spotify-smalltv-simulator/>
- ソース: <https://github.com/okibaaa/spotify-smalltv-simulator>

モックモードなら Spotify もデーモンも不要です。`make demo` でデーモンを起動したうえで
「Daemon」タブを選ぶと、実際のジャケットと進捗をそのまま表示できます。

### 4. Spotify と連携

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) でアプリを作成
2. Redirect URI に `http://127.0.0.1:8888/callback` を追加
3. `.env` に Client ID / Secret を記入

```bash
cp .env.example .env
${EDITOR:-vi} .env
make login    # 初回のみブラウザ認証
make daemon
```

デーモンは `0.0.0.0:8888` で待ち受けます。PC のファイアウォールで 8888/tcp を許可してください。

### 5. デバイスに書き込み

`firmware/include/config.h` に Wi-Fi と PC の IP を設定してから書き込みます。

```bash
cp firmware/include/config.example.h firmware/include/config.h
${EDITOR:-vi} firmware/include/config.h

make build
make flash UPLOAD_PORT=/dev/ttyUSB0
make monitor MONITOR_PORT=/dev/ttyUSB0
```

配線・分解・バックアップ・復旧の詳細は **[firmware/FLASHING.md](firmware/FLASHING.md)** を参照してください。

## よく使うコマンド

| コマンド | 内容 |
|---|---|
| `make setup` | 依存関係と `config.h` を準備 |
| `make demo` | Spotify なしで起動 |
| `make login` / `make daemon` | OAuth ログイン / 本番起動 |
| `make test` / `make smoke` | テスト / デモ API の結合テスト |
| `make build` / `make flash` | ビルド / 書き込み |
| `make monitor` | シリアルログ表示 |

## API（デーモン → デバイス）

| エンドポイント | 内容 |
|---|---|
| `GET /api/now` | 再生状態・曲情報・進捗の JSON |
| `GET /api/art/{art_id}.bin` | 240x240 RGB565（リトルエンディアン、115,200 バイト固定） |
| `GET /api/health` | 死活監視 |

ブラウザのシミュレーターから直接読めるよう、`/api/*` はクロスオリジン GET を許可しています
（`Access-Control-Allow-Origin: *`。認証情報を扱わない読み取り専用 API のため）。

`/api/now` の例:

```json
{
  "playing": true,
  "track_id": "4uLU6hMCjMI75M1A2tKUQC",
  "art_id": "a1b2c3d4e5f6",
  "title": "曲名",
  "artist": "アーティスト名",
  "progress_ms": 83200,
  "duration_ms": 224000,
  "stale": false,
  "error": null
}
```

- `progress_ms` は応答時刻まで補間済み
- Spotify 側の情報が 15 秒以上更新されていないと `stale: true` になり、
  直近の失敗理由が `error` に入る（デバイスはエラー画面を表示）
- ジャケットが無い曲は `art_id: "no-art"` のプレースホルダ画像を返す

## 設定

| 変数 | 既定値 | 説明 |
|---|---|---|
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | (必須) | Spotify アプリの認証情報 |
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:8888/callback` | アプリ登録と一致させる |
| `SPOTIFY_TV_HOST` | `0.0.0.0` | デーモンのリッスンアドレス |
| `SPOTIFY_TV_PORT` | `8888` | デーモンの待ち受けポート |
| `SPOTIFY_TV_POLL_INTERVAL` | `3.0` | Spotify ポーリング間隔（秒） |
| `SPOTIFY_TV_CACHE` | `~/.config/spotify-tv/credentials.json` | トークンの保存先 |

トークンは既定で `~/.config/spotify-tv/credentials.json` に保存されます。

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| 画面が真っ白 | CS/DC/RST のピン設定を確認（[FLASHING.md](firmware/FLASHING.md)） |
| 色が赤青反転 | `platformio.ini` の `TFT_RGB_ORDER` を `TFT_BGR` ↔ `TFT_RGB` |
| Daemon unreachable | `config.h` の IP、PC のファイアウォール、同一 LAN を確認 |
| Wi-Fi に繋がらない | 2.4GHz のみ対応。SSID / パスワードを確認 |
| 書き込みが `Connecting...` で止まる | GPIO0 を GND、TX/RX クロス、RST を一瞬 GND |

## ドキュメント

- [設計書](docs/design.md)
- [書き込み手順](firmware/FLASHING.md)

## ライセンス

[MIT License](LICENSE) © 2026 okiba
