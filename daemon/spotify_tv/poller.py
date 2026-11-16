"""Background Spotify polling thread."""

from __future__ import annotations

import logging
import threading
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from .artwork import ArtCache, art_id_for, download_rgb565
from .state import SharedState, TrackState

log = logging.getLogger(__name__)


class Poller(threading.Thread):
    def __init__(
        self,
        oauth: SpotifyOAuth,
        state: SharedState,
        cache: ArtCache,
        interval: float = 3.0,
    ) -> None:
        super().__init__(daemon=True, name="spotify-poller")
        self._sp = spotipy.Spotify(
            auth_manager=oauth, requests_timeout=10, retries=1
        )
        self._state = state
        self._cache = cache
        self._interval = interval
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        log.info("Spotify poller started (interval=%.1fs)", self._interval)
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception:  # keep the daemon alive on transient errors
                log.exception("Spotify poll failed")
            self._stop_event.wait(self._interval)

    def tick(self) -> None:
        playback = self._sp.current_user_playing_track()
        if not playback or not playback.get("item"):
            self._state.set(
                TrackState(playing=False, updated_at=time.monotonic())
            )
            return

        item = playback["item"]
        album = item.get("album") or {}
        images = album.get("images") or []
        art_url = images[0]["url"] if images else None
        art_id = art_id_for(art_url) if art_url else None

        track = TrackState(
            playing=bool(playback.get("is_playing")),
            track_id=item.get("id"),
            art_id=art_id,
            art_url=art_url,
            title=item.get("name", ""),
            artist=", ".join(
                artist.get("name", "")
                for artist in item.get("artists", [])
                if artist.get("name")
            ),
            progress_ms=int(playback.get("progress_ms") or 0),
            duration_ms=int(item.get("duration_ms") or 0),
            updated_at=time.monotonic(),
        )

        # Publish metadata first so /api/now never blocks on artwork.
        self._state.set(track)

        if art_id and self._cache.get(art_id) is None and art_url:
            try:
                self._cache.put(art_id, download_rgb565(art_url))
                log.debug("artwork cached: %s", art_id)
            except Exception:
                log.warning("artwork download failed: %s", art_url, exc_info=True)
