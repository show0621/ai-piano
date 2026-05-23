import base64
import json
import os
import re

import streamlit as st
import streamlit.components.v1 as components

from audio_processor import (
    HAS_BASIC_PITCH,
    detect_chorus_bounds,
    extract_section,
    get_demo_score,
    process_audio_to_json,
)
from config_secrets import (
    get_spotify_credentials,
    mask_secret,
    spotify_configured,
    spotify_credential_source,
    spotify_premium_help_markdown,
    verify_spotify_connection,
)
from music_search import SpotifyPremiumRequiredError
from music_search import resolve_spotify_to_youtube, search_spotify, search_youtube
from youtube_dl import YouTubeDownloadError, download_audio_from_url, format_youtube_error

st.set_page_config(
    page_title="音ノ手帖 · AI 鋼琴",
    layout="wide",
    page_icon="🎹",
    initial_sidebar_state="expanded",
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")
OUTPUT_DIR = os.path.join(APP_DIR, "output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

IS_CLOUD = bool(os.environ.get("STREAMLIT_RUNTIME_ENVIRONMENT"))

# ── 日系文青 UI ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;600&family=Zen+Kaku+Gothic+New:wght@300;400&display=swap');

html, body, [class*="css"] {
    font-family: 'Zen Kaku Gothic New', 'Noto Sans TC', sans-serif;
    color: #4A4035;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {
    font-family: 'Noto Serif JP', 'Noto Serif TC', serif !important;
    font-weight: 400 !important;
    letter-spacing: 0.12em;
    color: #4A4035 !important;
}
.stApp {
    background: linear-gradient(165deg, #F7F3EB 0%, #EFEBE3 45%, #E8E2D8 100%);
}
[data-testid="stSidebar"] {
    background: #EFEBE3;
    border-right: 1px solid #D4C9B8;
}
.stButton > button[kind="primary"] {
    background: #8B7355 !important;
    color: #F7F3EB !important;
    border: none !important;
    border-radius: 2px !important;
    letter-spacing: 0.08em;
}
.stButton > button {
    border-radius: 2px !important;
    border: 1px solid #C9B8A4 !important;
    background: #F7F3EB !important;
    color: #4A4035 !important;
}
.hero-sub {
    font-family: 'Noto Serif JP', serif;
    color: #8B7355;
    letter-spacing: 0.2em;
    font-size: 0.85rem;
    margin-bottom: 0.2rem;
}
.hero-title {
    font-family: 'Noto Serif JP', serif;
    font-size: 1.85rem;
    letter-spacing: 0.15em;
    color: #3D3530;
    margin: 0 0 0.5rem 0;
}
.card {
    background: rgba(255,252,247,0.75);
    border: 1px solid #D4C9B8;
    border-radius: 4px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)


def audio_to_data_uri(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4"}.get(ext, "audio/mpeg")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def render_piano(
    score_data: list,
    audio_src: str,
    title: str,
    chorus_start: float = 0,
    chorus_end: float = 0,
    practice_mode: str = "full",
    audio_offset: float = 0,
    auto_play: bool = False,
):
    with open(os.path.join(APP_DIR, "frontend.html"), "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{{SCORE_JSON_PLACEHOLDER}}", json.dumps(score_data, ensure_ascii=False))
    html = html.replace("{{AUDIO_SRC_PLACEHOLDER}}", audio_src)
    html = html.replace("{{SONG_TITLE}}", title.replace('"', "'"))
    html = html.replace("{{CHORUS_START}}", str(chorus_start))
    html = html.replace("{{CHORUS_END}}", str(chorus_end))
    html = html.replace("{{PRACTICE_MODE}}", practice_mode)
    html = html.replace("{{AUDIO_OFFSET}}", str(audio_offset))
    html = html.replace("{{AUTO_PLAY}}", "true" if auto_play else "false")

    components.html(html, height=960, scrolling=False)


def save_upload(uploaded_file) -> str:
    safe_name = re.sub(r"[^\w.\-]", "_", uploaded_file.name)
    path = os.path.join(UPLOAD_DIR, f"upload_{safe_name}")
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def run_ai_transcription(audio_path: str, simplify_melody: bool) -> list:
    if not HAS_BASIC_PITCH:
        raise RuntimeError("未安裝 basic-pitch。請執行：pip install -r requirements.txt")

    cache_key = f"{audio_path}|{simplify_melody}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    notes = process_audio_to_json(audio_path, OUTPUT_DIR, simplify=simplify_melody)
    if not notes:
        raise ValueError("AI 未辨識到有效音符，請換一首或上傳較清晰的音檔。")

    st.session_state[cache_key] = notes
    return notes


def get_youtube_cookies_path() -> str | None:
    """Streamlit Secrets: [youtube] cookies_txt = 瀏覽器匯出的 cookies.txt 全文。"""
    try:
        raw = st.secrets.get("youtube", {}).get("cookies_txt")
        if raw:
            path = os.path.join(UPLOAD_DIR, ".yt_cookies.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw)
            return path
    except Exception:
        pass
    env_path = os.environ.get("YOUTUBE_COOKIES_FILE")
    if env_path and os.path.isfile(env_path):
        return env_path
    return None


def download_audio_from_candidates(candidates: list[dict], out_base: str) -> str:
    """依序嘗試多個 YouTube 結果，降低單一影片 403 的影響。"""
    cookies = get_youtube_cookies_path()
    last_err: Exception | None = None
    for i, cand in enumerate(candidates):
        try:
            return download_audio_from_url(
                cand["url"],
                f"{out_base}_{i}",
                cookies_path=cookies,
            )
        except Exception as exc:
            last_err = exc
    if isinstance(last_err, YouTubeDownloadError):
        raise last_err
    raise YouTubeDownloadError(format_youtube_error(last_err or Exception("download failed")), last_err)


def show_parse_error(exc: Exception) -> None:
    st.session_state["last_download_failed"] = True
    if isinstance(exc, YouTubeDownloadError):
        st.error(str(exc))
    else:
        low = str(exc).lower()
        if "403" in low or "forbidden" in low or "format is not available" in low:
            st.error(format_youtube_error(exc))
        else:
            st.error(f"解析失敗：{exc}")
    render_upload_fallback_guide()


def render_upload_fallback_guide() -> None:
    """YouTube / 網路下載失敗時的可靠替代流程。"""
    st.info(
        "**✅ 建議改走「上傳 MP3」（AI 抓譜一樣會跑）**\n\n"
        "1. 上方 **① 選擇音源** 點 **📁 本機上傳**\n"
        "2. 選擇電腦或手機裡的 MP3 / WAV / M4A\n"
        "3. 按 **上傳並抓譜**\n\n"
        "若暫時沒有檔案：可先選 **🌸 示範曲** 體驗鍵盤教學（不需 YouTube）。"
    )


def prepare_score(notes: list, practice_scope: str):
    """依練習範圍回傳 (score, chorus_start, chorus_end, audio_offset, mode)."""
    c0, c1 = detect_chorus_bounds(notes)
    if practice_scope == "僅副歌":
        return extract_section(notes, c0, c1), c0, c1, c0, "chorus"
    return notes, c0, c1, 0.0, "full"


AUDIO_SOURCES = [
    "📁 本機上傳",
    "🎧 Spotify",
    "▶️ YouTube",
    "🔗 其他音源網址",
    "🌸 示範曲",
]

UPLOAD_TYPES = ["mp3", "wav", "m4a", "ogg", "flac", "aac", "webm"]


def ai_not_ready_message() -> str:
    return (
        "**無法 AI 抓譜**：TensorFlow / basic-pitch 尚未載入。"
        " 請先用「🌸 示範曲」；雲端請確認 **Python 3.11**、**Memory 2GB+**，"
        "完成部署後 **Reboot**（首次 AI 約 1–3 分鐘）。"
    )


def queue_ai_job(job: dict) -> None:
    """將抓譜工作放入佇列（下一輪 rerun 執行）。"""
    st.session_state.pop("lesson_ready", None)
    st.session_state["pending_job"] = job


def save_lesson(notes: list, title: str, audio_path: str | None) -> None:
    score_data, chorus_start, chorus_end, audio_offset, practice_mode = prepare_score(
        notes, practice_scope
    )
    st.session_state["lesson"] = {
        "score": score_data,
        "title": title,
        "audio_path": audio_path,
        "chorus_start": chorus_start,
        "chorus_end": chorus_end,
        "audio_offset": audio_offset,
        "practice_mode": practice_mode,
        "auto_play": auto_play_demo,
        "source": st.session_state.get("audio_source", ""),
    }
    st.session_state["lesson_ready"] = True


# ── Header ──
st.markdown('<p class="hero-sub">音ノ手帖 · Oto no Techō</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-title">鍵盤上的練習筆記</p>', unsafe_allow_html=True)
st.caption("選擇音源：上傳 · Spotify · YouTube · 其他網址 · 示範曲")

if IS_CLOUD:
    st.success(
        "☁️ **雲端建議音源：📁 本機上傳**（YouTube / Spotify 在雲端常被擋，上傳 MP3 最穩）。"
    )
    st.caption("Memory 建議 2GB+ · 首次 AI 需下載模型 · 示範曲不需網路")
if not HAS_BASIC_PITCH:
    st.warning(
        "**AI 抓譜尚未就緒**（TensorFlow / basic-pitch 未載入）。"
        "仍可使用「示範曲」。雲端請確認：**Python 3.11**、**Memory 2GB+**，"
        "並等待本次部署安裝完成後按 **Reboot**。"
    )

# ── Sidebar ──
with st.sidebar:
    if IS_CLOUD and not HAS_BASIC_PITCH:
        st.warning(
            "Cloud 正在安裝 AI 模組，或安裝失敗。請到 App **Settings → Advanced → Python 3.11**、"
            "**Memory 2GB+**，查看 **Manage app → Logs** 是否有 TensorFlow 錯誤，完成後 **Reboot**。"
        )
    st.markdown("### 練習設定")
    practice_scope = st.radio(
        "練習範圍",
        ["整首歌曲", "僅副歌"],
        help="副歌由 AI 依音符密度自動估算，可在教學區微調 A-B 循環。",
    )
    simplify_melody = st.checkbox("簡化主旋律", value=True)
    auto_play_demo = st.checkbox("載入後自動彈奏示範", value=False)

    st.markdown("---")
    st.markdown("### Spotify")
    cid, csec = get_spotify_credentials()

    if spotify_configured():
        if "spotify_verify_ok" not in st.session_state:
            ok, msg = verify_spotify_connection()
            st.session_state["spotify_verify_ok"] = ok
            st.session_state["spotify_verify_msg"] = msg

        if st.session_state.get("spotify_verify_ok"):
            st.success("Spotify API 已自動連線")
            st.caption(st.session_state.get("spotify_verify_msg", ""))
        elif st.session_state.get("spotify_verify_msg") == "premium_required":
            st.warning("Secrets 正確，但 Spotify 要求帳號 Premium")
            with st.expander("為什麼？怎麼辦？", expanded=True):
                st.markdown(spotify_premium_help_markdown())
        else:
            st.error("Secrets 已讀取，但 Spotify 驗證失敗")
            st.caption(st.session_state.get("spotify_verify_msg", ""))

        st.caption(f"來源：{spotify_credential_source()} · ID：`{mask_secret(cid)}`")
        if st.button("重新測試連線", key="btn_spotify_retest"):
            st.session_state.pop("spotify_verify_ok", None)
            st.session_state.pop("spotify_verify_msg", None)
            st.rerun()
    else:
        st.warning("尚未讀到 Spotify Secrets")
        st.caption(
            "請確認 Secrets 格式為 `[spotify]` + `client_id` / `client_secret`，"
            "Save 後 **Reboot**。"
        )
    with st.expander("📖 Spotify API 與金鑰安全（勿提交 GitHub）"):
        st.markdown(
            "### 原則\n"
            "- **GitHub 倉庫只放程式**，`client_id` / `client_secret` **絕不 push**\n"
            "- 金鑰放在 **Streamlit Cloud Secrets**（加密、不進 repo）或本機 `.streamlit/secrets.toml`\n\n"
            "### 1. 申請 Spotify 金鑰\n"
            "1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) → **Create app**\n"
            "2. Redirect URI：`http://localhost:8501`\n"
            "3. **Settings** → 複製 **Client ID**、**Client secret**\n\n"
            "### 2. 雲端 Streamlit（推薦）\n"
            "1. [share.streamlit.io](https://share.streamlit.io) → 你的 App → **Settings** → **Secrets**\n"
            "2. 貼上後 **Save** → **Reboot**：\n"
            "```toml\n[spotify]\nclient_id = \"你的ID\"\nclient_secret = \"你的Secret\"\n```\n\n"
            "### 3. 本機開發\n"
            "- 複製 `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`（已在 .gitignore）\n"
            "- 或複製 `.env.example` → `.env`，填入 `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`\n\n"
            "### 4. GitHub Actions 加密 Secrets（進階 / CI）\n"
            "Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**\n"
            "- `SPOTIFY_CLIENT_ID`\n"
            "- `SPOTIFY_CLIENT_SECRET`\n\n"
            "僅供 Action 使用；**Streamlit Cloud 仍要在第 2 步單獨設定**。\n\n"
            "**注意**：Spotify 只負責搜尋歌名；音訊請用 **📁 上傳 MP3**（雲端最穩）。"
        )

    st.markdown("---")
    st.markdown("### YouTube（選填）")
    if get_youtube_cookies_path():
        st.success("已載入 YouTube cookies")
    else:
        st.caption(
            "雲端若 403，請改 **上傳 MP3**。"
            "或在 Secrets 加入 `youtube.cookies_txt`（cookies.txt 全文）。"
        )

# ── 音源選擇 ──
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ① 選擇音源")
audio_source = st.radio(
    "音源類型",
    AUDIO_SOURCES,
    horizontal=True,
    label_visibility="collapsed",
    key="audio_source_radio",
)
st.session_state["audio_source"] = audio_source

yt_cookies = get_youtube_cookies_path()

# ── 📁 本機上傳 ──
if audio_source == "📁 本機上傳":
    st.markdown("#### 本機音檔 ⭐ 推薦")
    st.caption("**最穩定**：不依賴 YouTube。支援 MP3、WAV、M4A、OGG、FLAC 等。")
    with st.expander("如何取得 MP3？（Spotify / YouTube 歌曲）"):
        st.markdown(
            "- **已有檔案**：直接上傳\n"
            "- **CD / 購買下載**：使用既有 MP3\n"
            "- **自行錄音**：手機錄製練習用音檔也可\n"
            "- **YouTube 在雲端常失敗**：請在本機用合法工具轉檔後再上傳\n"
            "- **示範**：選 **🌸 示範曲** 不需任何檔案"
        )
    uploaded = st.file_uploader(
        "選擇音檔",
        type=UPLOAD_TYPES,
        key="upload_file",
    )
    custom_title = st.text_input("歌曲名稱（選填）", placeholder="例：晴天")
    if uploaded and st.button("上傳並抓譜", type="primary", key="btn_upload"):
        if not HAS_BASIC_PITCH:
            st.error(ai_not_ready_message())
        else:
            title = custom_title.strip() or uploaded.name
            queue_ai_job({
                "kind": "upload",
                "path": save_upload(uploaded),
                "title": title,
            })

# ── 🎧 Spotify ──
elif audio_source == "🎧 Spotify":
    st.markdown("#### Spotify 搜尋")
    if st.session_state.get("spotify_verify_ok"):
        st.caption("✅ Spotify API 已連線。")
    elif st.session_state.get("spotify_verify_msg") == "premium_required":
        st.info(
            "無 Premium 時會**自動改用 YouTube 搜尋**歌名（結果標示 [YOUTUBE]）。"
            "音訊建議 **📁 上傳 MP3**。"
        )
    elif spotify_configured():
        st.warning("金鑰已載入但驗證未過，請看側邊欄。")
    else:
        st.warning("請先在 Streamlit **Secrets** 設定 `[spotify]`，Save 後 **Reboot**。")
    if st.session_state.get("spotify_search_via") == "youtube":
        st.caption("上次搜尋：已透過 **YouTube** 取得曲目列表。")
    sp_query = st.text_input(
        "歌名或歌手 + 歌名",
        placeholder="例：周杰倫 晴天",
        key="sp_query",
    )
    if sp_query and st.button("Spotify 搜尋", type="primary", key="btn_sp_search"):
        with st.spinner("搜尋中…"):
            sp_results = []
            use_yt_fallback = not st.session_state.get("spotify_verify_ok")
            if not use_yt_fallback and cid and csec:
                try:
                    sp_results = search_spotify(sp_query, cid, csec)
                except SpotifyPremiumRequiredError:
                    use_yt_fallback = True
                    st.session_state["spotify_verify_ok"] = False
                    st.session_state["spotify_verify_msg"] = "premium_required"
            if use_yt_fallback or not sp_results:
                sp_results = search_youtube(sp_query, max_results=6, cookies_path=yt_cookies)
                st.session_state["spotify_search_via"] = "youtube"
            else:
                st.session_state["spotify_search_via"] = "spotify"
        st.session_state["spotify_results"] = sp_results

    sp_results = st.session_state.get("spotify_results", [])
    if sp_results:
        sp_labels = [f"[{r['source'].upper()}] {r['title']}" for r in sp_results]
        sp_pick = st.selectbox(
            "選擇曲目",
            range(len(sp_labels)),
            format_func=lambda i: sp_labels[i],
            key="sp_pick",
        )
        if st.button("解析並開始教學", type="primary", key="btn_sp_parse"):
            if not HAS_BASIC_PITCH:
                st.error(ai_not_ready_message())
            else:
                queue_ai_job({"kind": "track", "track": sp_results[sp_pick]})

# ── ▶️ YouTube ──
elif audio_source == "▶️ YouTube":
    st.markdown("#### YouTube")
    if IS_CLOUD:
        st.warning(
            "☁️ **雲端 YouTube 成功率低**（403 / 無格式）。"
            "失敗請改 **📁 本機上傳**；或在本機執行 `streamlit run app.py` 再試 YouTube。"
        )
    yt_mode = st.radio(
        "方式",
        ["搜尋歌曲", "貼上連結"],
        horizontal=True,
        key="yt_mode",
    )
    if yt_mode == "搜尋歌曲":
        yt_query = st.text_input(
            "歌名或關鍵字",
            placeholder="例：First Love 宇多田ヒカル",
            key="yt_query",
        )
        if yt_query and st.button("YouTube 搜尋", type="primary", key="btn_yt_search"):
            with st.spinner("YouTube 搜尋中…"):
                st.session_state["youtube_results"] = search_youtube(
                    yt_query, cookies_path=yt_cookies
                )
        yt_results = st.session_state.get("youtube_results", [])
        if yt_results:
            yt_labels = [f"[YT] {r['title']}" for r in yt_results]
            yt_pick = st.selectbox(
                "選擇影片",
                range(len(yt_labels)),
                format_func=lambda i: yt_labels[i],
                key="yt_pick",
            )
            if st.button("解析並開始教學", type="primary", key="btn_yt_parse"):
                if not HAS_BASIC_PITCH:
                    st.error(ai_not_ready_message())
                else:
                    queue_ai_job({"kind": "track", "track": yt_results[yt_pick]})
    else:
        yt_url = st.text_input(
            "YouTube 網址",
            placeholder="https://www.youtube.com/watch?v=...",
            key="yt_url",
        )
        yt_title = st.text_input("歌曲名稱（選填）", key="yt_url_title")
        if yt_url and st.button("下載並抓譜", type="primary", key="btn_yt_url"):
            if not HAS_BASIC_PITCH:
                st.error(ai_not_ready_message())
            else:
                queue_ai_job({
                    "kind": "url",
                    "url": yt_url.strip(),
                    "title": yt_title.strip() or "YouTube 歌曲",
                    "out_base": "yt_direct",
                })

# ── 🔗 其他音源 ──
elif audio_source == "🔗 其他音源網址":
    st.markdown("#### 其他音源網址")
    st.caption(
        "貼上可下載的音訊／影片連結，由 yt-dlp 處理。"
        "常見：SoundCloud、Bilibili、直接 .mp3 連結等（依網站而定）。"
    )
    other_url = st.text_input(
        "音源網址",
        placeholder="https://...",
        key="other_url",
    )
    other_title = st.text_input("歌曲名稱（選填）", key="other_title")
    if other_url and st.button("下載並抓譜", type="primary", key="btn_other_url"):
        if not HAS_BASIC_PITCH:
            st.error(ai_not_ready_message())
        else:
            queue_ai_job({
                "kind": "url",
                "url": other_url.strip(),
                "title": other_title.strip() or "網路音源",
                "out_base": "media_url",
            })

# ── 🌸 示範曲 ──
else:
    st.markdown("#### 內建示範曲")
    st.caption("不需 AI、不需網路，可直接練習鍵盤與下落音符。")
    demo = st.selectbox("選擇曲目", ["小星星", "笑傲江湖（滄海一聲笑）"], key="demo_pick")
    if st.button("載入示範曲", type="primary", key="btn_demo"):
        demo_id = "xiaoaojianghu" if "笑傲" in demo else "twinkle"
        full = get_demo_score(demo_id)
        score_data, chorus_start, chorus_end, audio_offset, practice_mode = prepare_score(
            full, practice_scope
        )
        st.session_state["lesson_ready"] = True
        st.session_state["lesson"] = {
            "score": score_data,
            "title": demo,
            "audio_path": None,
            "chorus_start": chorus_start,
            "chorus_end": chorus_end,
            "audio_offset": audio_offset,
            "practice_mode": practice_mode,
            "auto_play": auto_play_demo,
            "source": audio_source,
        }

st.markdown("</div>", unsafe_allow_html=True)

# ── 處理 AI 抓譜佇列 ──
if "pending_job" in st.session_state and not HAS_BASIC_PITCH:
    st.session_state.pop("pending_job", None)

if "pending_job" in st.session_state and HAS_BASIC_PITCH:
    job = st.session_state.pop("pending_job")
    with st.spinner("取得音源並 AI 抓譜中…"):
        try:
            if job["kind"] == "upload":
                audio_path = job["path"]
                title = job["title"]
            elif job["kind"] == "url":
                audio_path = download_audio_from_url(
                    job["url"],
                    os.path.join(UPLOAD_DIR, job.get("out_base", "media")),
                    cookies_path=yt_cookies,
                )
                title = job["title"]
            elif job["kind"] == "track":
                track = job["track"]
                title = track["title"]
                if track["source"] == "spotify":
                    yt_candidates = resolve_spotify_to_youtube(
                        track, cookies_path=yt_cookies
                    )
                    if not yt_candidates:
                        raise ValueError(
                            "找不到對應 YouTube 音源。請改選 YouTube 搜尋或上傳 MP3。"
                        )
                else:
                    yt_candidates = [track]
                audio_path = download_audio_from_candidates(
                    yt_candidates, os.path.join(UPLOAD_DIR, "search_audio")
                )
            else:
                raise ValueError(f"未知工作類型：{job.get('kind')}")

            notes = run_ai_transcription(audio_path, simplify_melody)
            save_lesson(notes, title, audio_path)
            st.success(f"完成：{title}")
        except Exception as e:
            show_parse_error(e)

# ── Render lesson ──
if st.session_state.get("lesson_ready") and "lesson" in st.session_state:
    L = st.session_state["lesson"]
    st.markdown("---")
    mode_label = "副歌練習" if L["practice_mode"] == "chorus" else "整首練習"
    src = L.get("source", "")
    src_tag = f" · {src}" if src else ""
    st.markdown(f"**{L['title']}** · {len(L['score'])} 音符 · {mode_label}{src_tag}")

    if L["practice_mode"] == "full" and L["chorus_end"] > L["chorus_start"]:
        st.caption(
            f"偵測副歌約 {L['chorus_start']:.1f}s – {L['chorus_end']:.1f}s"
            "（可在下方切換「僅副歌」重新載入）"
        )

    audio_src = ""
    if L.get("audio_path") and os.path.exists(L["audio_path"]):
        st.audio(L["audio_path"])
        audio_src = audio_to_data_uri(L["audio_path"])

    render_piano(
        L["score"],
        audio_src,
        L["title"],
        chorus_start=L["chorus_start"],
        chorus_end=L["chorus_end"],
        practice_mode=L["practice_mode"],
        audio_offset=L["audio_offset"],
        auto_play=L.get("auto_play", False),
    )

    if L.get("auto_play"):
        st.caption("已啟用「載入後自動彈奏」— 請在教學區點擊播放或等待自動開始。")
