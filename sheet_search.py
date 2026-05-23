"""線上搜尋既有樂譜（IMSLP、GitHub ABC 等）並轉為鋼琴練習譜。"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from score_convert import convert_sheet, guess_format_from_url, notes_from_midi_bytes
from score_library import search_catalog

_USER_AGENT = "ai-piano-sheet-search/1.0"


@dataclass
class SheetHit:
    hit_id: str
    title: str
    source: str
    fmt: str
    url: str
    description: str = ""

    def label(self) -> str:
        return f"[{self.source}] {self.title} ({self.fmt})"


def _fetch_bytes(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _fetch_text(url: str, timeout: float = 20.0) -> str:
    return _fetch_bytes(url, timeout).decode("utf-8", errors="replace")


def search_local_catalog(query: str, limit: int = 10) -> list[SheetHit]:
    hits = []
    for ent in search_catalog(query, limit=limit):
        sid = ent.get("id", "")
        hits.append(
            SheetHit(
                hit_id=f"local:{sid}",
                title=str(ent.get("title") or sid),
                source="曲庫",
                fmt="json",
                url=f"score://{sid}",
                description=", ".join(ent.get("tags") or []) or "本機 / GitHub 曲庫",
            )
        )
    return hits


def search_imslp(query: str, limit: int = 6) -> list[SheetHit]:
    q = urllib.parse.quote(query.strip())
    api = (
        "https://imslp.org/api.php?action=query&list=search"
        f"&srsearch={q}&srlimit={limit}&format=json"
    )
    try:
        data = json.loads(_fetch_text(api, timeout=15))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []

    hits: list[SheetHit] = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "").replace("IMSLP:", "")
        page_url = "https://imslp.org/wiki/" + urllib.parse.quote(
            item.get("title", "").replace(" ", "_")
        )
        hits.append(
            SheetHit(
                hit_id=f"imslp:{item.get('pageid', title)}",
                title=title,
                source="IMSLP",
                fmt="page",
                url=page_url,
                description="公有領域古典樂譜 · 將嘗試抓取頁面中的 MIDI",
            )
        )
    return hits


def _imslp_midi_links_from_html(html: str) -> list[str]:
    links = re.findall(
        r'href="(https?://[^"]+\.(?:mid|midi))"',
        html,
        re.I,
    )
    links += re.findall(
        r'href="(/wiki/Special:ReverseLookup/[^"]+\.(?:mid|midi))"',
        html,
        re.I,
    )
    out = []
    for u in links:
        if u.startswith("/"):
            u = "https://imslp.org" + u
        out.append(u)
    return list(dict.fromkeys(out))[:5]


def search_github_abc(query: str, limit: int = 6) -> list[SheetHit]:
    q = urllib.parse.quote(f"{query} extension:abc")
    url = f"https://api.github.com/search/code?q={q}&per_page={limit}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []

    hits: list[SheetHit] = []
    for item in data.get("items", []):
        repo = item.get("repository", {}).get("full_name", "")
        path = item.get("path", "")
        name = item.get("name", path)
        raw = item.get("html_url", "").replace(
            "github.com", "raw.githubusercontent.com"
        ).replace("/blob/", "/")
        if "/blob/" in item.get("html_url", ""):
            raw = item["html_url"].replace(
                "https://github.com/",
                "https://raw.githubusercontent.com/",
            ).replace("/blob/", "/")
        hits.append(
            SheetHit(
                hit_id=f"github:{item.get('sha', name)}",
                title=f"{name} ({repo})",
                source="GitHub ABC",
                fmt="abc",
                url=raw,
                description="開源 ABC 檔 · 將轉為鋼琴主旋律",
            )
        )
    return hits


def search_bitmidi(query: str, limit: int = 8) -> list[SheetHit]:
    """
    嘗試解析 BitMidi 搜尋頁（若網站改版可能失效）。
    失敗時請改用手動下載 MIDI 後上傳。
    """
    q = query.strip()
    if not q:
        return []
    url = f"https://bitmidi.com/search?q={urllib.parse.quote(q)}"
    try:
        html = _fetch_text(url)
    except (urllib.error.URLError, TimeoutError):
        return []

    hits: list[SheetHit] = []
    seen: set[str] = set()
    for path in re.findall(r'"(/upload/\d+/[^"]+\.mid)"', html, re.I):
        if path in seen:
            continue
        seen.add(path)
        title = path.split("/")[-1].replace(".mid", "").replace("-", " ")
        hits.append(
            SheetHit(
                hit_id=f"bitmidi:{path}",
                title=title,
                source="BitMidi",
                fmt="midi",
                url="https://bitmidi.com" + path,
                description="免費 MIDI · 可直接轉鋼琴譜",
            )
        )
        if len(hits) >= limit:
            break
    return hits


def search_all(
    query: str,
    *,
    use_local: bool = True,
    use_bitmidi: bool = True,
    use_imslp: bool = True,
    use_github_abc: bool = True,
    limit_per_source: int = 6,
) -> list[SheetHit]:
    if not query.strip():
        return []
    hits: list[SheetHit] = []
    if use_local:
        hits.extend(search_local_catalog(query, limit=limit_per_source))
    if use_bitmidi:
        hits.extend(search_bitmidi(query, limit=limit_per_source))
    if use_imslp:
        hits.extend(search_imslp(query, limit=limit_per_source))
    if use_github_abc:
        hits.extend(search_github_abc(query, limit=limit_per_source))
    return hits


def fetch_and_convert(hit: SheetHit, *, simplify: bool = True) -> tuple[list, str]:
    """下載並轉換為音符列表。"""
    if hit.url.startswith("score://"):
        from score_library import load_score

        sid = hit.url.replace("score://", "")
        return load_score(sid), hit.title

    if hit.fmt == "page" and hit.source == "IMSLP":
        html = _fetch_text(hit.url)
        mids = _imslp_midi_links_from_html(html)
        if not mids:
            raise ValueError(
                "此 IMSLP 頁面找不到 MIDI 檔。"
                "請改選其他曲目，或貼上直接 MIDI / ABC 連結。"
            )
        data = _fetch_bytes(mids[0])
        notes = notes_from_midi_bytes(data, simplify=simplify)
        return notes, hit.title + " (MIDI)"

    if hit.fmt == "json" and hit.source == "曲庫":
        from score_library import load_score

        sid = hit.hit_id.split(":", 1)[-1]
        return load_score(sid), hit.title

    data = _fetch_bytes(hit.url)
    fmt = hit.fmt if hit.fmt not in ("page", "auto") else guess_format_from_url(hit.url)
    if fmt == "musicxml":
        raise ValueError(
            "此連結為 MusicXML，目前請改選 MIDI 或 ABC，"
            "或在本機用 MuseScore 匯出 MIDI 後上傳。"
        )
    if fmt == "abc":
        notes = convert_sheet(data.decode("utf-8", errors="replace"), "abc")
    else:
        notes = convert_sheet(data, "midi", simplify=simplify)
    return notes, hit.title


def convert_user_input(
    text: str,
    input_kind: str,
    *,
    simplify: bool = True,
) -> tuple[list, str]:
    """使用者貼上：和弦譜 / ABC / MIDI URL。"""
    text = text.strip()
    if not text:
        raise ValueError("內容為空")

    if input_kind == "chord":
        return convert_sheet(text, "chord"), "和弦練習譜"

    if input_kind == "abc":
        return convert_sheet(text, "abc"), "ABC 樂譜"

    if input_kind.startswith("url"):
        url = text.splitlines()[0].strip()
        fmt = guess_format_from_url(url)
        data = _fetch_bytes(url)
        if fmt == "abc":
            notes = convert_sheet(data.decode("utf-8", errors="replace"), "abc")
        else:
            notes = convert_sheet(data, "midi", simplify=simplify)
        return notes, url.split("/")[-1][:40]

    raise ValueError(f"未知輸入類型：{input_kind}")
