"""流行樂 MIDI 資源指南與外部搜尋連結（供 App 顯示，不自動爬取有版權站）。"""

from __future__ import annotations

import urllib.parse


def external_midi_search_links(query: str) -> list[dict]:
    """依歌名產生各站「搜尋頁」連結（使用者自行下載 MIDI 後上傳本 App）。"""
    q = query.strip()
    if not q:
        return []
    enc = urllib.parse.quote(q)
    enc_plus = urllib.parse.quote_plus(q)
    return [
        {
            "name": "BitMidi",
            "region": "歐美 · 懷舊流行",
            "url": f"https://bitmidi.com/search?q={enc}",
            "hint": "免費 .mid 直接下載，80–90 年代流行、搖滾、遊戲曲多",
        },
        {
            "name": "FreeMidi",
            "region": "歐美 · 依曲風分類",
            "url": f"https://freemidi.org/search?q={enc}",
            "hint": "Pop / Rock / Hip-Hop 分類齊全",
        },
        {
            "name": "MuseScore",
            "region": "全球 · 網友聽寫譜",
            "url": f"https://musescore.com/sheetmusic?text={enc}",
            "hint": "版本多；部分曲目下載 MIDI 可能需 Pro，可匯出後上傳",
        },
        {
            "name": "Everyone Piano (EOP)",
            "region": "華語 · 抖音 · 動漫",
            "url": f"http://www.everyonepiano.com/Search?term={enc}",
            "hint": "華語流行、動漫極多，常有 .mid 或可先下 .eop 再轉 MIDI",
        },
        {
            "name": "YouTube",
            "region": "華語 · 扒譜頻道",
            "url": f"https://www.youtube.com/results?search_query={enc_plus}+synthesia+piano+midi",
            "hint": "影片說明欄常有 MIDI 下載（Ru's Piano、SLSMusic 等）",
        },
        {
            "name": "IMSLP",
            "region": "古典 · 公有領域",
            "url": f"https://imslp.org/wiki/Special:Search?search={enc}&go=Go",
            "hint": "古典樂 MIDI 合法下載",
        },
    ]


def midi_resources_guide_markdown() -> str:
    return (
        "### 中文 / 亞洲流行（華語、J-Pop、K-Pop）\n"
        "| 來源 | 說明 |\n"
        "|------|------|\n"
        "| **廷廷的鋼琴窩 (Tintinpiano)** | 台灣老牌論壇，周杰倫、林俊傑、告五人等扒譜多，"
        "常附 MIDI / Overture 檔 → [論壇搜尋](https://www.tintinpiano.com/forum/search.php) |\n"
        "| **Everyone Piano** | 華語、抖音神曲、動漫量大 → 用上方 **EOP** 連結搜尋 |\n"
        "| **YouTube** | 搜尋「歌名 + Synthesia / 鋼琴 MIDI」→ 說明欄下載連結 |\n\n"
        "### 歐美與綜合題庫\n"
        "| 來源 | 說明 |\n"
        "|------|------|\n"
        "| **BitMidi** | 10 萬+ 免費 .mid，80–90 經典流行、搖滾 |\n"
        "| **FreeMidi** | 依 Pop / Rock / 歌手字母瀏覽 |\n"
        "| **MuseScore** | 全球最大分享社群，多版本、多難度（注意版權與 Pro） |\n\n"
        "### 接到本 App 的標準流程\n"
        "1. 在上述網站 **下載 `.mid`**（請尊重版權，個人練習為宜）\n"
        "2. 本頁選 **🎹 MIDI 檔** → 上傳 → **立即練習**（不需 AI、不需 YouTube）\n"
        "3. 滿意後按練習區 **匯出 JSON** → 放入 `scores/` push GitHub → 下次用 **📚 曲庫**\n\n"
        "**注意：** 本 App **不會**自動從這些網站批量下載有版權的流行歌 MIDI，"
        "以避免違反服務條款；僅提供搜尋連結與本機/曲庫轉換。"
    )
