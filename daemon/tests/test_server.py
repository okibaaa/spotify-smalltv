import time

from fastapi.testclient import TestClient

from spotify_tv.artwork import FRAME_BYTES, ArtCache
from spotify_tv.server import create_app
from spotify_tv.state import SharedState, TrackState


def make_client(
    art_wait_seconds: float = 0.0,
) -> tuple[TestClient, SharedState, ArtCache]:
    state = SharedState()
    cache = ArtCache()
    state.set(
        TrackState(
            playing=True,
            track_id="track-1",
            art_id="abc123",
            title="Test Song",
            artist="Test Artist",
            progress_ms=1000,
            duration_ms=200000,
            updated_at=time.monotonic(),
        )
    )
    cache.put("abc123", bytes(range(256)) * (FRAME_BYTES // 256))
    app = create_app(state, cache, art_wait_seconds=art_wait_seconds)
    return TestClient(app), state, cache


def test_health() -> None:
    client, _, _ = make_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_now() -> None:
    client, _, _ = make_client()
    body = client.get("/api/now").json()
    assert body["playing"] is True
    assert body["track_id"] == "track-1"
    assert body["art_id"] == "abc123"
    assert body["title"] == "Test Song"
    # 応答時点まで補間されるため、わずかに進んでいる
    assert 1000 <= body["progress_ms"] <= 1100
    assert body["duration_ms"] == 200000
    assert body["stale"] is False
    assert body["error"] is None
    assert "art_url" not in body


def test_now_reports_error() -> None:
    client, state, _ = make_client()
    state.set_error("SpotifyException")
    body = client.get("/api/now").json()
    assert body["error"] == "SpotifyException"


def test_art_frame() -> None:
    client, _, _ = make_client()
    response = client.get("/api/art/abc123.bin")
    assert response.status_code == 200
    assert len(response.content) == FRAME_BYTES
    assert response.headers["content-length"] == str(FRAME_BYTES)


def test_art_missing_returns_404_without_delay() -> None:
    client, _, _ = make_client(art_wait_seconds=0.0)
    started = time.monotonic()
    response = client.get("/api/art/unknown.bin")
    assert response.status_code == 404
    assert response.headers["retry-after"] == "1"
    assert time.monotonic() - started < 1.0
