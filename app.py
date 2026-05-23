import base64
import json
import os
import re

import streamlit as st
import streamlit.components.v1 as components

from audio_processor import (
    HAS_BASIC_PITCH,
    download_youtube_audio,
    get_demo_score,
    process_audio_to_json,
)

st.set_page_config(page_title="AI 互動鋼琴教學", layout="wide", page_icon="🎹")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")
OUTPUT_DIR = os.path.join(APP_DIR, "output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") is not None or bool(
    os.environ.get("STREAMLIT_RUNTIME_ENVIRONMENT")
)


def audio_to_data_uri(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4"}.get(ext, "audio/mpeg")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def render_piano(score_data: list, audio_src: str, title: str):
    template_path = os.path.join(APP_DIR, "frontend.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{{SCORE_JSON_PLACEHOLDER}}", json.dumps(score_data, ensure_ascii=False))
    html = html.replace("{{AUDIO_SRC_PLACEHOLDER}}", audio_src)
    html = html.replace("{{SONG_TITLE}}", title.replace('"', "'"))

    components.html(html, height=920, scrolling=False)


def save_upload(uploaded_file) -> str:
    safe_name = re.sub(r"[^\w.\-]", "_", uploaded_file.name)
    path = os.path.join(UPLOAD_DIR, f"upload_{safe_name}")
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def run_ai_transcription(audio_path: str, simplify_melody: bool) -> list:
    """上傳 / YouTube 音檔一律走真實 AI，不再使用模擬樂譜。"""
    if not HAS_BASIC_PITCH:
        raise RuntimeError(
            "未安裝 basic-pitch。請執行：pip install -r requirements.txt"
        )

    cache_key = f"{audio_path}|{simplify_melody}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    notes = process_audio_to_json(audio_path, OUTPUT_DIR, simplify=simplify_melody)
    if not notes:
        raise ValueError(
            "AI 未辨識到有效音符。請嘗試：較短的純鋼琴片段、提高音量、或關閉主旋律簡化。"
        )

    st.session_state[cache_key] = notes
    return notes


# --- UI ---
st.title("🎹 AI 互動鋼琴：上傳 / YouTube → 自動抓譜 → 鍵盤教學")
st.caption(
    "上傳 MP3、貼上 YouTube 連結，或用示範曲。AI（basic-pitch）辨識後以 Synthesia 式下落音符教學，"
    "雙八度鍵盤標示要按哪一鍵、按多久。"
)

if IS_CLOUD:
    st.info("☁️ Streamlit Cloud 模式：建議 Memory 設為 2GB+，首次 AI 抓譜需下載模型。")

if not HAS_BASIC_PITCH:
    st.error("❌ 未偵測到 basic-pitch，上傳 / YouTube 無法抓譜。請執行 `pip install -r requirements.txt`")
    st.code("pip install basic-pitch tensorflow-cpu", language="bash")

col_side, col_main = st.columns([1, 2])

with col_side:
    st.subheader("① 選擇音源")
    source = st.radio(
        "音源類型",
        ["上傳音檔", "YouTube 連結", "內建示範曲"],
        label_visibility="collapsed",
    )

    simplify_melody = st.checkbox(
        "簡化為主旋律（建議，流行歌適用）",
        value=True,
        help="關閉可保留更多和弦音，但難度較高。",
    )

    if source != "內建示範曲":
        st.caption("✅ 已啟用真實 AI 抓譜（basic-pitch）")

    st.subheader("② 學習紀錄")
    mistake_json = st.text_area(
        "貼上前端複製的失誤 JSON（選填）",
        height=120,
        placeholder='[{"pitch":60,"start_time":1.2}, ...]',
    )
    if st.button("分析弱點段落") and mistake_json.strip():
        try:
            mistakes = json.loads(mistake_json)
            times = sorted(m["start_time"] for m in mistakes if "start_time" in m)
            segments = []
            if times:
                start, end = times[0], times[0]
                for t in times[1:]:
                    if t - end <= 3:
                        end = t
                    else:
                        segments.append({"start": max(0, start - 2), "end": end + 2})
                        start = end = t
                segments.append({"start": max(0, start - 2), "end": end + 2})
            st.session_state.practice_segments = segments
            st.success(f"找到 {len(segments)} 個建議練習段落")
            for i, seg in enumerate(segments, 1):
                st.write(f"段落 {i}: {seg['start']:.1f}s – {seg['end']:.1f}s")
        except json.JSONDecodeError:
            st.error("JSON 格式錯誤")

with col_main:
    score_data = None
    audio_path = None
    song_title = "示範曲"

    if source == "上傳音檔":
        if not HAS_BASIC_PITCH:
            st.warning("請先安裝 basic-pitch 後再上傳音檔。")
        else:
            uploaded = st.file_uploader("上傳 MP3 / WAV", type=["mp3", "wav", "m4a"])
            if uploaded:
                audio_path = save_upload(uploaded)
                song_title = uploaded.name

    elif source == "YouTube 連結":
        if not HAS_BASIC_PITCH:
            st.warning("請先安裝 basic-pitch。")
        else:
            yt_url = st.text_input(
                "貼上 YouTube 網址",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            if yt_url and st.button("下載並 AI 抓譜", type="primary"):
                with st.spinner("正在下載 YouTube 音檔…"):
                    try:
                        audio_path = download_youtube_audio(
                            yt_url, os.path.join(UPLOAD_DIR, "yt_audio")
                        )
                        song_title = "YouTube 歌曲"
                        st.session_state["yt_audio_path"] = audio_path
                        st.success("下載完成，開始 AI 抓譜…")
                    except Exception as e:
                        st.error(f"下載失敗：{e}")
            if "yt_audio_path" in st.session_state and not audio_path:
                audio_path = st.session_state["yt_audio_path"]
                song_title = "YouTube 歌曲"

    else:
        demo = st.selectbox("選擇示範曲（免 AI）", ["小星星", "笑傲江湖（滄海一聲笑）"])
        demo_id = "xiaoaojianghu" if "笑傲" in demo else "twinkle"
        score_data = get_demo_score(demo_id)
        song_title = demo

    # 真實 AI 抓譜（上傳 / YouTube）
    if audio_path and score_data is None and HAS_BASIC_PITCH:
        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if size_mb > 12:
            st.warning(f"音檔 {size_mb:.1f} MB，嵌入播放可能較慢，建議 3 分鐘內。")

        with st.spinner("🤖 AI 正在解析樂譜（basic-pitch）… 首次需下載模型"):
            try:
                score_data = run_ai_transcription(audio_path, simplify_melody)
            except Exception as e:
                st.error(f"抓譜失敗：{e}")
                st.stop()

    if score_data:
        st.success(f"樂譜就緒：{len(score_data)} 個音符 · {song_title}")

        if audio_path and os.path.exists(audio_path):
            st.audio(audio_path)
            audio_src = audio_to_data_uri(audio_path)
        else:
            audio_src = ""

        st.markdown("### 🎮 互動教學區")
        st.markdown(
            "**下排** A–J = C4–B4 · **上排** Q–U = C5–B5。"
            "跟彈模式：音符落到紅線時按對應鍵。"
        )
        render_piano(score_data, audio_src, song_title)
