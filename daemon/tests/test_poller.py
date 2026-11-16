import time

import pytest

import spotify_tv.poller as poller_module
from spotify_tv.artwork import FRAME_BYTES, PLACEHOLDER_ID, ArtCache
from spotify_tv.poller import Poller
from spotify_tv.state import SharedState


class FakeSpotify:
    def __init__(self, playback: dict | None) -> None:
        self.playback = playback
        self.kwargs: dict | None = None

    def current_user_playing_track(self, **kwargs: object) -> dict | None:
        self.kwargs = kwargs
        return self.playback


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Never hit i.scdn.co from tests; record requested URLs instead."""
    requested: list[str] = []

    def fake_download(url: str) -> bytes:
        requested.append(url)
        return b"\x01" * FRAME_BYTES

    monkeypatch.setattr(poller_module, "download_rgb565", fake_download)
    return requested


def make_poller(
    playback: dict | None,
) -> tuple[Poller, SharedState, ArtCache, FakeSpotify]:
    state = SharedState()
    cache = ArtCache()
    client = FakeSpotify(playback)
    return Poller(None, state, cache, client=client), state, cache, client


def track_playback(images: list[dict] | None = None) -> dict:
    return {
        "is_playing": True,
        "progress_ms": 12345,
        "item": {
            "type": "track",
            "id": "track-1",
            "name": "Song",
            "duration_ms": 200000,
            "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
            "album": {
                "images": images
                if images is not None
                else [{"url": "https://i.scdn.co/large"}]
            },
        },
    }


def test_publishes_track_metadata(no_network: list[str]) -> None:
    poller, state, cache, client = make_poller(track_playback())
    poller.tick()

    body = state.public_dict()
    assert body["playing"] is True
    assert body["track_id"] == "track-1"
    assert body["title"] == "Song"
    assert body["artist"] == "Artist A, Artist B"
    assert body["duration_ms"] == 200000
    assert 12345 <= body["progress_ms"] <= 12500
    assert client.kwargs == {"additional_types": ("track", "episode")}
    assert no_network == ["https://i.scdn.co/large"]
    assert cache.get(body["art_id"]) is not None


def test_successful_poll_clears_previous_error() -> None:
    poller, state, _, _ = make_poller(track_playback())
    state.set_error("SpotifyException")
    poller.tick()
    assert state.public_dict()["error"] is None


def test_episode_uses_show_name_and_images() -> None:
    playback = {
        "is_playing": True,
        "progress_ms": 0,
        "item": {
            "type": "episode",
            "id": "episode-1",
            "name": "Episode",
            "duration_ms": 3600000,
            "images": [{"url": "https://i.scdn.co/episode"}],
            "show": {"name": "Show"},
        },
    }
    poller, state, cache, _ = make_poller(playback)
    poller.tick()

    body = state.public_dict()
    assert body["title"] == "Episode"
    assert body["artist"] == "Show"
    assert cache.get(body["art_id"]) is not None


def test_track_without_artwork_uses_placeholder(no_network: list[str]) -> None:
    poller, state, cache, _ = make_poller(track_playback(images=[]))
    poller.tick()

    body = state.public_dict()
    assert body["art_id"] == PLACEHOLDER_ID
    assert cache.get(PLACEHOLDER_ID) is not None
    assert no_network == []


def test_no_playback_publishes_idle_state() -> None:
    poller, state, _, _ = make_poller(None)
    poller.tick()

    body = state.public_dict()
    assert body["playing"] is False
    assert body["art_id"] is None


def test_artwork_failure_backs_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def failing_download(url: str) -> bytes:
        calls.append(url)
        raise RuntimeError("cdn down")

    monkeypatch.setattr(poller_module, "download_rgb565", failing_download)
    poller, state, cache, _ = make_poller(track_playback())

    poller.tick()
    poller.tick()

    art_id = state.public_dict()["art_id"]
    assert art_id is not None
    assert cache.get(art_id) is None
    # 2 回目はバックオフ中なので再取得しない
    assert calls == ["https://i.scdn.co/large"]
    assert poller._art_retry_at[art_id] > time.monotonic()
