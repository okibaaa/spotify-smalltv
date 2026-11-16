"""Shared state between the Spotify poller and the HTTP server."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

# これ以上 /api/now が更新されていなければ「鮮度切れ」とみなす。
# デーモンのポーリング間隔 (既定 3 秒) の 5 倍を目安にしている。
STALE_AFTER_SECONDS = 15.0


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

    def public(
        self, now: float | None = None, stale_after: float = STALE_AFTER_SECONDS
    ) -> dict:
        """Device-facing JSON (art_url and timestamps stay internal)."""
        now = time.monotonic() if now is None else now

        # Spotify の progress_ms はポーリングした瞬間の値なので、
        # 応答時点までの経過を足してデバイス側の補間と基点を揃える。
        progress = self.progress_ms
        if self.playing and self.updated_at:
            progress += int(max(0.0, now - self.updated_at) * 1000)
        if self.duration_ms > 0:
            progress = min(progress, self.duration_ms)

        stale = bool(self.updated_at) and now - self.updated_at > stale_after

        return {
            "playing": self.playing,
            "track_id": self.track_id,
            "art_id": self.art_id,
            "title": self.title,
            "artist": self.artist,
            "progress_ms": progress,
            "duration_ms": self.duration_ms,
            "stale": stale,
        }


class SharedState:
    def __init__(self, stale_after_seconds: float = STALE_AFTER_SECONDS) -> None:
        self._lock = threading.Lock()
        self._track = TrackState(updated_at=time.monotonic())
        self._error: str | None = None
        self._stale_after = stale_after_seconds

    def set(self, track: TrackState, error: str | None = None) -> None:
        with self._lock:
            self._track = track
            self._error = error

    def set_error(self, error: str | None) -> None:
        """Record a poll failure without discarding the last known track."""
        with self._lock:
            self._error = error

    def _copy_locked(self) -> TrackState:
        # Return a shallow copy so callers cannot mutate shared state.
        t = self._track
        return TrackState(
            playing=t.playing,
            track_id=t.track_id,
            art_id=t.art_id,
            art_url=t.art_url,
            title=t.title,
            artist=t.artist,
            progress_ms=t.progress_ms,
            duration_ms=t.duration_ms,
            updated_at=t.updated_at,
        )

    def snapshot(self) -> TrackState:
        with self._lock:
            return self._copy_locked()

    def public_dict(self) -> dict:
        now = time.monotonic()
        with self._lock:
            track = self._copy_locked()
            error = self._error
        body = track.public(now, self._stale_after)
        # 直近のポーリング失敗理由。デバイスは stale=true を見てエラー画面にする。
        body["error"] = error
        return body
