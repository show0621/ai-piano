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
    filter_notes,
    get_demo_score,
    midi_to_web_notes,
    process_audio_to_json,
    simplify_to_melody,
)
from midi_resources import external_midi_search_links, midi_resources_guide_markdown
from score_library import (
    catalog_entry_title,
    export_notes_payload,
    list_catalog_entries,
    load_score,
    search_catalog,
)
from sheet_search import SheetHit, convert_user_input, fetch_and_convert, search_all
from media_fetch import MediaFetchError, download_audio_from_url

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
/* 手機 / iPad */
@media (max-width: 1024px) {
    .block-container { padding: 0.5rem 0.75rem 1rem; max-width: 100%; }
    [data-testid="stSidebar"] { min-width: 240px; }
    .hero-title { font-size: 1.35rem !important; }
}
@media (max-width: 768px) {
    .block-container { padding: 0.35rem 0.5rem 0.75rem; }
    [data-testid="column"] { width: 100% !important; flex: 1 1 100%; }
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

    # 手機橫向需較高 iframe；內部 frontend 會自適應寬高
    components.html(html, height=1180, scrolling=True)


def save_upload(uploaded_file) -> str:
    safe_name = re.sub(r"[^\w.\-]", "_", uploaded_file.name)
    path = os.path.join(UPLOAD_DIR, f"upload_{safe_name}")
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def save_audio_bytes(data: bytes, filename: str = "recording.wav") -> str:
    safe_name = re.sub(r"[^\w.\-]", "_", filename)
    path = os.path.join(UPLOAD_DIR, f"rec_{safe_name}")
    with open(path, "wb") as f:
        f.write(data)
    return path


def mobile_practice_guide() -> str:
    return (
        "### 📱 手機 / iPad 隨地練\n\n"
        "| 方式 | 穩定度 | 做法 |\n"
        "|------|--------|------|\n"
        "| **🎹 MIDI 檔** | ⭐⭐⭐ | BitMidi / EOP / MuseScore 下載 .mid 上傳 |\n"
        "| **📚 曲庫** | ⭐⭐⭐ | 已轉好的樂譜，雲端免 YT / 免 AI |\n"
        "| **🔍 搜尋樂譜** | ⭐⭐ | BitMidi / IMSLP / ABC / 外站連結 |\n"
        "| **🌸 示範曲** | ⭐⭐⭐ | 選示範曲 → 載入 → 橫放 → 點琴鍵 |\n"
        "| **📁 上傳 MP3** | ⭐⭐⭐ | 先把歌存成 MP3 到「檔案」→ 本頁上傳 |\n"
        "| **🎤 錄音** | ⭐⭐ | Android Chrome 較穩；錄一段旋律再抓譜 |\n\n"
        "**iPhone 把 MP3 放進手機：**\n"
        "1. 用 iTunes / 電腦同步、或合法下載 MP3 到 **「檔案」** App\n"
        "2. Safari 開本 App → **📁 本機上傳** → 選擇檔案\n"
        "3. 橫放 → **跟彈** → 點螢幕琴鍵\n\n"
        "練習區載入後，**同一首曲會保留在分頁中**（重新整理前可繼續練）。"
    )


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


def show_parse_error(exc: Exception) -> None:
    st.session_state["last_download_failed"] = True
    st.error(f"解析失敗：{exc}")
    render_upload_fallback_guide()


def render_upload_fallback_guide() -> None:
    """音源下載失敗時的替代流程。"""
    st.info(
        "**✅ 建議改走「上傳 MP3」（AI 抓譜一樣會跑）**\n\n"
        "1. 上方 **① 選擇音源** 點 **📁 本機上傳**\n"
        "2. 選擇電腦或手機裡的 MP3 / WAV / M4A\n"
        "3. 按 **上傳並抓譜**\n\n"
        "若暫時沒有檔案：可先選 **🌸 示範曲**、**🎹 MIDI 檔** 或 **📚 曲庫**。"
    )


def prepare_score(notes: list, practice_scope: str):
    """依練習範圍回傳 (score, chorus_start, chorus_end, audio_offset, mode)."""
    c0, c1 = detect_chorus_bounds(notes)
    if practice_scope == "僅副歌":
        return extract_section(notes, c0, c1), c0, c1, c0, "chorus"
    return notes, c0, c1, 0.0, "full"


AUDIO_SOURCES = [
    "📁 本機上傳",
    "🎹 MIDI 檔",
    "📚 曲庫",
    "🔍 搜尋樂譜",
    "🔗 直接音檔網址",
    "🌸 示範曲",
]

UPLOAD_TYPES = ["mp3", "wav", "m4a", "ogg", "flac", "aac", "webm"]


def ai_not_ready_message() -> str:
    return (
        "**無法 AI 抓譜**：TensorFlow / basic-pitch 尚未載入。"
        " 請先用「🌸 示範曲」「🎹 MIDI」「📚 曲庫」；雲端請確認 **Python 3.11**、**Memory 2GB+**，"
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


def load_midi_lesson(midi_path: str, title: str) -> None:
    """上傳或下載的 .mid → 鋼琴練習譜（不需 AI）。"""
    notes = midi_to_web_notes(midi_path)
    if not notes:
        raise ValueError("MIDI 檔內沒有可用的音符（可能為空檔或僅鼓組）。")
    if simplify_melody:
        notes = simplify_to_melody(notes)
    notes = filter_notes(notes, max_notes=1200)
    load_score_lesson(notes, title)


def load_score_lesson(
    notes: list,
    title: str,
    *,
    force_full: bool = False,
    audio_path: str | None = None,
) -> None:
    """從曲庫 / 樂譜搜尋載入（不需 AI）。"""
    if force_full:
        c0, c1 = detect_chorus_bounds(notes)
        score_data, chorus_start, chorus_end, audio_offset, practice_mode = (
            notes,
            c0,
            c1,
            0.0,
            "full",
        )
    else:
        score_data, chorus_start, chorus_end, audio_offset, practice_mode = prepare_score(
            notes, practice_scope
        )
    st.session_state["lesson_ready"] = True
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


# ── Header ──
st.markdown('<p class="hero-sub">音ノ手帖 · Oto no Techō</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-title">鍵盤上的練習筆記</p>', unsafe_allow_html=True)
st.caption("音源：上傳 · MIDI 檔 · 曲庫 · 搜尋樂譜 · 直接音檔網址 · 示範曲")

if IS_CLOUD:
    with st.expander("📱 手機隨地練指南（必讀）", expanded=True):
        st.markdown(mobile_practice_guide())

if st.session_state.get("lesson_ready") and st.session_state.get("lesson"):
    L0 = st.session_state["lesson"]
    st.success(f"🎹 已載入 **{L0['title']}** — 向下滑動到鍵盤即可繼續練（關閉分頁前不用重傳）。")
if not HAS_BASIC_PITCH:
    st.warning(
        "**AI 抓譜尚未就緒**（TensorFlow / basic-pitch 未載入）。"
        "仍可使用「示範曲」「MIDI」「曲庫」。雲端請確認：**Python 3.11**、**Memory 2GB+**，"
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
    with st.expander("📱 手機隨地練"):
        st.markdown(mobile_practice_guide())
    with st.expander("🎹 流行樂 MIDI 哪裡找？", expanded=False):
        st.markdown(midi_resources_guide_markdown())

# ── 音源選擇 ──
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ① 選擇音源")
_source_options = AUDIO_SOURCES
audio_source = st.radio(
    "音源類型",
    _source_options,
    horizontal=True,
    label_visibility="collapsed",
    key="audio_source_radio",
)
st.session_state["audio_source"] = audio_source

# ── 📁 本機上傳 ──
if audio_source == "📁 本機上傳":
    st.markdown("#### 📁 上傳音檔 ⭐ 隨地練首選")
    st.caption("**手機也可**：從「檔案」選 MP3，不需電腦。")
    upload_mode = st.radio(
        "上傳方式",
        ["選擇檔案（手機 / 電腦）", "麥克風錄音"],
        horizontal=True,
        key="upload_mode",
    )
    custom_title = st.text_input("歌曲名稱（選填）", placeholder="例：晴天")

    if upload_mode.startswith("選擇"):
        with st.expander("手機如何準備 MP3？"):
            st.markdown(
                "- **iPhone**：MP3 放到「檔案」App → 此處「Browse」選取\n"
                "- **Android**：從下載資料夾或檔案管理員選取\n"
                "- 已有 MP3 / WAV / M4A 即可\n"
                "- 想先玩：用 **🌸 示範曲** 零檔案開練"
            )
        uploaded = st.file_uploader(
            "點此選擇音檔（可從手機檔案 App）",
            type=UPLOAD_TYPES,
            key="upload_file",
        )
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
    else:
        st.caption("錄下參考旋律（副歌哼唱 15–30 秒），再 AI 抓譜。Android Chrome 較穩。")
        mic_widget = getattr(st, "audio_input", None) or getattr(
            st, "experimental_audio_input", None
        )
        if mic_widget is None:
            st.warning("此瀏覽器不支援網頁錄音，請改「選擇檔案」或示範曲。")
        else:
            recorded = mic_widget("按下錄音", key="mic_recording")
            if recorded is not None:
                st.audio(recorded)
                if st.button("用錄音抓譜", type="primary", key="btn_rec_upload"):
                    if not HAS_BASIC_PITCH:
                        st.error(ai_not_ready_message())
                    else:
                        name = getattr(recorded, "name", None) or "recording.wav"
                        path = save_audio_bytes(recorded.getvalue(), name)
                        title = custom_title.strip() or "錄音練習"
                        queue_ai_job({
                            "kind": "upload",
                            "path": path,
                            "title": title,
                        })

# ── 🎹 MIDI 檔 ──
elif audio_source == "🎹 MIDI 檔":
    st.markdown("#### 🎹 上傳 MIDI 檔")
    st.caption(
        "從 **BitMidi、FreeMidi、MuseScore、EOP、YouTube 說明欄** 等下載 `.mid` 後上傳。"
        "**不需 AI**，雲端最適合擴充流行歌庫。"
    )
    midi_title = st.text_input("歌曲名稱（選填）", placeholder="例：晴天", key="midi_title")
    midi_file = st.file_uploader(
        "選擇 .mid / .midi 檔",
        type=["mid", "midi"],
        key="midi_upload",
    )
    if midi_file and st.button("載入 MIDI 並練習", type="primary", key="btn_midi_load"):
        try:
            path = save_upload(midi_file)
            title = midi_title.strip() or midi_file.name
            load_midi_lesson(path, title)
            st.rerun()
        except Exception as e:
            st.error(str(e))
    with st.expander("🔗 還沒有 MIDI？去這些站搜尋", expanded=True):
        midi_search_q = st.text_input(
            "歌名",
            placeholder="例：周杰倫 晴天、Adele Hello",
            key="midi_link_query",
        )
        if midi_search_q.strip():
            for link in external_midi_search_links(midi_search_q):
                st.markdown(
                    f"**[{link['name']}]({link['url']})** · {link['region']}\n\n"
                    f"{link['hint']}"
                )

# ── 📚 曲庫 ──
elif audio_source == "📚 曲庫":
    st.markdown("#### 📚 線上曲庫")
    st.caption(
        "已轉好的樂譜（本機 `scores/` 或 GitHub）。**不需 AI**，"
        "雲端最穩。新增曲目：本機轉譜後將 JSON 放入 `scores/` 並 push。"
    )
    lib_q = st.text_input("篩選曲庫", placeholder="例：滄海、小星星", key="lib_filter")
    entries = search_catalog(lib_q) if lib_q.strip() else list_catalog_entries()
    if not entries:
        st.info("曲庫尚無曲目。可先載入示範曲，或執行 `python tools/export_scores.py` 產生 JSON。")
    else:
        labels = [catalog_entry_title(e) for e in entries]
        lib_pick = st.selectbox(
            "選擇曲目",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key="lib_pick",
        )
        ent = entries[lib_pick]
        tags = ", ".join(ent.get("tags") or [])
        if tags:
            st.caption(f"標籤：{tags}")
        if st.button("載入曲庫曲目", type="primary", key="btn_lib_load"):
            try:
                notes = load_score(ent["id"])
                force = ent["id"] == "xiaoaojianghu"
                load_score_lesson(
                    notes,
                    catalog_entry_title(ent),
                    force_full=force,
                )
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ── 🔍 搜尋樂譜 ──
elif audio_source == "🔍 搜尋樂譜":
    st.markdown("#### 🔍 搜尋現成樂譜並轉鋼琴譜")
    st.caption(
        "搜尋 **曲庫**、**BitMidi**、**IMSLP**、**GitHub ABC**，或貼 **和弦 / ABC / MIDI 網址**。"
        "也可先在外站下載 .mid → 用 **🎹 MIDI 檔** 上傳。"
    )
    sheet_q = st.text_input(
        "歌名 / 曲名",
        placeholder="例：Für Elise、滄海、folk tune",
        key="sheet_q",
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        src_local = st.checkbox("曲庫", value=True, key="src_local")
    with c2:
        src_bitmidi = st.checkbox("BitMidi", value=True, key="src_bitmidi")
    with c3:
        src_imslp = st.checkbox("IMSLP", value=True, key="src_imslp")
    with c4:
        src_gh = st.checkbox("GitHub ABC", value=True, key="src_gh")

    if sheet_q and st.button("搜尋樂譜", type="primary", key="btn_sheet_search"):
        with st.spinner("搜尋中…"):
            st.session_state["sheet_hits"] = search_all(
                sheet_q,
                use_local=src_local,
                use_bitmidi=src_bitmidi,
                use_imslp=src_imslp,
                use_github_abc=src_gh,
            )
            st.session_state["midi_ext_links"] = external_midi_search_links(sheet_q)

    if sheet_q.strip() and st.session_state.get("midi_ext_links"):
        with st.expander("🌐 更多 MIDI 站（手動下載後用 🎹 MIDI 檔 上傳）", expanded=True):
            for link in st.session_state["midi_ext_links"]:
                st.markdown(
                    f"**[{link['name']}]({link['url']})** · {link['region']} — {link['hint']}"
                )
            st.caption("華語論壇：**[廷廷的鋼琴窩 搜尋](https://www.tintinpiano.com/forum/search.php)**")

    hits: list[SheetHit] = st.session_state.get("sheet_hits", [])
    if hits:
        hit_labels = [h.label() for h in hits]
        hit_pick = st.selectbox(
            "搜尋結果",
            range(len(hit_labels)),
            format_func=lambda i: hit_labels[i],
            key="sheet_hit_pick",
        )
        h = hits[hit_pick]
        st.caption(h.description or h.url)
        if st.button("轉成鋼琴譜並練習", type="primary", key="btn_sheet_convert"):
            with st.spinner("轉換中…"):
                try:
                    notes, title = fetch_and_convert(h, simplify=simplify_melody)
                    load_score_lesson(notes, title)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    elif sheet_q and "sheet_hits" in st.session_state:
        st.warning("沒有找到結果，請改關鍵字或貼上樂譜內容。")

    with st.expander("📋 貼上樂譜（和弦 / ABC / MIDI 網址）", expanded=False):
        paste_kind = st.radio(
            "格式",
            ["吉他和弦 / 和弦譜", "ABC 簡譜文字", "MIDI 或 ABC 網址"],
            horizontal=True,
            key="paste_kind",
        )
        paste_text = st.text_area(
            "內容",
            height=140,
            placeholder="和弦例：Am G C F\n或貼 https://.../*.mid",
            key="paste_sheet",
        )
        if st.button("轉換並練習", key="btn_paste_convert"):
            kind_map = {
                "吉他和弦 / 和弦譜": "chord",
                "ABC 簡譜文字": "abc",
                "MIDI 或 ABC 網址": "url",
            }
            try:
                notes, title = convert_user_input(
                    paste_text,
                    kind_map[paste_kind],
                    simplify=simplify_melody,
                )
                load_score_lesson(notes, title)
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ── 🔗 直接音檔網址 ──
elif audio_source == "🔗 直接音檔網址":
    st.markdown("#### 直接音檔網址")
    st.caption(
        "貼上以 **.mp3 / .wav / .m4a** 結尾的直連網址。"
        "不支援 YouTube、Spotify 等串流平台。"
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
elif audio_source == "🌸 示範曲":
    st.markdown("#### 內建示範曲")
    st.caption(
        "不需 AI、不需網路，可直接練習鍵盤與下落音符。"
        "「滄海一聲笑」為完整版（主歌×3＋副歌＋尾奏，約 1 分 10 秒）。"
    )
    demo = st.selectbox(
        "選擇曲目",
        ["小星星", "笑傲江湖（滄海一聲笑·完整版）"],
        key="demo_pick",
    )
    if st.button("載入示範曲", type="primary", key="btn_demo"):
        demo_id = "xiaoaojianghu" if "笑傲" in demo else "twinkle"
        full = get_demo_score(demo_id)
        load_score_lesson(
            full,
            demo,
            force_full=(demo_id == "xiaoaojianghu"),
        )
        st.rerun()

else:
    st.warning("請選擇音源類型。")

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
                )
                title = job["title"]
            else:
                raise ValueError(f"未知工作類型：{job.get('kind')}")

            notes = run_ai_transcription(audio_path, simplify_melody)
            save_lesson(notes, title, audio_path)
            st.success(f"完成：{title}")
        except MediaFetchError as e:
            st.error(str(e))
            render_upload_fallback_guide()
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

    st.download_button(
        "⬇️ 匯出樂譜 JSON（可放入 scores/ 推上 GitHub）",
        data=export_notes_payload(
            L["score"],
            L["title"],
            {"source": L.get("source", ""), "exported_from": "app"},
        ),
        file_name=re.sub(r"[^\w\-]+", "_", L["title"])[:40] + ".json",
        mime="application/json",
        key="btn_export_score",
    )
    st.caption(
        "本機 MP3 + AI 抓譜 → 匯出 JSON → 放入 `scores/` 並 push，"
        "之後用 **📚 曲庫** 直接練。"
    )
