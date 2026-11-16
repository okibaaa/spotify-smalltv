# SmallTV-Ultra 書き込み手順（シリアル / UART）

対象: GeekMagic SmallTV-Ultra (ESP8266 / ESP-12E, 4MB Flash)

> 純正 Web コンソールからの書き換えは Magic Byte チェックがあり、
> カスタムファームウェアは書けません。**有線 UART 書き込み**を行います。

---

## 0. 必要なもの

| 品目 | 例 | 注意 |
|---|---|---|
| USB-シリアル変換 | CH340 / CP2102 / FT232 | **3.3V ロジック**のもの。5V 品は不可 |
| ジャンパ線 | メス-メス など | 6本程度 |
| ピンヘッダ (任意) | 2.54mm 6ピン | 繰り返し書き込むなら半田付け推奨 |
| USB 電源 | 本体付属の USB ケーブル | 本体の電源入力から給電 |
| PC | Linux / macOS / Windows | PlatformIO または esptool |

> ⚠️ 変換アダプタの **VCC は接続しない**でください。
> 本体は付属の USB ケーブルで給電し、**GND だけ共通化**します。
> （アダプタの 3.3V で給電すると電流不足で起動しないことがあります）

---

## 1. 分解してパッドを出す

1. 底面のネジ（2本）を外す
2. 画面侧を押し出すようにして基板を取り出す
3. 基板の左端に **6ピンのスルーホール**がある

SmallTV-Ultra の UART パッド（上から順）:

```
┌─────────┐
│  RST    │ 1  ← リセット (任意)
│  GPIO0  │ 2  ← 書き込みモード (GND に落とす)
│  VCC    │ 3  ← 3.3V (接続しない)
│  RX     │ 4  ← アダプタの TX へ
│  TX     │ 5  ← アダプタの RX へ
│  GND    │ 6  ← アダプタの GND へ
└─────────┘
```

> ロットによってシルクや並びが異なる場合があります。
> 必ずテスターで GND との導通・VCC の 3.3V を確認してください。
> 参考写真: https://github.com/iodn/geekmagic-tv-esp8266/blob/master/assets/UART-pinout.jpg

---

## 2. 配線

| USB-シリアル変換 | 本体パッド | 備考 |
|---|---|---|
| TX | RX | **クロス接続** |
| RX | TX | **クロス接続** |
| GND | GND | 必ず共通 |
| 3V3 / VCC | (未接続) | 接続しない |
| GND (ジャンパ) | GPIO0 | 書き込み時だけ GND |

GPIO0 → GND のジャンパは、書き込み時のみ接続します。
（スイッチ付きジャンパやピンセットでショートしても可）

---

## 3. 書き込みモードに入る

1. GPIO0 を GND に接続したまま
2. 本体の USB ケーブルを差して電源投入
3. これで ESP8266 がブートローダーモードに入ります

うまく入らない場合:

- GPIO0 を GND に接続したまま、**RST パッドを一瞬 GND に触れて離す**
- USB ケーブルを抜き差しして再試行

確認:

```bash
esptool.py --port /dev/ttyUSB0 chip_id
# Connecting....
# Chip is ESP8266EX
# ...
```

`Connecting....` のまま失敗する場合は、TX/RX のクロスと GPIO0 を再確認。

---

## 4. 純正ファームをバックアップ（必須）

書き換え前に、工場出荷状態を丸ごと吸い出しておきます。

```bash
# Flash サイズの確認 (4MB = 0x400000)
esptool.py --port /dev/ttyUSB0 flash_id

# 全 Flash を読み出し (数分かかります)
esptool.py --port /dev/ttyUSB0 --baud 460800 \
  read_flash 0x0 0x400000 stock-backup.bin
```

- `stock-backup.bin` は **4,194,304 バイト** になることを確認
- このファイルがあれば、いつでも純正状態に戻せます
- 大切に保管してください（RF キャリブレーション情報も含まれます）

---

## 5. 書き込み

### PlatformIO を使う場合

```bash
cd spotify-smalltv/firmware
pio run -t upload --upload-port /dev/ttyUSB0
```

出力例:

```
Writing at 0x00000000... (100 %)
Wrote 353680 bytes ...
Hard resetting via RTS pin...
```

> PlatformIO は自動リセットを試みますが、ESP-12E では効かないことがあります。
> その場合は手順 3 の状態にしてからコマンドを実行してください。

### esptool を直接使う場合

```bash
esptool.py --port /dev/ttyUSB0 --baud 115200 \
  write_flash 0x0 .pio/build/smalltv-ultra/firmware.bin
```

- 書き込み先は **0x0**（PlatformIO の firmware.bin はブートローダ込みの結合イメージ）
- `0x00000` 以外を指定すると起動しません
- ボーレートは 115200 が確実。460800 が通れば高速化できます

### Windows の場合

```powershell
esptool.py --port COM3 --baud 115200 write_flash 0x0 .pio\build\smalltv-ultra\firmware.bin
```

デバイスマネージャで CH340/CP210x の COM 番号を確認してください。

---

## 6. 起動確認

1. USB 電源を抜く
2. **GPIO0 → GND のジャンパを外す**
3. USB を差し直す
4. 画面にロゴ → 「Connecting Wi-Fi」と出れば成功

シリアルログを見る場合:

```bash
pio device monitor -b 115200
# または
python3 -m serial.tools.miniterm /dev/ttyUSB0 115200
```

正常時のログ例:

```
=== Spotify SmallTV-Ultra ===
[wifi] connected: 192.168.1.42
[main] fetching art a1b2c3d4e5f6
[art] drawn a1b2c3d4e5f6 in 412 ms
[mem] free heap: 38216
```

---

## 7. 純正ファームに戻す

```bash
esptool.py --port /dev/ttyUSB0 --baud 460800 \
  write_flash 0x0 stock-backup.bin
```

バックアップを取っていない場合は、GeekMagic 公式リポジトリの
SmallTV-Ultra 用ファームウェアを同じ手順で書き込みます:
https://github.com/GeekMagicClock/smalltv-ultra

---

## 8. トラブルシューティング

| 症状 | 対処 |
|---|---|
| `Connecting....` で止まる | GPIO0 が GND か、TX/RX クロスを確認。RST を GND に一瞬触れる |
| `Failed to connect to ESP8266: Timed out` | 電源不足。本体付属 USB で給電し、アダプタ VCC は未接続に |
| `Permission denied: /dev/ttyUSB0` | `sudo usermod -aG dialout $USER` → 再ログイン。暫定は `sudo chmod a+rw /dev/ttyUSB0` |
| 書き込み後、画面が真っ白 | CS/DC/RST のピン設定を確認。`platformio.ini` の `build_flags` を修正して再書き込み |
| 起動しない（書き込み後） | GPIO15 (CS) が起動時に LOW か確認。必要なら 10kΩ プルダウン。GPIO0 は HIGH |
| 画面が上下/左右反転 | `display.cpp` の `tft.setRotation(0)` を 0〜3 に変更 |
| 色が赤青反転 | `platformio.ini` の `TFT_RGB_ORDER=TFT_BGR` を `TFT_RGB` に変更 |
| Wi-Fi に繋がらない | 2.4GHz のみ対応。SSID/パスワードと `config.h` を確認 |
| 純正に戻したい | 手順 7。バックアップが無ければ公式ファームを書き込み |

---

## メモ: 書き込み後の更新

本ファームウェアは OTA を実装していません。
更新時は毎回このシリアル手順が必要です。

繰り返し開発する場合は、6ピンヘッダを半田付けしておくと
ジャンパを差し替えるだけで書き込めます。
