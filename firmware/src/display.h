#pragma once

#include <TFT_eSPI.h>

namespace display {

extern TFT_eSPI tft;

void begin();
void setBacklight(uint8_t level);
void showBoot(const char *subtitle);
void showIdle();
void showError(const char *line);
void showSpotifyError();
void showArtworkError();
void showWifiError();
void showApInfo(const char *ssid, const char *ip);

// ジャケット下部の黒帯 + プログレスバー
void drawBaseBand();
void drawProgressBar(float ratio);

}  // namespace display
