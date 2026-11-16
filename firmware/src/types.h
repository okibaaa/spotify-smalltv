#pragma once

#include <stdint.h>

#define ART_WIDTH 240
#define ART_HEIGHT 240
#define ART_ROW_BYTES (ART_WIDTH * 2)
#define ART_FRAME_BYTES (ART_WIDTH * ART_HEIGHT * 2)

// /api/now のスナップショット
struct NowPlaying {
  bool valid = false;
  bool playing = false;
  char trackId[48] = {0};
  char artId[20] = {0};
  char title[96] = {0};
  char artist[96] = {0};
  uint32_t progressMs = 0;
  uint32_t durationMs = 0;
  uint32_t fetchedAtMs = 0;
};
