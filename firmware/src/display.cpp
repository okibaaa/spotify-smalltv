#include "display.h"

#include <Arduino.h>

#include "app_config.h"

namespace {
constexpr uint16_t kSpotifyGreen = 0x1DCA;  // #1DB954 を RGB565 に変換した値
constexpr int kScreen = 240;

// プログレスバー配置
constexpr int kBandY = 226;
constexpr int kBandH = 14;
constexpr int kBarX = 4;
constexpr int kBarY = 231;
constexpr int kBarW = 232;
constexpr int kBarH = 4;
constexpr uint16_t kBarTrack = 0x2104;  // 暗いグレー

void drawLogo(int cx, int cy, int radius) {
  display::tft.fillCircle(cx, cy, radius, kSpotifyGreen);
  // Spotify ロゴ風の3本ライン
  for (int i = 0; i < 3; i++) {
    int w = radius + 6 - i * 7;
    int y = cy - 7 + i * 7;
    display::tft.fillRoundRect(cx - w / 2, y, w, 3, 2, TFT_BLACK);
  }
}

void drawCentered(const char *text, int y, uint8_t font, uint16_t color) {
  display::tft.setTextFont(font);
  display::tft.setTextSize(1);
  display::tft.setTextColor(color, TFT_BLACK);
  display::tft.setTextDatum(MC_DATUM);
  display::tft.drawString(text, kScreen / 2, y);
}

void drawHeader(const char *subtitle) {
  display::tft.fillScreen(TFT_BLACK);
  drawLogo(kScreen / 2, 82, 30);
  drawCentered("Spotify TV", 132, 4, TFT_WHITE);
  if (subtitle && subtitle[0]) {
    drawCentered(subtitle, 162, 2, TFT_LIGHTGREY);
  }
}

void drawErrorScreen(const char *title, const char *line) {
  display::tft.fillScreen(TFT_BLACK);
  drawCentered(title, 90, 4, TFT_ORANGE);
  if (line && line[0]) {
    drawCentered(line, 128, 2, TFT_LIGHTGREY);
  }
  drawCentered("Retrying...", 156, 2, TFT_DARKGREY);
}
}  // namespace

TFT_eSPI display::tft = TFT_eSPI();

namespace display {

void begin() {
  tft.init();
  tft.setRotation(0);
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(MC_DATUM);

  pinMode(BACKLIGHT_PIN, OUTPUT);
  analogWriteRange(255);
  setBacklight(BACKLIGHT_LEVEL);
}

void setBacklight(uint8_t level) {
  const uint8_t duty = BACKLIGHT_INVERTED ? (uint8_t)(255 - level) : level;
  analogWrite(BACKLIGHT_PIN, duty);
}

void showBoot(const char *subtitle) { drawHeader(subtitle); }

void showIdle() { drawHeader("Not playing"); }

void showError(const char *line) { drawErrorScreen("Connection error", line); }

void showSpotifyError() {
  drawErrorScreen("Spotify error", "Check daemon log");
}

void showArtworkError() {
  drawErrorScreen("Artwork error", "Retrying image download");
}

void showWifiError() {
  tft.fillScreen(TFT_BLACK);
  drawCentered("Wi-Fi error", 90, 4, TFT_ORANGE);
  drawCentered("Check config.h", 128, 2, TFT_LIGHTGREY);
  drawCentered("Retrying...", 156, 2, TFT_DARKGREY);
}

void drawBaseBand() { tft.fillRect(0, kBandY, kScreen, kBandH, TFT_BLACK); }

void drawProgressBar(float ratio) {
  if (ratio < 0.0f) ratio = 0.0f;
  if (ratio > 1.0f) ratio = 1.0f;

  tft.fillRect(0, kBandY, kScreen, kBandH, TFT_BLACK);
  tft.fillRect(kBarX, kBarY, kBarW, kBarH, kBarTrack);

  const int filled = static_cast<int>(ratio * kBarW + 0.5f);
  if (filled > 0) {
    tft.fillRect(kBarX, kBarY, filled, kBarH, kSpotifyGreen);
  }
}

}  // namespace display
