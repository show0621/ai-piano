"""YouTube 下載（yt-dlp），含 403 重試與 player client 回退。"""

from __future__ import annotations

import os
from typing import Optional

# 依 yt-dlp 2026 建議：避開 android_sdkless，輪換 client
PLAYER_STRATEGIES: list[dict] = [
    {"player_client": ["web", "android_vr"]},
    {"player_client": ["default", "-android_sdkless"]},
    {"player_client": ["ios", "web"]},
    {"player_client": ["mweb"]},
    {"player_client": ["tv_embedded", "web"]},
]

# 由寬到嚴：部分影片僅有合併串流或 m3u8，需多種 fallback
AUDIO_FORMAT_CANDIDATES: list[str] = [
    "bestaudio/best",
    "bestaudio",
    "ba/b",
    "b",
    "best[height<=720]/best",
    "best",
    "worstaudio/worst",
    "worst",
]


class YouTubeDownloadError(Exception):
    """YouTube 下載失敗（含 403 等）。"""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


def format_youtube_error(exc: Exception) -> str:
    """轉成使用者可讀的繁中說明。"""
    raw = str(exc).strip()
    low = raw.lower()
    if "403" in low or "forbidden" in low:
        return (
            "YouTube 拒絕下載（HTTP 403）。常見原因：\n"
            "1. **Streamlit 雲端 IP** 被 YouTube 擋下 → 請改用 **「📁 上傳音檔」** 分頁上傳 MP3\n"
            "2. yt-dlp 版本過舊 → 請 Reboot 等重新部署\n"
            "3. 進階：在 Secrets 加入 `youtube.cookies_txt`（瀏覽器匯出的 cookies.txt）"
        )
    if "private" in low or "unavailable" in low:
        return "此影片無法播放（私人、地區限制或已下架）。請換一首或上傳音檔。"
    if "ffmpeg" in low:
        return "需要 ffmpeg 才能轉成 MP3。雲端請確認 `packages.txt` 含 ffmpeg。"
    if "format is not available" in low or "requested format" in low:
        return (
            "此影片沒有可用的音訊格式（YouTube 限制）。"
            "請換一首、改 **上傳 MP3**，或於 Secrets 設定 `youtube.cookies_txt` 後重試。"
        )
    return raw or "YouTube 下載失敗，請改上傳音檔或稍後再試。"


def _apply_strategy(opts: dict, strategy: dict) -> dict:
    merged = dict(opts)
    ea = dict(merged.get("extractor_args") or {})
    yt = dict(ea.get("youtube") or {})
    yt.update(strategy)
    ea["youtube"] = yt
    merged["extractor_args"] = ea
    return merged


def base_ydl_opts(
    *,
    cookies_path: Optional[str] = None,
    quiet: bool = True,
) -> dict:
    opts: dict = {
        "quiet": quiet,
        "no_warnings": quiet,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 5,
        "socket_timeout": 45,
        "geo_bypass": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        },
    }
    if cookies_path and os.path.isfile(cookies_path):
        opts["cookiefile"] = cookies_path
    return opts


def _find_audio_file(out_base: str) -> Optional[str]:
    mp3_path = out_base + ".mp3"
    if os.path.exists(mp3_path):
        return mp3_path

    folder = os.path.dirname(out_base) or "."
    base = os.path.basename(out_base)
    candidates = []
    for name in os.listdir(folder):
        if name.startswith(base) and name.endswith((".mp3", ".m4a", ".wav", ".webm", ".opus")):
            candidates.append(os.path.join(folder, name))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def download_youtube_audio(
    url: str,
    output_path: str,
    cookies_path: Optional[str] = None,
) -> str:
    """將 YouTube 連結下載為 MP3，多種 client 輪換以避開 403。"""
    import yt_dlp

    out_base = output_path.rsplit(".", 1)[0]
    parent = os.path.dirname(out_base)
    if parent:
        os.makedirs(parent, exist_ok=True)

    postprocessors = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ]

    last_exc: Exception | None = None
    for strategy in PLAYER_STRATEGIES:
        for fmt in AUDIO_FORMAT_CANDIDATES:
            opts = _apply_strategy(
                base_ydl_opts(cookies_path=cookies_path, quiet=True),
                strategy,
            )
            opts.update({
                "format": fmt,
                "outtmpl": out_base + ".%(ext)s",
                "postprocessors": postprocessors,
                # 允許合併影音後再抽音訊（format=b / best 時需要）
                "merge_output_format": "mp4",
            })
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                found = _find_audio_file(out_base)
                if found:
                    return found
                last_exc = FileNotFoundError("下載完成但找不到音檔")
            except Exception as exc:
                last_exc = exc
                err = str(exc).lower()
                # 格式不符才換下一組；403 等也繼續嘗試
                if "format is not available" in err or "requested format" in err:
                    continue
                if "403" in err or "forbidden" in err:
                    break  # 換 player client
                continue

    raise YouTubeDownloadError(format_youtube_error(last_exc or Exception("unknown")), last_exc)


def search_ytdl_opts(cookies_path: Optional[str] = None) -> dict:
    """搜尋用（不下載）的 yt-dlp 選項。"""
    opts = base_ydl_opts(cookies_path=cookies_path, quiet=True)
    opts.update({
        "extract_flat": True,
        "skip_download": True,
    })
    return _apply_strategy(opts, PLAYER_STRATEGIES[0])
