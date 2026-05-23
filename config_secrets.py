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


def get_spotify_credentials() -> tuple[str | None, str | None]:
    """回傳 (client_id, client_secret)，未設定則為 (None, None)。"""
    try:
        import streamlit as st

        block = st.secrets.get("spotify", {})
        cid = _clean(block.get("client_id"))
        csec = _clean(block.get("client_secret"))
        if cid and csec:
            return cid, csec
    except Exception:
        pass

    cid = _clean(os.environ.get("SPOTIFY_CLIENT_ID"))
    csec = _clean(os.environ.get("SPOTIFY_CLIENT_SECRET"))
    return cid, csec


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
