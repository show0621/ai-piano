"""本機 / GitHub 曲庫：預先轉好的樂譜 JSON。"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_DIR = os.path.join(APP_DIR, "scores")
INDEX_PATH = os.path.join(SCORES_DIR, "index.json")

_INDEX_CACHE: dict | None = None


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip()
    return v or None


def get_github_raw_base() -> str | None:
    """可選：Streamlit Secrets [scores] github_raw_base 或環境變數。"""
    base = _clean(os.environ.get("SCORES_GITHUB_RAW_BASE"))
    if base:
        return base.rstrip("/")
    try:
        import streamlit as st

        block = st.secrets.get("scores")
        if block and hasattr(block, "get"):
            base = _clean(block.get("github_raw_base"))
            if base:
                return base.rstrip("/")
    except Exception:
        pass
    return None


def _http_get_json(url: str, timeout: float = 12.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ai-piano-score-library/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_index() -> dict:
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE

    if os.path.isfile(INDEX_PATH):
        with open(INDEX_PATH, encoding="utf-8") as f:
            _INDEX_CACHE = json.load(f)
            return _INDEX_CACHE

    remote = get_github_raw_base()
    if remote:
        try:
            _INDEX_CACHE = _http_get_json(f"{remote}/index.json")
            return _INDEX_CACHE
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            pass

    _INDEX_CACHE = {"version": 1, "scores": []}
    return _INDEX_CACHE


def list_catalog_entries() -> list[dict]:
    idx = load_index()
    return list(idx.get("scores") or [])


def search_catalog(query: str, limit: int = 20) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return list_catalog_entries()[:limit]
    out = []
    for ent in list_catalog_entries():
        hay = " ".join(
            str(ent.get(k, ""))
            for k in ("id", "title", "title_en", "tags", "artist")
        ).lower()
        if q in hay or any(w in hay for w in q.split() if len(w) > 1):
            out.append(ent)
        if len(out) >= limit:
            break
    return out


def _normalize_notes(raw: list) -> list:
    notes = []
    for n in raw:
        pitch = int(n["pitch"])
        start = float(n["start_time"])
        dur = float(n.get("duration", n.get("end_time", start) - start))
        notes.append({
            "pitch": pitch,
            "note_name": n.get("note_name") or "",
            "start_time": round(start, 3),
            "end_time": round(start + dur, 3),
            "duration": round(dur, 3),
            "isHit": False,
        })
    if notes and not notes[0].get("note_name"):
        import pretty_midi

        for n in notes:
            n["note_name"] = pretty_midi.note_number_to_name(n["pitch"])
    return notes


def load_score(score_id: str) -> list:
    """載入樂譜；優先本機 scores/{id}.json，其次 GitHub raw，最後內建 demo。"""
    local_path = os.path.join(SCORES_DIR, f"{score_id}.json")
    if os.path.isfile(local_path):
        with open(local_path, encoding="utf-8") as f:
            data = json.load(f)
        return _normalize_notes(data.get("notes", data))

    remote = get_github_raw_base()
    if remote:
        try:
            data = _http_get_json(f"{remote}/{score_id}.json")
            return _normalize_notes(data.get("notes", data))
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            pass

    try:
        from audio_processor import get_demo_score

        return get_demo_score(score_id)
    except KeyError:
        pass

    raise FileNotFoundError(f"找不到曲庫曲目：{score_id}")


def export_notes_payload(notes: list, title: str, meta: dict | None = None) -> str:
    """供下載 / 放入 scores/ 推 GitHub。"""
    payload = {
        "title": title,
        "notes": [
            {
                "pitch": n["pitch"],
                "start_time": n["start_time"],
                "end_time": n.get("end_time", n["start_time"] + n["duration"]),
                "duration": n["duration"],
            }
            for n in notes
        ],
    }
    if meta:
        payload["meta"] = meta
    return json.dumps(payload, ensure_ascii=False, indent=2)


def catalog_entry_title(ent: dict) -> str:
    return str(ent.get("title") or ent.get("id", "未命名"))
