"""HTTP API consumed by the ESP8266 firmware."""

from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response

from .artwork import FRAME_BYTES, ArtCache
from .state import SharedState

NO_STORE = {"Cache-Control": "no-store"}


def create_app(state: SharedState, cache: ArtCache) -> FastAPI:
    app = FastAPI(title="Spotify SmallTV daemon", version="0.1.0")

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
        deadline = time.monotonic() + 5.0
        while True:
            data = cache.get(art_id)
            if data is not None:
                return Response(
                    content=data,
                    media_type="application/octet-stream",
                    headers={
                        **NO_STORE,
                        "Content-Length": str(FRAME_BYTES),
                    },
                )
            if time.monotonic() >= deadline:
                raise HTTPException(status_code=404, detail="artwork not ready")
            time.sleep(0.1)

    @app.get("/")
    def index() -> dict:
        track = state.public_dict()
        return {
            "service": "spotify-smalltv-daemon",
            "endpoints": ["/api/health", "/api/now", "/api/art/{art_id}.bin"],
            "track": track,
        }

    return app
