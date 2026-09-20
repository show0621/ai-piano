#!/usr/bin/env python3
"""把 frontend.html + scores/jianndanai.json 編成可雙擊開啟的 play.html。"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend.html")
SCORE = os.path.join(ROOT, "scores", "jianndanai.json")
OUT = os.path.join(ROOT, "play.html")


def main() -> None:
    with open(FRONTEND, encoding="utf-8") as f:
        html = f.read()
    with open(SCORE, encoding="utf-8") as f:
        data = json.load(f)

    notes = data.get("notes", data)
    title = data.get("title") or "簡單愛"
    score_id = (data.get("meta") or {}).get("id") or "jianndanai"

    html = html.replace("{{SCORE_JSON_PLACEHOLDER}}", json.dumps(notes, ensure_ascii=False))
    html = html.replace("{{AUDIO_SRC_PLACEHOLDER}}", "")
    html = html.replace("{{SONG_TITLE}}", title.replace('"', "'"))
    html = html.replace("{{CHORUS_START}}", "0")
    html = html.replace("{{CHORUS_END}}", "0")
    html = html.replace("{{PRACTICE_MODE}}", "full")
    html = html.replace("{{AUDIO_OFFSET}}", "0")
    html = html.replace("{{AUTO_PLAY}}", "false")
    html = html.replace("{{SCORE_ID}}", score_id)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {OUT} ({len(notes)} notes)")


if __name__ == "__main__":
    main()
