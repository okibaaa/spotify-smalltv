#pragma once

#include "types.h"

// /api/now を取得して out を更新する。成功したら true。
bool fetchNowPlaying(NowPlaying &out);

// /api/art/{artId}.bin を取得し、1行ずつ ST7789 に描画する。
bool fetchAndDrawArt(const char *artId);

// 直近の HTTP エラー内容 (シリアルログ用)
extern char httpError[96];
