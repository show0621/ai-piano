import base64
import json
import os
import re

import streamlit as st
import streamlit.components.v1 as components

from audio_processor import (
    HAS_BASIC_PITCH,
    detect_chorus_bounds,
    download_youtube_audio,
    extract_section,
    get_demo_score,
    process_audio_to_json,
)
from music_search import resolve_spotify_to_youtube, search_spotify, search_youtube
from youtube_dl import YouTubeDownloadError, format_youtube_error

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


def get_spotify_credentials():
    try:
        s = st.secrets.get("spotify", {})
        return s.get("client_id"), s.get("client_secret")
    except Exception:
        return None, None


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
            return download_youtube_audio(
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
    if isinstance(exc, YouTubeDownloadError):
        st.error(str(exc))
    else:
        low = str(exc).lower()
        if "403" in low or "forbidden" in low:
            st.error(format_youtube_error(exc))
        else:
            st.error(f"解析失敗：{exc}")


def prepare_score(notes: list, practice_scope: str):
    """依練習範圍回傳 (score, chorus_start, chorus_end, audio_offset, mode)."""
    c0, c1 = detect_chorus_bounds(notes)
    if practice_scope == "僅副歌":
        return extract_section(notes, c0, c1), c0, c1, c0, "chorus"
    return notes, c0, c1, 0.0, "full"


# ── Header ──
st.markdown('<p class="hero-sub">音ノ手帖 · Oto no Techō</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-title">鍵盤上的練習筆記</p>', unsafe_allow_html=True)
st.caption("輸入歌名搜尋 · AI 抓譜 · 副歌專練 · 自動彈奏示範")

if IS_CLOUD:
    st.info("☁️ 雲端模式：Memory 建議 2GB+，首次 AI 需下載模型。")
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
    st.markdown("### Spotify（選填）")
    st.caption("在 Secrets 設定 `spotify.client_id` 與 `client_secret` 即可啟用 Spotify 搜尋。")
    cid, csec = get_spotify_credentials()
    if cid and csec:
        st.success("Spotify API 已連線")
    else:
        st.caption("未設定時，Spotify 結果將改以 YouTube 搜尋代替。")

    st.markdown("---")
    st.markdown("### YouTube（選填）")
    if get_youtube_cookies_path():
        st.success("已載入 YouTube cookies")
    else:
        st.caption(
            "雲端若 403，請改 **上傳 MP3**。"
            "或在 Secrets 加入 `youtube.cookies_txt`（cookies.txt 全文）。"
        )

# ── Main tabs ──
tab_search, tab_upload, tab_url, tab_demo = st.tabs([
    "🔍 搜尋歌曲", "📁 上傳音檔", "🔗 YouTube 連結", "🌸 示範曲",
])

score_data = None
audio_path = None
song_title = "未命名"
chorus_start, chorus_end, audio_offset, practice_mode = 0, 0, 0, "full"

with tab_search:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if IS_CLOUD:
        st.caption("☁️ 雲端常因 YouTube 封鎖機房 IP 出現 403，建議改用 **📁 上傳音檔**。")
    query = st.text_input(
        "輸入歌名或「歌手 + 歌名」",
        placeholder="例：宇多田ヒカル First Love、周杰倫 晴天",
    )
    platform = st.radio(
        "搜尋來源",
        ["YouTube", "Spotify → YouTube", "兩者都搜"],
        horizontal=True,
        label_visibility="collapsed",
    )

    yt_cookies = get_youtube_cookies_path()

    if query and st.button("搜尋", type="primary", key="btn_search"):
        results = []
        with st.spinner("正在搜尋…"):
            if platform in ("YouTube", "兩者都搜"):
                results.extend(search_youtube(query, cookies_path=yt_cookies))
            if platform in ("Spotify → YouTube", "兩者都搜"):
                sp = search_spotify(query, cid, csec)
                if sp:
                    results.extend(sp)
                else:
                    results.extend(
                        search_youtube(f"{query} spotify", max_results=3, cookies_path=yt_cookies)
                    )
        st.session_state["search_results"] = results
        st.session_state["search_query"] = query

    results = st.session_state.get("search_results", [])
    if results:
        labels = [f"[{r['source'].upper()}] {r['title']}" for r in results]
        pick = st.selectbox("選擇曲目", range(len(labels)), format_func=lambda i: labels[i])
        picked = results[pick]

        if st.button("解析並開始教學", type="primary", key="btn_parse_search"):
            st.session_state.pop("lesson_ready", None)
            if not HAS_BASIC_PITCH:
                st.error(
                    "**無法 AI 抓譜**：TensorFlow / basic-pitch 尚未載入。"
                    " 請先用「🌸 示範曲」；雲端請確認 **Python 3.11**、**Memory 2GB+**，"
                    "等部署日誌安裝完成後 **Reboot**（首次 AI 還需下載模型，約 1–3 分鐘）。"
                )
            else:
                st.session_state["pending_track"] = picked

    st.markdown("</div>", unsafe_allow_html=True)

with tab_upload:
    uploaded = st.file_uploader("MP3 / WAV / M4A", type=["mp3", "wav", "m4a"])
    if uploaded and st.button("上傳並抓譜", type="primary", key="btn_upload"):
        st.session_state.pop("lesson_ready", None)
        if not HAS_BASIC_PITCH:
            st.error("**無法 AI 抓譜**：請先安裝 ML 依賴（見上方黃色提示）或使用「示範曲」。")
        else:
            st.session_state["pending_upload"] = save_upload(uploaded)
            st.session_state["pending_title"] = uploaded.name

with tab_url:
    yt_url = st.text_input("YouTube 網址", placeholder="https://www.youtube.com/watch?v=...")
    if yt_url and st.button("下載並抓譜", type="primary", key="btn_yt"):
        st.session_state.pop("lesson_ready", None)
        if not HAS_BASIC_PITCH:
            st.error("**無法 AI 抓譜**：請先安裝 ML 依賴（見上方黃色提示）或使用「示範曲」。")
        else:
            st.session_state["pending_yt"] = yt_url

with tab_demo:
    demo = st.selectbox("內建示範", ["小星星", "笑傲江湖（滄海一聲笑）"])
    if st.button("載入示範曲", type="primary", key="btn_demo"):
        demo_id = "xiaoaojianghu" if "笑傲" in demo else "twinkle"
        full = get_demo_score(demo_id)
        score_data, chorus_start, chorus_end, audio_offset, practice_mode = prepare_score(
            full, practice_scope
        )
        song_title = demo
        st.session_state["lesson_ready"] = True
        st.session_state["lesson"] = {
            "score": score_data,
            "title": song_title,
            "audio_path": None,
            "chorus_start": chorus_start,
            "chorus_end": chorus_end,
            "audio_offset": audio_offset,
            "practice_mode": practice_mode,
            "auto_play": auto_play_demo,
        }

# ── Process pending jobs ──
if "pending_track" in st.session_state and not HAS_BASIC_PITCH:
    st.session_state.pop("pending_track", None)

if "pending_upload" in st.session_state and not HAS_BASIC_PITCH:
    st.session_state.pop("pending_upload", None)
    st.session_state.pop("pending_title", None)

if "pending_yt" in st.session_state and not HAS_BASIC_PITCH:
    st.session_state.pop("pending_yt", None)

if "pending_track" in st.session_state and HAS_BASIC_PITCH:
    track = st.session_state.pop("pending_track")
    with st.spinner("取得音源並 AI 抓譜中…"):
        try:
            song_title = track["title"]
            if track["source"] == "spotify":
                yt_candidates = resolve_spotify_to_youtube(
                    track, cookies_path=get_youtube_cookies_path()
                )
                if not yt_candidates:
                    raise ValueError("找不到對應 YouTube 音源")
            else:
                yt_candidates = [track]
            audio_path = download_audio_from_candidates(
                yt_candidates, os.path.join(UPLOAD_DIR, "search_audio")
            )
            notes = run_ai_transcription(audio_path, simplify_melody)
            score_data, chorus_start, chorus_end, audio_offset, practice_mode = prepare_score(
                notes, practice_scope
            )
            st.session_state["lesson"] = {
                "score": score_data,
                "title": song_title,
                "audio_path": audio_path,
                "chorus_start": chorus_start,
                "chorus_end": chorus_end,
                "audio_offset": audio_offset,
                "practice_mode": practice_mode,
                "auto_play": auto_play_demo,
            }
            st.session_state["lesson_ready"] = True
            st.success(f"完成：{song_title}")
        except Exception as e:
            show_parse_error(e)

if "pending_upload" in st.session_state and HAS_BASIC_PITCH:
    path = st.session_state.pop("pending_upload")
    title = st.session_state.pop("pending_title", "上傳歌曲")
    with st.spinner("AI 抓譜中…"):
        try:
            notes = run_ai_transcription(path, simplify_melody)
            score_data, chorus_start, chorus_end, audio_offset, practice_mode = prepare_score(
                notes, practice_scope
            )
            st.session_state["lesson"] = {
                "score": score_data,
                "title": title,
                "audio_path": path,
                "chorus_start": chorus_start,
                "chorus_end": chorus_end,
                "audio_offset": audio_offset,
                "practice_mode": practice_mode,
                "auto_play": auto_play_demo,
            }
            st.session_state["lesson_ready"] = True
        except Exception as e:
            st.error(f"抓譜失敗：{e}")

if "pending_yt" in st.session_state and HAS_BASIC_PITCH:
    url = st.session_state.pop("pending_yt")
    with st.spinner("下載並抓譜…"):
        try:
            audio_path = download_youtube_audio(
                url,
                os.path.join(UPLOAD_DIR, "yt_audio"),
                cookies_path=get_youtube_cookies_path(),
            )
            notes = run_ai_transcription(audio_path, simplify_melody)
            score_data, chorus_start, chorus_end, audio_offset, practice_mode = prepare_score(
                notes, practice_scope
            )
            st.session_state["lesson"] = {
                "score": score_data,
                "title": "YouTube 歌曲",
                "audio_path": audio_path,
                "chorus_start": chorus_start,
                "chorus_end": chorus_end,
                "audio_offset": audio_offset,
                "practice_mode": practice_mode,
                "auto_play": auto_play_demo,
            }
            st.session_state["lesson_ready"] = True
        except Exception as e:
            show_parse_error(e)

# ── Render lesson ──
if st.session_state.get("lesson_ready") and "lesson" in st.session_state:
    L = st.session_state["lesson"]
    st.markdown("---")
    mode_label = "副歌練習" if L["practice_mode"] == "chorus" else "整首練習"
    st.markdown(f"**{L['title']}** · {len(L['score'])} 音符 · {mode_label}")

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
