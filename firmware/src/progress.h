#pragma once

#include <stdint.h>

#include "types.h"

// デーモン取得時点の progress に、取得からの経過時間を加算して現在位置を返す。
inline uint32_t currentPositionMs(const NowPlaying &now, uint32_t nowMs) {
  uint32_t pos = now.progressMs;
  if (now.playing) {
    pos += nowMs - now.fetchedAtMs;
  }
  if (now.durationMs > 0 && pos > now.durationMs) {
    pos = now.durationMs;
  }
  return pos;
}

inline float progressRatio(const NowPlaying &now, uint32_t nowMs) {
  if (now.durationMs == 0) {
    return 0.0f;
  }
  float ratio = static_cast<float>(currentPositionMs(now, nowMs)) /
                static_cast<float>(now.durationMs);
  if (ratio < 0.0f) ratio = 0.0f;
  if (ratio > 1.0f) ratio = 1.0f;
  return ratio;
}
