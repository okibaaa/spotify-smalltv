"""Spotify OAuth helpers."""

from __future__ import annotations

from spotipy.oauth2 import SpotifyOAuth

from .config import Config


def build_oauth(cfg: Config) -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=cfg.client_id,
        client_secret=cfg.client_secret,
        redirect_uri=cfg.redirect_uri,
        scope=cfg.scope,
        cache_path=cfg.cache_path,
        open_browser=True,
    )


def main() -> None:
    """One-time interactive login (`spotify-tv-login`)."""
    cfg = Config.from_env()
    if not cfg.client_id or not cfg.client_secret:
        raise SystemExit(
            "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET を設定してください。"
        )

    oauth = build_oauth(cfg)
    token = oauth.get_access_token(as_dict=False, check_cache=False)
    if token:
        print("ログイン成功。トークンを保存しました:", cfg.cache_path)
    else:
        raise SystemExit("ログインに失敗しました。")


if __name__ == "__main__":
    main()
