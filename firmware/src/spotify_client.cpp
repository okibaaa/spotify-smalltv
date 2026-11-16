#include "spotify_client.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>

#include "app_config.h"
#include "display.h"

char httpError[96] = {0};

namespace {

void fail(const char *message) {
  strlcpy(httpError, message, sizeof(httpError));
  Serial.print("[http] ");
  Serial.println(message);
}

void copyString(char *dst, size_t cap, const char *src) {
  if (src == nullptr) src = "";
  strlcpy(dst, src, cap);
}

String apiUrl(const String &path) {
  return String("http://") + DAEMON_HOST + ":" + String(DAEMON_PORT) + path;
}

// stream から len バイト読み切る。deadline を過ぎたら false。
bool readExact(WiFiClient *stream, uint8_t *dst, size_t len, uint32_t deadline) {
  size_t done = 0;
  while (done < len) {
    if (stream->available() > 0) {
      int n = stream->read(dst + done, len - done);
      if (n > 0) {
        done += n;
        continue;
      }
    }
    if (!stream->connected()) {
      return false;
    }
    if (static_cast<int32_t>(millis() - deadline) >= 0) {
      return false;
    }
    delay(1);
  }
  return true;
}

}  // namespace

bool fetchNowPlaying(NowPlaying &out) {
  WiFiClient client;
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  const String url = apiUrl("/api/now");
  if (!http.begin(client, url)) {
    fail("begin failed");
    return false;
  }

  const int code = http.GET();
  if (code != HTTP_CODE_OK) {
    char msg[64];
    snprintf(msg, sizeof(msg), "GET /api/now -> %d", code);
    fail(msg);
    http.end();
    return false;
  }

  const String payload = http.getString();
  http.end();

  JsonDocument doc;
  const DeserializationError err = deserializeJson(doc, payload);
  if (err) {
    fail("invalid JSON from /api/now");
    return false;
  }

  out.playing = doc["playing"] | false;
  out.stale = doc["stale"] | false;
  copyString(out.trackId, sizeof(out.trackId), doc["track_id"] | "");
  copyString(out.artId, sizeof(out.artId), doc["art_id"] | "");
  copyString(out.title, sizeof(out.title), doc["title"] | "");
  copyString(out.artist, sizeof(out.artist), doc["artist"] | "");
  out.progressMs = doc["progress_ms"] | 0;
  out.durationMs = doc["duration_ms"] | 0;
  out.fetchedAtMs = millis();
  return true;
}

bool fetchAndDrawArt(const char *artId) {
  if (artId == nullptr || artId[0] == '\0') {
    fail("empty art_id");
    return false;
  }

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  const String url = apiUrl(String("/api/art/") + artId + ".bin");
  if (!http.begin(client, url)) {
    fail("art begin failed");
    return false;
  }

  const int code = http.GET();
  if (code != HTTP_CODE_OK) {
    char msg[64];
    snprintf(msg, sizeof(msg), "GET art -> %d", code);
    fail(msg);
    http.end();
    return false;
  }

  const int contentLength = http.getSize();
  if (contentLength != ART_FRAME_BYTES) {
    char msg[80];
    snprintf(msg, sizeof(msg), "art size %d != %d", contentLength,
             ART_FRAME_BYTES);
    fail(msg);
    http.end();
    return false;
  }

  WiFiClient *stream = http.getStreamPtr();
  if (stream == nullptr) {
    fail("no stream");
    http.end();
    return false;
  }

  // PC側はリトルエンディアンの RGB565 を送る。
  // ESP8266 もリトルエンディアンなので、そのまま uint16_t として読める。
  static uint16_t row[ART_WIDTH];
  const uint32_t frameDeadline = millis() + 20000;
  const uint32_t startMs = millis();

  for (int y = 0; y < ART_HEIGHT; y++) {
    if (static_cast<int32_t>(millis() - frameDeadline) >= 0) {
      fail("art frame timeout");
      http.end();
      return false;
    }
    const uint32_t rowDeadline = millis() + 2000;
    if (!readExact(stream, reinterpret_cast<uint8_t *>(row), ART_ROW_BYTES,
                   rowDeadline)) {
      fail("art read timeout");
      http.end();
      return false;
    }
    display::tft.pushImage(0, y, ART_WIDTH, 1, row);
  }

  http.end();
  Serial.printf("[art] drawn %s in %lu ms\n", artId,
                static_cast<unsigned long>(millis() - startMs));
  return true;
}
