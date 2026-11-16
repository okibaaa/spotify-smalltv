import time

from spotify_tv.state import STALE_AFTER_SECONDS, SharedState, TrackState


def test_progress_is_interpolated_at_response_time() -> None:
    now = time.monotonic()
    track = TrackState(
        playing=True,
        progress_ms=1000,
        duration_ms=200000,
        updated_at=now - 2.0,
    )
    assert 2900 <= track.public(now)["progress_ms"] <= 3100


def test_progress_stops_at_duration() -> None:
    now = time.monotonic()
    track = TrackState(
        playing=True,
        progress_ms=199800,
        duration_ms=200000,
        updated_at=now - 5.0,
    )
    assert track.public(now)["progress_ms"] == 200000


def test_paused_track_does_not_advance() -> None:
    now = time.monotonic()
    track = TrackState(
        playing=False,
        progress_ms=1000,
        duration_ms=200000,
        updated_at=now - 5.0,
    )
    assert track.public(now)["progress_ms"] == 1000


def test_track_without_duration_has_no_ceiling() -> None:
    now = time.monotonic()
    track = TrackState(playing=True, progress_ms=0, duration_ms=0, updated_at=now - 1.0)
    assert track.public(now)["progress_ms"] >= 900


def test_stale_after_threshold() -> None:
    now = time.monotonic()
    fresh = TrackState(updated_at=now)
    old = TrackState(updated_at=now - STALE_AFTER_SECONDS - 1.0)
    assert fresh.public(now)["stale"] is False
    assert old.public(now)["stale"] is True


def test_error_is_cleared_by_next_successful_poll() -> None:
    state = SharedState()
    state.set_error("SpotifyException")
    assert state.public_dict()["error"] == "SpotifyException"

    state.set(TrackState(playing=False, updated_at=time.monotonic()))
    body = state.public_dict()
    assert body["error"] is None
    assert body["stale"] is False
