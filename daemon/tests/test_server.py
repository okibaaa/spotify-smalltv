from fastapi.testclient import TestClient

from spotify_tv.artwork import FRAME_BYTES, ArtCache
from spotify_tv.server import create_app
from spotify_tv.state import SharedState, TrackState


def make_client() -> tuple[TestClient, SharedState, ArtCache]:
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
        )
    )
    cache.put("abc123", bytes(range(256)) * (FRAME_BYTES // 256))
    return TestClient(create_app(state, cache)), state, cache


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
    assert body["progress_ms"] == 1000
    assert "art_url" not in body


def test_art_frame() -> None:
    client, _, _ = make_client()
    response = client.get("/api/art/abc123.bin")
    assert response.status_code == 200
    assert len(response.content) == FRAME_BYTES
    assert response.headers["content-length"] == str(FRAME_BYTES)


def test_art_missing_times_out() -> None:
    client, _, _ = make_client()
    # 404 を返すまで最大5秒待つ実装なので、ここでは存在しないIDで検証
    response = client.get("/api/art/unknown.bin")
    assert response.status_code == 404
