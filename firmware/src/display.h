#pragma once

#include <TFT_eSPI.h>

namespace display {

extern TFT_eSPI tft;

void begin();
void setBacklight(uint8_t level);
void showBoot(const char *subtitle);
void showIdle();
void showError(const char *line);
void showWifiError();

// ジャケット下部の黒帯 + プログレスバー
void drawBaseBand();
void drawProgressBar(float ratio);

}  // namespace display
