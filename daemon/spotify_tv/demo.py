"""Demo poller: fake tracks and generated artwork, no Spotify account needed."""

from __future__ import annotations

import threading
import time

from PIL import Image

from .artwork import SIZE, ArtCache, to_rgb565_le
from .state import SharedState, TrackState

TRACK_SECONDS = 30


def make_demo_art(index: int) -> Image.Image:
    """Diagonal hue gradient that changes every track."""
    img = Image.new("RGB", (SIZE, SIZE))
    pixels = img.load()
    shift = (index * 57) % 256
    for y in range(SIZE):
        for x in range(SIZE):
            r = (x * 255) // SIZE
            g = (y * 255) // SIZE
            b = shift
            pixels[x, y] = (r, g, b)
    return img


class DemoPoller(threading.Thread):
    def __init__(self, state: SharedState, cache: ArtCache) -> None:
        super().__init__(daemon=True, name="demo-poller")
        self._state = state
        self._cache = cache
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        index = 0
        track_start = time.monotonic()

        while not self._stop_event.is_set():
            elapsed = time.monotonic() - track_start
            if elapsed >= TRACK_SECONDS:
                index += 1
                track_start = time.monotonic()
                elapsed = 0.0

            art_id = f"demo{index % 1000:04d}"
            if self._cache.get(art_id) is None:
                self._cache.put(art_id, to_rgb565_le(make_demo_art(index)))

            self._state.set(
                TrackState(
                    playing=True,
                    track_id=f"demo-track-{index}",
                    art_id=art_id,
                    art_url=None,
                    title=f"Demo Track {index + 1}",
                    artist="Demo Artist",
                    progress_ms=int(elapsed * 1000),
                    duration_ms=TRACK_SECONDS * 1000,
                    updated_at=time.monotonic(),
                )
            )
            self._stop_event.wait(1.0)
