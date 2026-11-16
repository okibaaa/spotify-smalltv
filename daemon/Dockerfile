FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY daemon/pyproject.toml /app/pyproject.toml
COPY daemon/spotify_tv /app/spotify_tv

RUN pip install .

EXPOSE 8888

CMD ["spotify-tv-daemon"]
