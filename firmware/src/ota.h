#pragma once

#include <Arduino.h>
#include <IPAddress.h>

namespace ota {

// 通常の Wi-Fi 接続後に呼ぶ。80 番で Web 更新ページを開始する。
void begin();

// Wi-Fi に繋がらないときの復旧用アクセスポイントを立てる。
// 2 回目以降の呼び出しは何もしない。
void startRescueAp();

// 復旧用 AP を止めて通常の STA モードへ戻す。
void exitRescue();

bool inRescueMode();

// 復旧用 AP の SSID (例: SmallTV-Setup-12ab34)
String rescueSsid();

// 復旧用 AP の IP (通常 192.168.4.1)
IPAddress rescueIp();

// loop() から毎回呼ぶ。
void loop();

}  // namespace ota
