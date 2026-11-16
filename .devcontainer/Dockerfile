FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl usbutils udev \
    && rm -rf /var/lib/apt/lists/*

# PlatformIO (ファームウェア) と esptool (手動書き込み)
RUN pip install --no-cache-dir platformio esptool
