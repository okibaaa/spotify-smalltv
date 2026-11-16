"""Background Spotify polling thread."""

from __future__ import annotations

import logging
import threading
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from .artwork import (
    PLACEHOLDER_ID,
    ArtCache,
    art_id_for,
    download_rgb565,
    placeholder_frame,
)
from .state import SharedState, TrackState

log = logging.getLogger(__name__)

# アート取得失敗時の再試行バックオフ (秒)
ART_RETRY_BASE_SECONDS = 5.0
ART_RETRY_MAX_SECONDS = 60.0


class Poller(threading.Thread):
    def __init__(
        self,
        oauth: SpotifyOAuth | None,
        state: SharedState,
        cache: ArtCache,
        interval: float = 3.0,
        client: object | None = None,
    ) -> None:
        super().__init__(daemon=True, name="spotify-poller")
        self._sp = client or spotipy.Spotify(
            auth_manager=oauth, requests_timeout=10, retries=1
        )
        self._state = state
        self._cache = cache
        self._interval = interval
        self._stop_event = threading.Event()
        self._art_failures: dict[str, int] = {}
        self._art_retry_at: dict[str, float] = {}

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        log.info("Spotify poller started (interval=%.1fs)", self._interval)
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as exc:
                # keep the daemon alive on transient errors, but surface them
                # via /api/now so the display can show an error screen.
                log.exception("Spotify poll failed")
                self._state.set_error(type(exc).__name__)
            self._stop_event.wait(self._interval)

    def tick(self) -> None:
        playback = self._sp.current_user_playing_track(
            additional_types=("track", "episode")
        )
        if not playback or not playback.get("item"):
            self._state.set(
                TrackState(playing=False, updated_at=time.monotonic())
            )
            return

        item = playback["item"]
        art_url, artist = _describe_item(item)
        art_id = art_id_for(art_url) if art_url else PLACEHOLDER_ID

        track = TrackState(
            playing=bool(playback.get("is_playing")),
            track_id=item.get("id"),
            art_id=art_id,
            art_url=art_url,
            title=item.get("name", ""),
            artist=artist,
            progress_ms=int(playback.get("progress_ms") or 0),
            duration_ms=int(item.get("duration_ms") or 0),
            updated_at=time.monotonic(),
        )

        # Publish metadata first so /api/now never blocks on artwork.
        self._state.set(track)

        self._ensure_art(art_id, art_url)

    def _ensure_art(self, art_id: str, art_url: str | None) -> None:
        if self._cache.get(art_id) is not None:
            return

        retry_at = self._art_retry_at.get(art_id)
        if retry_at is not None and time.monotonic() < retry_at:
            return

        try:
            frame = download_rgb565(art_url) if art_url else placeholder_frame()
        except Exception:
            failures = self._art_failures.get(art_id, 0) + 1
            delay = min(
                ART_RETRY_MAX_SECONDS, ART_RETRY_BASE_SECONDS * 2 ** (failures - 1)
            )
            self._art_failures[art_id] = failures
            self._art_retry_at[art_id] = time.monotonic() + delay
            log.warning(
                "artwork download failed (%d times), retry in %.0fs: %s",
                failures,
                delay,
                art_url,
                exc_info=True,
            )
            return

        self._cache.put(art_id, frame)
        self._art_failures.pop(art_id, None)
        self._art_retry_at.pop(art_id, None)
        log.debug("artwork cached: %s", art_id)


def _describe_item(item: dict) -> tuple[str | None, str]:
    """Return (largest image URL, artist name) for a track or episode."""
    if item.get("type") == "episode":
        images = item.get("images") or []
        artist = (item.get("show") or {}).get("name", "")
    else:
        images = (item.get("album") or {}).get("images") or []
        artist = ", ".join(
            a.get("name", "") for a in item.get("artists", []) if a.get("name")
        )

    url = next((image.get("url") for image in images if image.get("url")), None)
    return url, artist
