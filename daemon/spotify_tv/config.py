"""Environment-based configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_cache_path() -> str:
    return str(Path.home() / ".config" / "spotify-tv" / "credentials.json")


@dataclass(frozen=True)
class Config:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://127.0.0.1:8888/callback"
    cache_path: str = field(default_factory=_default_cache_path)
    host: str = "0.0.0.0"
    port: int = 8888
    poll_interval: float = 3.0
    scope: str = "user-read-currently-playing user-read-playback-state"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            client_id=os.environ.get("SPOTIFY_CLIENT_ID", ""),
            client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", ""),
            redirect_uri=os.environ.get(
                "SPOTIFY_REDIRECT_URI", cls.redirect_uri
            ),
            cache_path=os.environ.get("SPOTIFY_TV_CACHE") or _default_cache_path(),
            host=os.environ.get("SPOTIFY_TV_HOST", cls.host),
            port=int(os.environ.get("SPOTIFY_TV_PORT", cls.port)),
            poll_interval=float(
                os.environ.get("SPOTIFY_TV_POLL_INTERVAL", cls.poll_interval)
            ),
        )
