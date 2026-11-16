import time

from PIL import Image

from spotify_tv.artwork import (
    FRAME_BYTES,
    SIZE,
    ArtCache,
    placeholder_frame,
    to_rgb565_le,
)


def test_frame_size() -> None:
    data = to_rgb565_le(Image.new("RGB", (10, 10), (255, 0, 0)))
    assert len(data) == FRAME_BYTES == SIZE * SIZE * 2


def test_little_endian_red() -> None:
    data = to_rgb565_le(Image.new("RGB", (10, 10), (255, 0, 0)))
    value = data[0] | (data[1] << 8)
    assert value == 0xF800


def test_white_and_black() -> None:
    white = to_rgb565_le(Image.new("RGB", (8, 8), (255, 255, 255)))
    black = to_rgb565_le(Image.new("RGB", (8, 8), (0, 0, 0)))
    assert (white[0] | (white[1] << 8)) == 0xFFFF
    assert (black[0] | (black[1] << 8)) == 0x0000


def test_placeholder_is_spotify_green() -> None:
    data = placeholder_frame()
    assert len(data) == FRAME_BYTES
    value = data[0] | (data[1] << 8)
    assert value == 0x1DCA  # #1DB954


def test_wait_for_returns_cached_frame() -> None:
    cache = ArtCache()
    cache.put("art", b"\x00" * FRAME_BYTES)
    assert cache.wait_for("art", timeout=1.0) is not None


def test_wait_for_times_out() -> None:
    cache = ArtCache()
    started = time.monotonic()
    assert cache.wait_for("missing", timeout=0.1) is None
    assert time.monotonic() - started >= 0.1
