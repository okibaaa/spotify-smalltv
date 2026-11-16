"""Shared state between the Spotify poller and the HTTP server."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class TrackState:
    playing: bool = False
    track_id: str | None = None
    art_id: str | None = None
    art_url: str | None = None
    title: str = ""
    artist: str = ""
    progress_ms: int = 0
    duration_ms: int = 0
    updated_at: float = 0.0

    def public(self) -> dict:
        """Device-facing JSON (art_url and timestamps stay internal)."""
        return {
            "playing": self.playing,
            "track_id": self.track_id,
            "art_id": self.art_id,
            "title": self.title,
            "artist": self.artist,
            "progress_ms": self.progress_ms,
            "duration_ms": self.duration_ms,
        }


class SharedState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._track = TrackState(updated_at=time.monotonic())

    def set(self, track: TrackState) -> None:
        with self._lock:
            self._track = track

    def snapshot(self) -> TrackState:
        with self._lock:
            # Return a shallow copy so callers cannot mutate shared state.
            return TrackState(
                playing=self._track.playing,
                track_id=self._track.track_id,
                art_id=self._track.art_id,
                art_url=self._track.art_url,
                title=self._track.title,
                artist=self._track.artist,
                progress_ms=self._track.progress_ms,
                duration_ms=self._track.duration_ms,
                updated_at=self._track.updated_at,
            )

    def public_dict(self) -> dict:
        return self.snapshot().public()
