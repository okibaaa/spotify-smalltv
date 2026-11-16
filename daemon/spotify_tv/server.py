"""HTTP API consumed by the ESP8266 firmware."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .artwork import FRAME_BYTES, ArtCache
from .state import SharedState

NO_STORE = {"Cache-Control": "no-store"}

# デバイスの HTTP タイムアウト (4 秒) より短くする。
# 間に合わなければ 404 を返し、次のポーリングで取り直してもらう。
DEFAULT_ART_WAIT_SECONDS = 2.0


def create_app(
    state: SharedState,
    cache: ArtCache,
    art_wait_seconds: float = DEFAULT_ART_WAIT_SECONDS,
) -> FastAPI:
    app = FastAPI(title="Spotify SmallTV daemon", version="0.1.0")

    # ブラウザ用シミュレーター
    # (https://github.com/okibaaa/spotify-smalltv-simulator) は別オリジンから
    # /api/* を読むため CORS を許可する。認証情報を扱わない読み取り専用の
    # API なので、オリジンは制限しない。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
        max_age=600,
    )

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/api/now")
    def now() -> JSONResponse:
        return JSONResponse(state.public_dict(), headers=NO_STORE)

    @app.get("/api/art/{art_id}.bin")
    def art(art_id: str) -> Response:
        # The firmware asks for artwork immediately after /api/now, so wait
        # briefly for the poller's prefetch instead of returning 404.
        data = cache.wait_for(art_id, timeout=art_wait_seconds)
        if data is None:
            raise HTTPException(
                status_code=404,
                detail="artwork not ready",
                headers={"Retry-After": "1", **NO_STORE},
            )
        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={
                **NO_STORE,
                "Content-Length": str(FRAME_BYTES),
            },
        )

    @app.get("/")
    def index() -> dict:
        track = state.public_dict()
        return {
            "service": "spotify-smalltv-daemon",
            "endpoints": ["/api/health", "/api/now", "/api/art/{art_id}.bin"],
            "track": track,
        }

    return app
