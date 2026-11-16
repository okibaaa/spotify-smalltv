"""Daemon entry point: `spotify-tv-daemon`."""

from __future__ import annotations

import argparse
import logging

import uvicorn

from .artwork import ArtCache
from .auth import build_oauth
from .config import Config
from .demo import DemoPoller
from .poller import Poller
from .server import create_app
from .state import SharedState


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Spotify now-playing bridge for GeekMagic SmallTV-Ultra"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Spotify を使わずダミーの曲とジャケットを配信する",
    )
    parser.add_argument("--host", default=None, help="リッスンアドレス")
    parser.add_argument("--port", type=int, default=None, help="ポート")
    parser.add_argument(
        "--log-level", default="info", help="uvicorn のログレベル"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.log_level == "debug" else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = Config.from_env()
    state = SharedState()
    cache = ArtCache()

    if args.demo:
        poller: Poller | DemoPoller = DemoPoller(state, cache)
        logging.info("Demo mode: no Spotify credentials required")
    else:
        if not cfg.client_id or not cfg.client_secret:
            parser.error(
                "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET を設定するか、"
                "--demo を指定してください"
            )
        poller = Poller(
            build_oauth(cfg), state, cache, interval=cfg.poll_interval
        )

    poller.start()

    app = create_app(state, cache)
    uvicorn.run(
        app,
        host=args.host or cfg.host,
        port=args.port or cfg.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
