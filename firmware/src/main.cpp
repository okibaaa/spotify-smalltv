#include <Arduino.h>
#include <ESP8266WiFi.h>

#include <cstring>

#include "app_config.h"
#include "display.h"
#include "progress.h"
#include "spotify_client.h"
#include "types.h"

namespace {

enum class State { Boot, WifiError, ConnError, Idle, Playing };

State state = State::Boot;
NowPlaying now;
uint32_t lastPollMs = 0;
uint32_t lastBarMs = 0;
uint32_t lastWifiRetryMs = 0;

void setState(State next) {
  if (state == next) return;
  state = next;
  switch (next) {
    case State::Boot:
      display::showBoot("Starting...");
      break;
    case State::WifiError:
      display::showWifiError();
      break;
    case State::ConnError:
      display::showError("Daemon unreachable");
      break;
    case State::Idle:
      display::showIdle();
      break;
    case State::Playing:
      break;
  }
}

void pollOnce(uint32_t nowMs) {
  NowPlaying fresh;
  if (!fetchNowPlaying(fresh)) {
    setState(State::ConnError);
    return;
  }

  const bool trackChanged =
      !now.valid || std::strcmp(fresh.trackId, now.trackId) != 0 ||
      std::strcmp(fresh.artId, now.artId) != 0;

  now = fresh;
  now.valid = true;

  if (!now.playing) {
    setState(State::Idle);
    return;
  }

  // 曲が変わった、または停止状態から復帰したときだけ画像を取り直す。
  if (trackChanged || state != State::Playing) {
    if (state == State::Boot || state == State::ConnError) {
      display::showBoot("Loading artwork...");
    }

    Serial.printf("[main] fetching art %s\n", now.artId);
    if (!fetchAndDrawArt(now.artId)) {
      setState(State::ConnError);
      return;
    }

    display::drawBaseBand();
    display::drawProgressBar(progressRatio(now, now.fetchedAtMs));
    lastBarMs = now.fetchedAtMs;
    state = State::Playing;
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("=== Spotify SmallTV-Ultra ===");

  display::begin();
  display::showBoot("Connecting Wi-Fi");

  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(100);
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[wifi] connected: %s\n", WiFi.localIP().toString().c_str());
    display::showBoot("Contacting daemon...");
    state = State::Boot;
  } else {
    Serial.println("[wifi] connection failed");
    state = State::WifiError;
    display::showWifiError();
  }

  lastWifiRetryMs = millis();
  lastPollMs = millis() - POLL_INTERVAL_MS;
}

void loop() {
  const uint32_t nowMs = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (state != State::WifiError) {
      setState(State::WifiError);
    }
    if (nowMs - lastWifiRetryMs >= WIFI_RETRY_MS) {
      lastWifiRetryMs = nowMs;
      Serial.println("[wifi] reconnecting...");
      WiFi.reconnect();
    }
    delay(50);
    return;
  }

  if (state == State::WifiError) {
    Serial.printf("[wifi] reconnected: %s\n", WiFi.localIP().toString().c_str());
    setState(State::Boot);
    lastPollMs = nowMs - POLL_INTERVAL_MS;
  }

  if (nowMs - lastPollMs >= POLL_INTERVAL_MS) {
    lastPollMs = nowMs;
    pollOnce(nowMs);
  }

  if (state == State::Playing) {
    const uint32_t position = currentPositionMs(now, nowMs);
    if (now.durationMs > 0 && position >= now.durationMs) {
      // 曲の終端に到達: 次のループで即座に取り直す
      lastPollMs = nowMs - POLL_INTERVAL_MS;
    }

    if (nowMs - lastBarMs >= 1000) {
      lastBarMs = nowMs;
      display::drawProgressBar(progressRatio(now, nowMs));
      Serial.printf("[mem] free heap: %u\n", ESP.getFreeHeap());
    }
  }

  delay(10);
}
