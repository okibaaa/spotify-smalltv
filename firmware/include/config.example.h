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
#define WIFI_RESCUE_DELAY_MS 30000  // 切断から復旧用 AP を立てるまでの待ち時間
#define HTTP_TIMEOUT_MS 4000    // 1リクエストのタイムアウト

// --- バックライト (GPIO5, 反転論理) ---
#define BACKLIGHT_PIN 5
#define BACKLIGHT_INVERTED 1
#define BACKLIGHT_LEVEL 255     // 0 (消灯) - 255 (最大)

// ============================================================
//  OTA (Wi-Fi 経由のファームウェア更新) / 復旧用 AP
//  Wi-Fi に繋がらないときは自動で AP を立て、192.168.4.1 で
//  更新ページを開けます。パスワードは必ず変更してください。
// ============================================================
#define OTA_ENABLED 1
#define OTA_WEB_USER "admin"
#define OTA_WEB_PASS "CHANGE_ME"          // 8文字以上を推奨
#define OTA_AP_SSID_PREFIX "SmallTV-Setup"
#define OTA_AP_PASSWORD "CHANGE_ME_TOO"   // 8文字以上 (短いとオープンAP)
