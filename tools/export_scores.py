#!/usr/bin/env python3
"""將內建示範曲匯出為 scores/*.json（在本機專案根目錄執行）。"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from audio_processor import get_demo_score
from score_library import SCORES_DIR, export_notes_payload


def main() -> None:
    os.makedirs(SCORES_DIR, exist_ok=True)
    for sid, title in (
        ("twinkle", "小星星"),
        ("xiaoaojianghu", "笑傲江湖（滄海一聲笑·完整版）"),
    ):
        notes = get_demo_score(sid)
        path = os.path.join(SCORES_DIR, f"{sid}.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(export_notes_payload(notes, title, {"id": sid, "source": "demo"}))
        print(f"Wrote {path} ({len(notes)} notes)")


if __name__ == "__main__":
    main()
