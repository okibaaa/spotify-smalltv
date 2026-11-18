#include "ota.h"

#include <ESP8266HTTPUpdateServer.h>
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>

#include <cstring>

#include "app_config.h"

// 古い config.h でもビルドできるように既定値を用意する
#ifndef OTA_ENABLED
#define OTA_ENABLED 1
#endif
#ifndef OTA_WEB_USER
#define OTA_WEB_USER "admin"
#endif
#ifndef OTA_WEB_PASS
#define OTA_WEB_PASS "smalltv-ota"
#endif
#ifndef OTA_AP_SSID_PREFIX
#define OTA_AP_SSID_PREFIX "SmallTV-Setup"
#endif
#ifndef OTA_AP_PASSWORD
#define OTA_AP_PASSWORD "smalltv-ota"
#endif

namespace {

ESP8266WebServer server(80);
ESP8266HTTPUpdateServer httpUpdater;
bool serverStarted = false;
bool rescueMode = false;

String rescueSsidValue() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char buf[40];
  snprintf(buf, sizeof(buf), "%s-%02x%02x%02x", OTA_AP_SSID_PREFIX, mac[3], mac[4],
           mac[5]);
  return String(buf);
}

String statusJson() {
  String json = "{";
  json += "\"mode\":\"";
  json += rescueMode ? "rescue" : "station";
  json += "\",\"ip\":\"";
  json += (rescueMode ? WiFi.softAPIP() : WiFi.localIP()).toString();
  json += "\",\"ssid\":\"";
  json += rescueMode ? rescueSsidValue() : WiFi.SSID();
  json += "\",\"free_heap\":";
  json += String(ESP.getFreeHeap());
  json += "}";
  return json;
}

String indexPage() {
  String html;
  html += F("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Spotify SmallTV</title><style>"
            "body{font-family:system-ui,sans-serif;max-width:32rem;margin:2rem auto;"
            "padding:0 1rem;line-height:1.6;color:#111}"
            "code{background:#f3f3f3;padding:.1rem .3rem;border-radius:.2rem}"
            "input[type=file]{display:block;margin:.8rem 0}"
            "button{padding:.5rem 1rem;font-size:1rem}"
            ".muted{color:#666;font-size:.9rem}</style></head><body>");
  html += F("<h1>Spotify SmallTV</h1><p>Firmware update over Wi-Fi.</p>");
  html += F("<p class='muted'>状態: ");
  html += rescueMode ? F("復旧モード (AP)") : F("通常 (Wi-Fi 接続済み)");
  html += F("</p><form method='POST' action='/update' "
            "enctype='multipart/form-data'>"
            "<input type='file' name='firmware' accept='.bin' required>"
            "<button type='submit'>書き込み</button></form>");
  html += F("<p class='muted'>アップロードするのは PlatformIO が生成した "
            "<code>firmware.bin</code> です。<br>"
            "書き込み後は自動で再起動します。</p>");
  html += F("<p class='muted'><a href='/api/status'>/api/status</a></p>");
  html += F("</body></html>");
  return html;
}

void handleRoot() { server.send(200, F("text/html; charset=utf-8"), indexPage()); }

void handleStatus() {
  server.send(200, F("application/json"), statusJson());
}

void startServer() {
  if (serverStarted) return;

  const char *user = OTA_WEB_USER;
  const char *pass = OTA_WEB_PASS;
  if (user[0] != '\0' && pass[0] != '\0') {
    httpUpdater.setup(&server, user, pass);
  } else {
    httpUpdater.setup(&server);
  }

  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/status", HTTP_GET, handleStatus);
  server.onNotFound([]() { server.send(404, F("text/plain"), F("not found")); });
  server.begin();
  serverStarted = true;
  Serial.println("[ota] web updater ready on port 80");
}

}  // namespace

namespace ota {

void begin() {
#if OTA_ENABLED
  startServer();
#endif
}

void startRescueAp() {
#if OTA_ENABLED
  if (rescueMode) return;

  const String ssid = rescueSsidValue();
  const char *password =
      (std::strlen(OTA_AP_PASSWORD) >= 8) ? OTA_AP_PASSWORD : nullptr;

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(ssid.c_str(), password);
  delay(100);

  rescueMode = true;
  startServer();

  Serial.printf("[ota] rescue AP: %s (%s)\n", ssid.c_str(),
                WiFi.softAPIP().toString().c_str());
#else
  (void)rescueMode;
#endif
}

void exitRescue() {
  if (!rescueMode) return;
  // AP だけ止める。WiFi.mode(WIFI_STA) を呼ぶと接続中の STA も切れて
  // 再接続ループに入るため、モードは AP_STA のままにしておく。
  WiFi.softAPdisconnect(true);
  rescueMode = false;
  Serial.println("[ota] rescue AP stopped");
}

bool inRescueMode() { return rescueMode; }

String rescueSsid() { return rescueSsidValue(); }

IPAddress rescueIp() { return WiFi.softAPIP(); }

void loop() {
#if OTA_ENABLED
  if (serverStarted) server.handleClient();
#endif
}

}  // namespace ota
