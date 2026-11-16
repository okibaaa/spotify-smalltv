# GeekMagic SmallTV-Ultra カスタムファームウェア 設計書
## Spotify ジャケット写真 + プログレスバー表示

バージョン: 0.1 (ドラフト)
日付: 2026-11-16

---

## 1. 概要

### 1.1 目的

GeekMagic SmallTV-Ultra (ESP8266 / ST7789 240x240 液晶) の純正ファームウェアを
カスタムファームウェアに置き換え、Spotify で再生中の楽曲の
**ジャケット写真 + プログレスバー**を常時表示する。

### 1.2 システム構成 (全体アーキテクチャ)

```
┌──────────────────────┐        ┌─────────────────────────┐
│  Spotify Web API      │  HTTPS │  PC 常駐デーモン          │
│  api.spotify.com      │◄───────│  (Python / spotipy)      │
│  i.scdn.co (ジャケ写)  │        │  ・OAuth認証管理          │
└──────────────────────┘        │  ・再生状況ポーリング      │
                                │  ・ジャケ写DL→RGB565変換  │
                                │  ・HTTPサーバー (LAN内)   │
                                └───────────┬─────────────┘
                                            │ 平文HTTP (LAN内)
                                            ▼
                                ┌─────────────────────────┐
                                │  SmallTV-Ultra (ESP8266) │
                                │  ・HTTPクライアント        │
                                │  ・ST7789 描画            │
                                │  ・進捗補間・部分再描画    │
                                └─────────────────────────┘
```

**設計判断の理由**: ESP8266 の RAM (実質ヒープ約40KB) では
TLS (BearSSL) 接続 1本で数十KB消費するため、api.spotify.com への
直接 HTTPS アクセスは不可能。よって Spotify との TLS 通信と
JPEG デコードは PC 側デーモンが担い、デバイスは LAN 内の
平文 HTTP で「変換済み画像 + メタデータ」を受信するのみとする。

### 1.3 スコープ

- ファームウェア: Arduino フレームワーク (PlatformIO ビルド)、C++
- PC デーモン: Python 3.11+ / spotipy / Pillow
- 書き込み: シリアル (UART / esptool)
- 対応デバイス: SmallTV-Ultra (ESP8266版) のみ
- 非スコープ: ボタン操作・タッチ (Ultra はボタン無し)、
  Spotify プレイヤー操作 (リモコン機能)、ESP32版 (Pro) 対応

---

## 2. ハードウェア仕様 (SmallTV-Ultra)

| 項目 | 仕様 |
|---|---|
| CPU | ESP8266 (ESP-12E), 80MHz, RAM 約80KB (ヒープ実質 40〜50KB) |
| Flash | 4MB |
| ディスプレイ | ST7789V, 240x240, SPI, 16bit色 (RGB565) |
| SPI CLK | GPIO14 |
| SPI MOSI | GPIO13 |
| DC | GPIO00 |
| RST | GPIO02 |
| Backlight | GPIO05 (PWM, 反転論理) |
| CS | GPIO15 (要実機確認: テスター/回路図で確認すること) |
| ボタン | なし |

⚠️ **制約事項 (最重要)**:
240x240 RGB565 の1フレーム = **115,200 バイト** で ESP8266 の RAM を超過する。
→ フレーム全体をメモリに展開せず、**数KB のチャンクバッファで
HTTP 応答 → SPI へ逐次ストリーミング描画**する方式を採る (§5.4)。

---

## 3. 機能要件

| ID | 要件 |
|---|---|
| FR-01 | PC デーモンから再生中楽曲のメタデータを取得する |
| FR-02 | ジャケット写真 (RGB565 240x240) を取得し全画面表示する |
| FR-03 | 画面下部にプログレスバーを描画する |
| FR-04 | 再生進行を補間し、バー領域のみ部分再描画する (約1秒周期) |
| FR-05 | 曲が変わったら自動でジャケットを差し替える |
| FR-06 | 停止/未再生時は「アイドル画面」(時計 or Not Playing 表示) を出す |
| FR-07 | PC デーモン不在時は「接続エラー」画面を表示し自動再接続する |
| FR-08 | 起動時に Wi-Fi 接続→デーモン検出→表示開始 |
| FR-09 | バックライト PWM 調光対応 (初期値は常時点灯) |
| FR-10 | OTA 更新は必須としない (シリアル書き込み前提) |

非機能要件:
- ジャケット取得 (曲変更検知) から表示完了まで 5 秒以内 (LAN内)
- メモリ: 常時ヒープ空き 15KB 以上を維持
- デバイス側で外部 TLS 通信を行わない

---

## 4. PC 常駐デーモン設計 (Python)

### 4.1 責務

1. Spotify OAuth (Authorization Code Flow + Refresh Token) の管理
2. `/v1/me/player` (Get Currently Playing Track) を 3 秒間隔でポーリング
3. ジャケット URL (640x640, i.scdn.co) をダウンロードし Pillow で
   240x240 にリサイズ → RGB565 変換
4. LAN 内 HTTP サーバー (平文) でデバイスに応答

### 4.2 Spotify 認証

- Spotify Developer Dashboard で App 登録
  (Redirect URI: `http://localhost:8888/callback`)
- 初回のみブラウザで認証 → refresh_token を
  `~/.config/spotify-tv/credentials.json` に保存
- 以降は refresh_token で access_token を自動更新 (有効期限 1 時間)
- **Premium がなくても** `user-read-currently-playing` スコープで
  現在再生中の曲は取得可能

### 4.3 ジャケット変換パイプライン

```
album.images[0].url (640x640 JPEG)
  → Pillow: RGB mode, resize((240,240), LANCZOS)
  → 各ピクセル RGB565 化:
      rgb565 = (R>>3)<<11 | (G>>2)<<5 | (B>>3)
  → リトルエンディアン2バイト列で出力 (ESP8266 の uint16_t に直接読める形式)
  → 115,200 バイトの生バイナリ
  → トラックごとに LRU キャッシュ (直近3曲分)
```

### 4.4 HTTP API (デーモンが提供)

| エンドポイント | 応答 | 用途 |
|---|---|---|
| `GET /api/now` | JSON (§4.5) | 現在の再生状況 |
| `GET /api/art/{art_id}.bin` | RGB565 生データ 115,200B | ジャケット画像 |
| `GET /api/health` | 200 OK | 存在確認 |

### 4.5 `/api/now` JSON スキーマ

```json
{
  "playing": true,
  "track_id": "4uLU6hMCjMI75M1A2tKUQC",
  "art_id": "sha1ハッシュ先頭12桁",
  "title": "曲名",
  "artist": "アーティスト名",
  "progress_ms": 83200,
  "duration_ms": 224000
}
```

- `playing: false` のとき進捗フィールドは未保証 (デバイスは FR-06 へ)
- 進捗補間は「デバイスがデータを取得した時刻からの経過時間」で行う (§5.5)

### 4.6 ポーリング規約

- Spotify API: 3 秒間隔 (レート制限 429 時は `Retry-After` を尊重)
- ジャケット DL は曲変更検知時のみ (art_id キャッシュで重複回避)

### 4.7 技術スタック

- Python 3.11+, spotipy, Pillow, FastAPI + uvicorn (or Flask)
- 起動設定: Windows タスクスケジューラ / systemd 等で常駐

---

## 5. ファームウェア設計 (ESP8266 / Arduino)

### 5.1 技術スタック

- PlatformIO, フレームワーク: arduino, ボード: `esp12e`
- 主要ライブラリ:
  - `ESP8266WiFi` / `ESP8266HTTPClient` (平文 HTTP クライアント)
  - `TFT_eSPI` (ST7789V ドライバ, `User_Setup.h` で §2 のピン定義)
- 設定: `config.h` に Wi-Fi SSID/Pass、デーモンの IP/ポートを定数定義
  (将来 WiFiManager 対応は拡張課題)

### 5.2 モジュール構成

```
src/
  main.cpp             … setup()/loop(), 状態遷移制御
  display.h/.cpp       … TFT_eSPI 初期化、全画面描画、バー部分描画
  spotify_client.h/.cpp … デーモン HTTP クライアント (now取得, art取得)
  art_stream.h/.cpp    … HTTP→SPI チャンクストリーミング描画 (§5.4)
  progress.h/.cpp      … 進捗補間・バー計算
  icons.h              … アイドル/エラー画面用アイコン・フォント
```

### 5.3 状態遷移

```
        起動
         │
    ┌────▼────┐    Wi-Fi接続失敗
    │ BOOT    │────────────►┌──────────┐
    │ (起動画) │◄───────────│ WIFI_ERR │ (5秒毎に再試行)
    └────┬────┘    成功     └──────────┘
         │ /api/health OK
    ┌────▼────┐
    │ FETCH   │◄───────────────┐ 5秒周期 or 曲変化時
    └────┬────┘                │
  playing? ├─true─► ┌──────────┐ │
         │         │ PLAYING  │─┘
         │         │ (§5.5)   │  /api/now 失敗→CONN_ERR
         └─false─► ┌──────────┐
                   │ IDLE     │ (時計表示)
                   └──────────┘
```

状態: `BOOT / WIFI_ERR / CONN_ERR / IDLE / PLAYING`

### 5.4 ジャケット描画 (ストリーミング描画 — 中核処理)

RAM 制約対策の核心。HTTP 応答をフレーム全体として保持しない。

```cpp
// 擬似コード
WiFiClient stream;
http.get("/api/art/<id>.bin");       // Content-Length: 115200
static uint16_t buf[1024];           // 2KB (静的確保) = 1行分
for (int y = 0; y < 240; y++) {
  stream.readBytes(buf, 480);        // 1行分 (240px x 2B)
  tft.pushImage(0, y, 240, 1, buf);  // そのまま SPI へ
}
```

- 応答バイト列はリトルエンディアン RGB565 のまま
  `pushImage` に渡す (ESP8266 の `uint16_t` にそのまま読める)
- 読み込みタイムアウト時はリトライ 1 回 → 失敗で CONN_ERR 表示
- 描画中のヒープ消費: HTTPClient + 2KB バッファで 10KB 未満を見込み

### 5.5 プログレスバー表示

- 配置: 画面下部 240x12px (下端に黒帯を敷きその上にバー)
- 進捗計算:
  ```
  elapsed = millis() - lastFetchMillis
  pos_ms  = progress_ms_at_fetch + elapsed  (playing中のみ加算)
  ratio   = pos_ms / duration_ms
  ```
- `PLAYING` 状態では **1秒周期でバー領域のみ部分再描画**
  (`tft.fillRect` 2 回: 進捗分の前景色 + 残り背景色)。全画面再描画はしない
- 曲終端に到達したら即 `FETCH` へ戻り実況を取り直す
- 曲変更検知 (track_id 変化) 時のみ §5.4 のジャケット再取得を実行

### 5.6 メモリ・タイミング見積り

| 要素 | 消費 |
|---|---|
| HTTPClient + WiFiClient | 〜6KB |
| 描画チャンクバッファ | 2KB (静的) |
| TFT_eSPI 内部 | 〜2KB |
| JSON パース (ArduinoJson) その他 | 〜4KB |
| **合計** | **〜14KB < 実質ヒープ 40KB ✓** |

---

## 6. 書き込み手順 (UART)

1. 本体を分解し ESP-12E のパッドを露出 (TX/RX/GPIO0/GND/EN)
2. `GPIO0 → GND` 接続で電源投入 → ブートローダーモード
3. PlatformIO から esptool で書き込み:
   - ボーレート 115200 (確実性重視; 921600 は要調整)
   - flash size 4MB
4. `GPIO0` を切断して再起動
5. **復旧手段**: 純正 FW の bin を同手順で再書き込みすれば戻せる
   (必ず純正 bin を事前に入手・保管しておくこと)

⚠️ 純正 Web コンソールからの書き換えは Magic Byte チェックにより
カスタム FW が通常書けないため、**シリアル書き込みを標準とする**。

---

## 7. テスト計画

| 段階 | 内容 | 合格基準 |
|---|---|---|
| T-1 | 単体: TFT_eSPI でテストパターン表示 | 240x240 正常表示 (色順・反転確認) |
| T-2 | 単体: デーモン `curl /api/now`, `/api/art` | JSON/画像サイズ正 |
| T-3 | 結合: デバイスが /api/now を取得 | シリアルログに track 情報 |
| T-4 | 結合: ジャケットストリーミング描画 | 5秒以内に全画面表示、ヒープ>15KB |
| T-5 | シナリオ: 曲変更/一時停止/再開/デーモン停止 | 各状態が仕様どおり遷移 |
| T-6 | 長時間 (8h) 動作 | メモリリーク・フリーズなし |

---

## 8. マイルストーン

1. **M1 環境構築** — PlatformIO プロジェクト作成、TFT_eSPI テスト表示 (T-1)
2. **M2 デーモン実装** — OAuth/ポーリング/RGB565変換/HTTPサーバー (T-2)
3. **M3 クライアント結合** — /api/now 取得と状態遷移 (T-3)
4. **M4 ジャケット表示** — ストリーミング描画 (T-4)
5. **M5 プログレスバー** — 補間と部分再描画 (T-5)
6. **M6 仕上げ** — エラー画面/調光/長時間試験 (T-6)

---

## 9. リスクと対策

| リスク | 影響 | 対策 |
|---|---|---|
| CS ピンが GPIO15 以外 | 画面が出ない | 実機で配線確認 (T-1 で早期発見) |
| 色順 (RGB/BGR) 反転・表示反転 | 色が変 | TFT_eSPI の `TFT_INVERT_ON` / color order 設定で調整 |
| HTTP 転送中の切断 | 画面乱れ | タイムアウト→1リトライ→CONN_ERR |
| Spotify API レート制限 | 更新遅延 | デーモン3秒ポーリング+429尊重。デバイス5秒ポーリングで分散 |
| ESP8266 ヒープ枯渇 | フリーズ | 静的確保中心、T-6 でヒープログ監視 |
| 純正 FW への復旧不可 | 端末故障 | 書き込み前に純正 bin を入手・保管 |
| 曲名/アーティスト未表示 (現設計) | 機能不足 | 将来拡張: 下部黒帯にフォント描画追加 |

---

## 10. 未決事項 / 将来拡張

- [ ] CS ピン・DC/RST ピンの実機確定 (テスター確認)
- [ ] Wi-Fi 設定の UI (WiFiManager) 対応
- [ ] 曲名・アーティスト名オーバーレイ表示
- [ ] カセットテープ風アニメーション演出
- [ ] Home Assistant / MQTT 対応
- [ ] ESP32 版 (SmallTV Pro) へのポータビリティ
