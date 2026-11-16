#pragma once

// ============================================================
//  SmallTV-Ultra 設定ファイルのサンプル
//  使い方: このファイルを config.h にコピーして編集する
//      cp include/config.example.h include/config.h
//  config.h は .gitignore 済み（認証情報をコミットしない）
// ============================================================

// --- Wi-Fi (2.4GHz のみ) ---
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// --- PC 常駐デーモン ---
#define DAEMON_HOST "192.168.1.10"
#define DAEMON_PORT 8888

// --- 動作設定 ---
#define POLL_INTERVAL_MS 5000   // /api/now のポーリング間隔
#define WIFI_RETRY_MS 5000      // Wi-Fi 再接続の試行間隔
#define HTTP_TIMEOUT_MS 4000    // 1リクエストのタイムアウト

// --- バックライト (GPIO5, 反転論理) ---
#define BACKLIGHT_PIN 5
#define BACKLIGHT_INVERTED 1
#define BACKLIGHT_LEVEL 255     // 0 (消灯) - 255 (最大)
