"""Album artwork download and RGB565 conversion.

The device expects exactly one 240x240 frame of little-endian RGB565
(115,200 bytes). Little-endian matches the ESP8266's native uint16_t
layout, so the firmware can stream rows directly into TFT_eSPI.
"""

from __future__ import annotations

import hashlib
import io
import threading
import time
from collections import OrderedDict

import requests
from PIL import Image

SIZE = 240
FRAME_BYTES = SIZE * SIZE * 2

# ジャケットの無い曲 (ローカルファイル等) 用の固定 art_id。
PLACEHOLDER_ID = "no-art"
_PLACEHOLDER_RGB = (29, 185, 84)  # #1DB954 (Spotify green)


def art_id_for(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def to_rgb565_le(image: Image.Image) -> bytes:
    """Resize to 240x240 and encode as little-endian RGB565."""
    img = image.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    pixels = img.load()
    buf = bytearray(FRAME_BYTES)
    i = 0
    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b = pixels[x, y]
            value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf[i] = value & 0xFF
            buf[i + 1] = (value >> 8) & 0xFF
            i += 2
    return bytes(buf)


def placeholder_frame() -> bytes:
    """Solid Spotify-green frame served when a track has no artwork."""
    return to_rgb565_le(Image.new("RGB", (SIZE, SIZE), _PLACEHOLDER_RGB))


def download_rgb565(url: str, timeout: float = 10.0) -> bytes:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    with Image.open(io.BytesIO(response.content)) as image:
        return to_rgb565_le(image)


class ArtCache:
    """Small LRU cache of converted frames."""

    def __init__(self, max_items: int = 3) -> None:
        self._max_items = max_items
        self._cond = threading.Condition()
        self._items: "OrderedDict[str, bytes]" = OrderedDict()

    def _get_locked(self, art_id: str) -> bytes | None:
        data = self._items.get(art_id)
        if data is not None:
            self._items.move_to_end(art_id)
        return data

    def get(self, art_id: str) -> bytes | None:
        with self._cond:
            return self._get_locked(art_id)

    def wait_for(self, art_id: str, timeout: float) -> bytes | None:
        """Return the frame, waiting up to `timeout` for the poller to fetch it."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                data = self._get_locked(art_id)
                if data is not None:
                    return data
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(remaining)

    def put(self, art_id: str, data: bytes) -> None:
        if len(data) != FRAME_BYTES:
            raise ValueError(f"frame must be {FRAME_BYTES} bytes, got {len(data)}")
        with self._cond:
            self._items[art_id] = data
            self._items.move_to_end(art_id)
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)
            self._cond.notify_all()
