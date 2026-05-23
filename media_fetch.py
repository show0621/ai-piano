"""下載直接音檔連結（.mp3 / .wav 等），不支援串流平台。"""

from __future__ import annotations

import os
import urllib.request
from urllib.parse import urlparse

DIRECT_AUDIO_EXTENSIONS = (
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus", ".webm",
)

BLOCKED_HOSTS = (
    "youtube.com",
    "youtu.be",
    "music.youtube.com",
    "m.youtube.com",
    "spotify.com",
    "open.spotify.com",
)


class MediaFetchError(Exception):
    pass


def is_blocked_streaming_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == b or host.endswith("." + b) for b in BLOCKED_HOSTS)


def is_direct_audio_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in DIRECT_AUDIO_EXTENSIONS)


def download_audio_from_url(url: str, output_path: str) -> str:
    """僅支援直接音檔 URL（結尾為 .mp3 / .wav 等）。"""
    if is_blocked_streaming_url(url):
        raise MediaFetchError(
            "不支援 YouTube / Spotify。請用 **📁 上傳 MP3** 或 **🎹 MIDI 檔**。"
        )
    if not is_direct_audio_url(url):
        raise MediaFetchError(
            "僅支援**直接音檔連結**（網址需以 .mp3、.wav、.m4a 等結尾）。"
            "請先下載檔案再上傳，或使用 **🎹 MIDI 檔**。"
        )

    path = urlparse(url).path.lower()
    ext = next((e for e in DIRECT_AUDIO_EXTENSIONS if path.endswith(e)), ".mp3")
    out_base = output_path.rsplit(".", 1)[0]
    parent = os.path.dirname(out_base)
    if parent:
        os.makedirs(parent, exist_ok=True)
    out_file = out_base + ext

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    if len(data) < 2048:
        raise MediaFetchError("下載檔案過小，可能不是有效音訊")
    with open(out_file, "wb") as f:
        f.write(data)
    return out_file
