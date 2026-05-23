"""YouTube / Spotify 歌曲搜尋。"""

from __future__ import annotations

import os
from typing import Optional


class SpotifyPremiumRequiredError(Exception):
    """Spotify 2026 起：開發者帳號需 Premium 才能呼叫 Web API。"""

    def __init__(self, message: str | None = None):
        super().__init__(
            message
            or (
                "Spotify 要求「建立此 App 的帳號」必須訂閱 Premium。"
                "訂閱後可能需等待數小時才會生效。"
            )
        )


def is_spotify_premium_error(exc: Exception) -> bool:
    return "premium subscription required" in str(exc).lower()


def search_youtube(
    query: str,
    max_results: int = 6,
    cookies_path: str | None = None,
) -> list[dict]:
    import yt_dlp

    from youtube_dl import search_ytdl_opts

    ydl_opts = search_ytdl_opts(cookies_path=cookies_path)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
    entries = info.get("entries") or []
    results = []
    for e in entries:
        if not e:
            continue
        vid = e.get("id")
        results.append({
            "source": "youtube",
            "id": vid,
            "title": e.get("title", "未知標題"),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "duration": e.get("duration"),
        })
    return results


def _spotify_client(client_id: str, client_secret: str):
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    )


def verify_spotify_api(
    client_id: str,
    client_secret: str,
    test_query: str = "a",
) -> dict:
    """啟動時連線測試，成功回傳第一筆曲目摘要。"""
    try:
        sp = _spotify_client(client_id, client_secret)
        resp = sp.search(q=test_query, type="track", limit=1)
    except Exception as exc:
        if is_spotify_premium_error(exc):
            raise SpotifyPremiumRequiredError() from exc
        raise
    items = resp.get("tracks", {}).get("items", [])
    if not items:
        return {"title": "（無搜尋結果，但 API 可用）"}
    t = items[0]
    artists = ", ".join(a["name"] for a in t["artists"])
    return {"title": f"{artists} — {t['name']}"}


def search_spotify(
    query: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    max_results: int = 6,
) -> list[dict]:
    cid = client_id or os.environ.get("SPOTIFY_CLIENT_ID")
    secret = client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not cid or not secret:
        return []

    try:
        sp = _spotify_client(cid, secret)
    except ImportError:
        return []

    try:
        resp = sp.search(q=query, type="track", limit=max_results)
    except Exception as exc:
        if is_spotify_premium_error(exc):
            raise SpotifyPremiumRequiredError() from exc
        raise
    items = resp.get("tracks", {}).get("items", [])
    results = []
    for t in items:
        artists = ", ".join(a["name"] for a in t["artists"])
        results.append({
            "source": "spotify",
            "id": t["id"],
            "title": f"{artists} — {t['name']}",
            "artist": artists,
            "name": t["name"],
            "url": t["external_urls"].get("spotify", ""),
            "duration_ms": t.get("duration_ms"),
        })
    return results


def resolve_spotify_to_youtube(
    spotify_track: dict,
    cookies_path: str | None = None,
) -> list[dict]:
    """Spotify 曲目 → 以歌名在 YouTube 找音檔。"""
    q = f"{spotify_track.get('artist', '')} {spotify_track.get('name', '')} official audio"
    return search_youtube(q.strip(), max_results=5, cookies_path=cookies_path)
