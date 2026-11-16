from PIL import Image

from spotify_tv.artwork import FRAME_BYTES, SIZE, to_rgb565_le


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
