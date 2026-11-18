#pragma once

// ============================================================
//  config.h はローカル専用ファイル（Git 管理外）
//
//  初回セットアップ:
//    cd firmware/include
//    cp config.example.h config.h
//  その後 config.h の Wi-Fi / デーモン IP を編集してください。
// ============================================================

#if __has_include("config.h")
#include "config.h"
#else
#error "firmware/include/config.h がありません。`cp include/config.example.h include/config.h` を実行してください。"
#endif

// 古い config.h でもビルドできるように既定値を用意する
#ifndef OTA_ENABLED
#define OTA_ENABLED 1
#endif
#ifndef WIFI_RESCUE_DELAY_MS
#define WIFI_RESCUE_DELAY_MS 30000
#endif
