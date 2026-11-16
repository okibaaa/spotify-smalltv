#include <Arduino.h>
#include <ESP8266WiFi.h>

#include <cstring>

#include "app_config.h"
#include "display.h"
#include "progress.h"
#include "spotify_client.h"
#include "types.h"

namespace {

enum class State {
  Boot,
  WifiError,
  ConnError,
  SpotifyError,
  ArtError,
  Idle,
  Playing,
};

State state = State::Boot;
NowPlaying now;
// 現在画面に描画済みのジャケット ID (空文字は未描画)
char drawnArtId[20] = {0};
// 曲の終端で即時ポーリングを 1 回だけ行うためのフラグ
bool endOfTrackPolled = false;
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
    case State::SpotifyError:
      display::showSpotifyError();
      break;
    case State::ArtError:
      display::showArtworkError();
      break;
    case State::Idle:
      display::showIdle();
      break;
    case State::Playing:
      break;
  }
}

void pollOnce() {
  NowPlaying fresh;
  if (!fetchNowPlaying(fresh)) {
    setState(State::ConnError);
    return;
  }

  // 曲が変わったら終端ポーリングのフラグを戻す
  if (std::strcmp(fresh.trackId, now.trackId) != 0) endOfTrackPolled = false;
  now = fresh;

  // デーモンは応答するが Spotify 側の情報が古い (認証切れ・API 障害)
  if (now.stale) {
    setState(State::SpotifyError);
    return;
  }

  if (!now.playing) {
    setState(State::Idle);
    return;
  }

  // ジャケットを描き直す必要があるのは、曲が変わったときと
  // 「Playing 以外の画面」(Idle/エラー復帰) から来たときだけ。
  const bool needArt =
      state != State::Playing || std::strcmp(now.artId, drawnArtId) != 0;
  if (!needArt) return;

  Serial.printf("[main] fetching art %s\n", now.artId);
  if (!fetchAndDrawArt(now.artId)) {
    // 次回ポーリングで再試行する (ここで ConnError にはしない)
    setState(State::ArtError);
    return;
  }

  strlcpy(drawnArtId, now.artId, sizeof(drawnArtId));
  const uint32_t drawnAtMs = millis();
  display::drawBaseBand();
  display::drawProgressBar(progressRatio(now, drawnAtMs));
  lastBarMs = drawnAtMs;
  state = State::Playing;
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
    pollOnce();
  }

  if (state == State::Playing) {
    const uint32_t position = currentPositionMs(now, nowMs);
    if (now.durationMs > 0 && position >= now.durationMs) {
      // 曲の終端に到達: 即座に取り直す。ただし同じ曲のまま何度も
      // ポーリングしないよう、1 曲につき 1 回だけにする。
      if (!endOfTrackPolled) {
        endOfTrackPolled = true;
        lastPollMs = nowMs - POLL_INTERVAL_MS;
      }
    } else {
      endOfTrackPolled = false;
    }

    if (nowMs - lastBarMs >= 1000) {
      lastBarMs = nowMs;
      display::drawProgressBar(progressRatio(now, nowMs));
      Serial.printf("[mem] free heap: %u\n", ESP.getFreeHeap());
    }
  }

  delay(10);
}
