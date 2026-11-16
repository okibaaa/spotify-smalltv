# Spotify SmallTV

GeekMagic SmallTV-Ultra (ESP8266 + ST7789 240x240) に
**Spotify で再生中の曲のジャケット写真とプログレスバー**を表示するカスタムファームウェアと、
そのための PC 常駐デーモンです。

- ジャケットは 240x240 RGB565 に変換して LAN 内 HTTP で配信
- デバイスは画像を 1 行ずつ SPI にストリーミング（RAM 消費 2KB）
- Spotify 未契約でも動く **デモモード** 内蔵
- devcontainer / Docker / GitHub Actions でどこでもビルド・デバッグ可能

設計書: [`docs/design.md`](docs/design.md) /
書き込み手順: [`firmware/FLASHING.md`](firmware/FLASHING.md)

---

## アーキテクチャ

```
Spotify Web API ──HTTPS──► PC 常駐デーモン (Python/FastAPI)
                              │  ・OAuth / 曲情報ポーリング
                              │  ・ジャケ写 → RGB565 変換
                              ▼
                      平文 HTTP (LAN 内)
                              │  /api/now, /api/art/{id}.bin
                              ▼
                    SmallTV-Ultra (ESP8266)
                      ・HTTP クライアント
                      ・ST7789 描画 / 進捗補間
```

ESP8266 の RAM では Spotify への TLS 接続が現実的でないため、
TLS と JPEG デコードは PC 側で行います。

---

## リポジトリ構成

```
.
├── firmware/                  ESP8266 ファームウェア (PlatformIO / Arduino)
│   ├── platformio.ini         ピン設定・ビルド設定
│   ├── FLASHING.md            シリアル書き込み手順
│   ├── include/
│   │   ├── config.example.h   設定サンプル（これをコピーして使う）
│   │   ├── app_config.h       config.h を読み込むラッパー
│   │   └── config.h           ローカル設定（Git 管理外）
│   └── src/
│       ├── main.cpp           状態遷移・ポーリング
│       ├── display.*          ST7789 描画・プログレスバー
│       ├── spotify_client.*   デーモン HTTP クライアント
│       ├── progress.h         進捗補間
│       └── types.h            共有データ構造
├── daemon/                    PC 常駐デーモン (Python)
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── spotify_tv/
│   │   ├── __main__.py        起動エントリ
│   │   ├── auth.py            OAuth ログイン
│   │   ├── config.py          環境変数設定
│   │   ├── poller.py          Spotify ポーリング
│   │   ├── artwork.py         ジャケ写 → RGB565
│   │   ├── state.py           共有状態
│   │   ├── server.py          FastAPI
│   │   └── demo.py            デモモード
│   └── tests/                 pytest
├── scripts/smoke-test.sh      --demo 起動 + API 検証
├── docs/design.md             設計書
├── .devcontainer/             VS Code / Codespaces 用
├── .github/workflows/         CI（ビルド・テスト）と Release
├── Makefile                   よく使うコマンド
├── docker-compose.yml         デーモンを Docker で常駐
└── .env.example               Spotify 認証情報のサンプル
```

---

## クイックスタート

### 必要なもの

| 用途 | 必要なもの |
|---|---|
| デーモン | Python 3.10+（`python3-venv` 推奨）、Spotify アカウント |
| ファーム | PlatformIO、USB-シリアル変換（3.3V） |
| 書き込み | プラスドライバー、ジャンパ線（詳細は [FLASHING.md](firmware/FLASHING.md)） |

### 1. セットアップ

```bash
git clone https://github.com/<your-name>/spotify-smalltv.git
cd spotify-smalltv
make setup
```

`make setup` は以下を行います:

- `daemon/.venv` 作成 + 依存インストール
- `firmware/include/config.h` をサンプルから作成

### 2. デモモードで動作確認（Spotify 不要）

```bash
make demo
# 別ターミナル
curl http://localhost:8888/api/now
```

`make smoke` で API と 115,200 バイトの画像配信を自動検証できます。

### 3. Spotify と連携

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) でアプリ作成
2. Redirect URI に `http://127.0.0.1:8888/callback` を追加
3. `.env` を作成して認証情報を記入:

```bash
cp .env.example .env
# SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET を編集
```

4. 初回ログイン:

```bash
make login
```

5. デーモン起動:

```bash
make daemon
```

デフォルトで `0.0.0.0:8888`。デバイスから到達できるよう
PC のファイアウォールで 8888/tcp を許可してください。

### 4. ファームウェア

```bash
# Wi-Fi と PC の IP を設定
${EDITOR:-vi} firmware/include/config.h

# ビルド
make build

# 書き込み（GPIO0 を GND に落として電源投入した状態で）
make flash UPLOAD_PORT=/dev/ttyUSB0

# ログ
make monitor MONITOR_PORT=/dev/ttyUSB0
```

書き込みの詳細（分解・配線・バックアップ・復旧）は
**[firmware/FLASHING.md](firmware/FLASHING.md)** を参照してください。

---

## どこでも開発する

### VS Code Dev Container / GitHub Codespaces

`.devcontainer/` に Python 3.12 + PlatformIO + esptool 入りの環境を用意しています。

- VS Code: 「Reopen in Container」
- Codespaces: リポジトリを開いて「Create codespace」

作成時に自動で `pip install -e ".[dev]"` と `config.h` の生成が行われます。
デーモンは `make demo` ですぐ起動できます。

> USB シリアル書き込みはホスト側で行うのが確実です。
> Linux でコンテナから書き込む場合は `devcontainer.json` に
> `"runArgs": ["--device=/dev/ttyUSB0"]` を追加してください。

### Docker でデーモンを常駐

```bash
cp .env.example .env   # 認証情報を記入
docker compose up --build -d

# 初回ログイン（ブラウザ認証のためポートを公開して実行）
docker compose run --rm --service-ports daemon spotify-tv-login
```

`http://<ホストIP>:8888/api/now` で確認できます。
トークンは Docker ボリューム `spotify-tv-config` に保存されます。

### CI

GitHub Actions (`.github/workflows/ci.yml`) が push / PR ごとに実行されます:

- **firmware**: PlatformIO でビルドし、`firmware.bin` を Artifact に保存
- **daemon**: pytest + `scripts/smoke-test.sh`（デモ API の結合テスト）

`v*` タグを push すると Release ワークフローが
`smalltv-ultra-vX.Y.Z.bin` を GitHub Release に添付します。

---

## コマンド一覧

| コマンド | 内容 |
|---|---|
| `make setup` | venv 作成 + 依存インストール + `config.h` 生成 |
| `make demo` | Spotify なしでデーモン起動 |
| `make login` | Spotify OAuth 初回ログイン |
| `make daemon` | `.env` を読み込んでデーモン起動 |
| `make test` | pytest |
| `make smoke` | デモ API のスモークテスト |
| `make build` | ファームウェアビルド |
| `make flash` | 書き込み（`UPLOAD_PORT` 指定可） |
| `make monitor` | シリアルモニタ（`MONITOR_PORT` 指定可） |
| `make clean` | ビルド成果物削除 |

---

## API 仕様（デーモン → デバイス）

### `GET /api/now`

```json
{
  "playing": true,
  "track_id": "4uLU6hMCjMI75M1A2tKUQC",
  "art_id": "a1b2c3d4e5f6",
  "title": "曲名",
  "artist": "アーティスト名",
  "progress_ms": 83200,
  "duration_ms": 224000
}
```

### `GET /api/art/{art_id}.bin`

- 240x240 RGB565 の生バイナリ、**115,200 バイト固定**
- リトルエンディアン（ESP8266 の `uint16_t` にそのまま読める）
- `Cache-Control: no-store`

### `GET /api/health`

`{"ok": true}`。死活監視用。

---

## 環境変数

| 変数 | 既定値 | 説明 |
|---|---|---|
| `SPOTIFY_CLIENT_ID` | (必須) | Spotify アプリの Client ID |
| `SPOTIFY_CLIENT_SECRET` | (必須) | Client Secret |
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:8888/callback` | アプリ登録と一致させる |
| `SPOTIFY_TV_HOST` | `0.0.0.0` | リッスンアドレス |
| `SPOTIFY_TV_PORT` | `8888` | ポート |
| `SPOTIFY_TV_POLL_INTERVAL` | `3.0` | Spotify ポーリング秒数 |
| `SPOTIFY_TV_CACHE` | `~/.config/spotify-tv/credentials.json` | トークン保存先 |

---

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| 画面が真っ白/真っ黒 | CS/DC/RST ピンを確認（[FLASHING.md](firmware/FLASHING.md)） |
| 色が赤青反転 | `platformio.ini` の `TFT_RGB_ORDER` を `TFT_BGR` ↔ `TFT_RGB` |
| 画面が上下/左右反転 | `display.cpp` の `tft.setRotation(0)` を 0〜3 に変更 |
| Daemon unreachable | PC のファイアウォール、`config.h` の IP、同一 LAN を確認 |
| `art.bin` が 404 | 曲変更直後の取得失敗。5 秒後に自動再試行 |
| Wi-Fi に繋がらない | 2.4GHz のみ対応。SSID/パスワードを確認 |
| ヒープ不足で再起動 | シリアルログの `free heap` を確認。`SPI_FREQUENCY` を下げる |
| 書き込みで `Connecting...` のまま | GPIO0 を GND、TX/RX クロス、RST を一瞬 GND |

---

## GitHub に公開するまで

このリポジトリは初期コミット済みのローカル Git リポジトリです。
GitHub 上に空のリポジトリを作成したら、以下を実行します。

```bash
git remote add origin https://github.com/<your-name>/spotify-smalltv.git
git push -u origin main
```

GitHub CLI を使う場合:

```bash
gh repo create spotify-smalltv --private --source=. --remote=origin --push
```

> `firmware/include/config.h` と `.env` は `.gitignore` 済みです。
> Wi-Fi パスワードや Spotify のシークレットがコミットされていないか、
> push 前に `git status` で確認してください。

---

## 設計資料

- 設計書: [`docs/design.md`](docs/design.md)
- 書き込み手順: [`firmware/FLASHING.md`](firmware/FLASHING.md)

## ライセンス

[MIT License](LICENSE) © 2026 okiba
