"""
API 金鑰載入（禁止寫死在程式碼或提交到 GitHub）。

優先順序：
  1. Streamlit Secrets（雲端：share.streamlit.io → Settings → Secrets）
  2. 環境變數（本機 .env、GitHub Actions 加密 Secrets）
"""

from __future__ import annotations

import os


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip()
    return v or None


def _read_spotify_block(block) -> tuple[str | None, str | None]:
    if block is None:
        return None, None
    if hasattr(block, "get"):
        return _clean(block.get("client_id")), _clean(block.get("client_secret"))
    return _clean(getattr(block, "client_id", None)), _clean(getattr(block, "client_secret", None))


def get_spotify_credentials() -> tuple[str | None, str | None]:
    """回傳 (client_id, client_secret)。優先 Streamlit Secrets，其次環境變數。"""
    cid = csec = None

    try:
        import streamlit as st

        cid, csec = _read_spotify_block(st.secrets.get("spotify"))
        if cid and csec:
            return cid, csec

        # 相容：Secrets 根層級變數名
        cid = _clean(st.secrets.get("SPOTIFY_CLIENT_ID")) or _clean(st.secrets.get("spotify_client_id"))
        csec = _clean(st.secrets.get("SPOTIFY_CLIENT_SECRET")) or _clean(
            st.secrets.get("spotify_client_secret")
        )
        if cid and csec:
            return cid, csec
    except Exception:
        pass

    cid = _clean(os.environ.get("SPOTIFY_CLIENT_ID"))
    csec = _clean(os.environ.get("SPOTIFY_CLIENT_SECRET"))
    return cid, csec


def spotify_credential_source() -> str:
    """回傳金鑰來源說明（除錯用，不含 secret）。"""
    try:
        import streamlit as st

        cid, csec = _read_spotify_block(st.secrets.get("spotify"))
        if cid and csec:
            return "Streamlit Secrets → [spotify]"
        if _clean(st.secrets.get("SPOTIFY_CLIENT_ID")):
            return "Streamlit Secrets → 根層級變數"
    except Exception:
        pass
    if os.environ.get("SPOTIFY_CLIENT_ID"):
        return "環境變數"
    return "未偵測到"


def mask_secret(value: str | None, visible: int = 4) -> str:
    """側欄顯示用，避免完整金鑰外洩。"""
    if not value:
        return "（未設定）"
    if len(value) <= visible + 2:
        return "*" * len(value)
    return value[:visible] + "…" + ("*" * 6)


def spotify_configured() -> bool:
    cid, csec = get_spotify_credentials()
    return bool(cid and csec)


def verify_spotify_connection() -> tuple[bool, str]:
    """
    實際呼叫 Spotify API 測試金鑰是否有效。
    回傳 (成功與否, 訊息)。
    """
    from music_search import verify_spotify_api

    cid, csec = get_spotify_credentials()
    if not cid or not csec:
        return False, "Secrets 未讀到 client_id / client_secret"
    try:
        sample = verify_spotify_api(cid, csec)
        title = sample.get("title", "測試曲目") if sample else "OK"
        return True, f"連線成功（範例：{title}）"
    except Exception as exc:
        from music_search import SpotifyPremiumRequiredError, is_spotify_premium_error

        if isinstance(exc, SpotifyPremiumRequiredError) or is_spotify_premium_error(exc):
            return False, "premium_required"
        return False, str(exc)


def get_youtube_cookies_path(upload_dir: str) -> str | None:
    """Streamlit Secrets: [youtube] cookies_txt。"""
    try:
        import streamlit as st

        raw = st.secrets.get("youtube", {}).get("cookies_txt")
        if raw:
            path = os.path.join(upload_dir, ".yt_cookies.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw)
            return path
    except Exception:
        pass
    env_path = os.environ.get("YOUTUBE_COOKIES_FILE")
    if env_path and os.path.isfile(env_path):
        return env_path
    return None


def get_youtube_proxy() -> str | None:
    """選填：住宅 Proxy，可提高雲端 YouTube 成功率（需自行購買）。"""
    try:
        import streamlit as st

        p = _clean(st.secrets.get("youtube", {}).get("proxy"))
        if p:
            return p
    except Exception:
        pass
    return _clean(os.environ.get("YOUTUBE_PROXY"))


def cloud_youtube_help_markdown() -> str:
    return (
        "### 為什麼雲端很難「穩定破解」？\n"
        "Streamlit Cloud 使用**機房 IP**，YouTube 會刻意阻擋自動下載（403 / 無格式）。"
        "這是平台政策，**沒有 100% 可靠的免費破解方式**。\n\n"
        "### 穩定方案（推薦順序）\n"
        "1. **📁 上傳 MP3** — 幾乎一定成功\n"
        "2. **本機執行** `streamlit run app.py` — 家用 IP，YouTube 成功率較高\n"
        "3. **🔗 其他音源** — 貼 **直接 .mp3 連結**（非 YouTube 頁面）\n\n"
        "### 可「提高機率」但非保證（Secrets）\n"
        "```toml\n[youtube]\n"
        'cookies_txt = """...瀏覽器 cookies.txt..."""\n'
        'proxy = "http://使用者:密碼@住宅代理:埠"\n'
        "```\n"
        "- **cookies**：登入 YouTube 後匯出，Save → Reboot\n"
        "- **proxy**：需**住宅 IP** 代理（機房代理通常仍被擋）\n\n"
        "不建議依賴違反服務條款的繞道工具，隨時會失效。"
    )


def spotify_premium_help_markdown() -> str:
    return (
        "**原因**：Spotify 自 2026/2 起，**建立 Developer App 的帳號**需有 "
        "**Spotify Premium**，否則搜尋 API 會回 403。\n\n"
        "**您可以：**\n"
        "1. 用**同一個帳號**（Dashboard 登入那個）訂閱 Premium，等 **2–24 小時** 再按「重新測試連線」\n"
        "2. 本 App 仍可用：**▶️ YouTube** 搜尋、**📁 上傳 MP3**（推薦）、**🌸 示範曲**\n"
        "3. 在 **🎧 Spotify** 分頁搜尋時，會**自動改以 YouTube** 找歌名（無需 Premium）\n\n"
        "參考：[Spotify 開發者公告](https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security)"
    )
