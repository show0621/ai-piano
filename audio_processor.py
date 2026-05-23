import os

import pretty_midi

# basic-pitch 體積大，允許未安裝時降級
try:
    from basic_pitch.inference import predict_and_save
    HAS_BASIC_PITCH = True
except ImportError:
    HAS_BASIC_PITCH = False

MIN_PITCH = 60   # C4（雙八度下限）
MAX_PITCH = 83   # B5（雙八度上限）
MIN_DURATION = 0.08


def filter_notes(notes: list, max_notes: int = 800) -> list:
    """過濾雜訊與過多音符，適合初學者練習。"""
    cleaned = []
    for n in notes:
        pitch = n.get("pitch", 0)
        dur = n.get("duration", 0)
        if pitch < MIN_PITCH or pitch > MAX_PITCH:
            continue
        if dur < MIN_DURATION:
            continue
        cleaned.append(n)

    cleaned.sort(key=lambda x: x["start_time"])

    if len(cleaned) > max_notes:
        step = len(cleaned) / max_notes
        sampled = [cleaned[int(i * step)] for i in range(max_notes)]
        cleaned = sampled

    return cleaned


def simplify_to_melody(notes: list) -> list:
    """將複音簡化為主旋律：每個時間窗口只保留最高音。"""
    if not notes:
        return notes

    window = 0.12
    sorted_notes = sorted(notes, key=lambda x: x["start_time"])
    melody = []
    i = 0
    while i < len(sorted_notes):
        t0 = sorted_notes[i]["start_time"]
        group = []
        while i < len(sorted_notes) and sorted_notes[i]["start_time"] < t0 + window:
            group.append(sorted_notes[i])
            i += 1
        if group:
            melody.append(max(group, key=lambda x: x["pitch"]))
    return melody


def midi_to_web_notes(midi_path: str) -> list:
    pm = pretty_midi.PrettyMIDI(midi_path)
    web_notes = []

    for instrument in pm.instruments:
        if instrument.is_drum:
            continue
        for note in instrument.notes:
            web_notes.append({
                "pitch": int(note.pitch),
                "note_name": pretty_midi.note_number_to_name(note.pitch),
                "start_time": round(note.start, 3),
                "end_time": round(note.end, 3),
                "duration": round(max(note.end - note.start, MIN_DURATION), 3),
                "isHit": False,
                "isMissed": False,
            })

    return sorted(web_notes, key=lambda x: x["start_time"])


def process_audio_to_json(
    audio_file_path: str,
    output_dir: str = "./output/",
    simplify: bool = True,
) -> list:
    """音檔 → basic-pitch → MIDI → 前端 JSON 樂譜。"""
    if not HAS_BASIC_PITCH:
        raise RuntimeError(
            "未安裝 basic-pitch。請執行: pip install basic-pitch"
        )

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    predict_and_save(
        audio_path_list=[audio_file_path],
        output_directory=output_dir,
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
    )

    base_name = os.path.basename(audio_file_path).rsplit(".", 1)[0]
    # 移除 temp_ 前綴
    if base_name.startswith("temp_"):
        base_name = base_name[5:]
    midi_path = os.path.join(output_dir, f"{base_name}_basic_pitch.mid")

    if not os.path.exists(midi_path):
        # 嘗試用完整檔名
        alt = os.path.join(
            output_dir,
            f"{os.path.basename(audio_file_path).rsplit('.', 1)[0]}_basic_pitch.mid",
        )
        midi_path = alt if os.path.exists(alt) else midi_path

    if not os.path.exists(midi_path):
        return []

    notes = midi_to_web_notes(midi_path)
    if simplify:
        notes = simplify_to_melody(notes)
    return filter_notes(notes)


_JIANPU_PITCH = {1: 60, 2: 62, 3: 64, 4: 65, 5: 67, 6: 69, 7: 71}
_JIANPU_HIGH = {1: 12, 2: 12}  # 高音 1、2 → C5、D5

# 笑傲江湖《滄海一聲笑》C 調簡譜（1' 2' 為高八度）
_XIAOAO_VERSE = """
6 6 5 3 5 6 1' 1' 2' 1' 6
5 5 3 2 3 5 6 5 3
2 3 2 3 5 6 1' 2' 1' 6 5 3
5 5 3 2 3 5 6 5 3 2 1 2 3
"""

_XIAOAO_OUTRO = """
6 - - 5 3 5 6 1' - 2' 1' 6 -
5 5 3 2 3 5 6 - 3 2 1 - -
"""


def _parse_jianpu(jianpu: str, tempo: float = 0.42) -> list[tuple[int, float, float]]:
    """將簡譜字串轉為 (midi, start, duration) 列表。"""
    t = 0.0
    out: list[tuple[int, float, float]] = []
    for token in jianpu.replace("|", " ").split():
        token = token.strip()
        if not token:
            continue
        if token in ("-", "0", "·", "."):
            t += tempo
            continue
        high = token.endswith("'") or token.endswith("’")
        num_s = token.rstrip("'’")
        if not num_s.isdigit():
            continue
        n = int(num_s)
        if n < 1 or n > 7:
            continue
        pitch = _JIANPU_PITCH[n]
        if high:
            pitch += _JIANPU_HIGH.get(n, 0)
        out.append((pitch, t, tempo))
        t += tempo
    return out


def _xiaoaojianghu_full_raw(tempo: float = 0.42) -> list[tuple[int, float, float]]:
    """完整曲：主歌×3 + 副歌 + 尾奏（約 90 秒）。"""
    verse = _parse_jianpu(_XIAOAO_VERSE, tempo)
    verse_len = verse[-1][1] + verse[-1][2] if verse else 0.0
    gap = tempo * 2  # 段間休止

    raw: list[tuple[int, float, float]] = []
    offset = 0.0
    for _ in range(3):
        for pitch, start, dur in verse:
            raw.append((pitch, start + offset, dur))
        offset += verse_len + gap

    for pitch, start, dur in verse:
        raw.append((pitch, start + offset, dur))
    offset += verse_len + gap * 2

    for pitch, start, dur in _parse_jianpu(_XIAOAO_OUTRO, tempo):
        raw.append((pitch, start + offset, dur))
    return raw


def _raw_to_notes(raw: list[tuple[int, float, float]]) -> list:
    notes = []
    for pitch, start, dur in raw:
        notes.append({
            "pitch": pitch,
            "note_name": pretty_midi.note_number_to_name(pitch),
            "start_time": round(start, 3),
            "end_time": round(start + dur, 3),
            "duration": dur,
            "isHit": False,
        })
    return notes


def get_demo_score(demo_id: str) -> list:
    """內建示範曲（不依賴 AI）。"""
    if demo_id == "xiaoaojianghu":
        return _raw_to_notes(_xiaoaojianghu_full_raw())
    raw = [
        (60, 0.0, 0.4), (60, 0.5, 0.4), (67, 1.0, 0.4), (67, 1.5, 0.4),
        (69, 2.0, 0.4), (69, 2.5, 0.4), (67, 3.0, 0.8),
    ]
    return _raw_to_notes(raw)


def get_song_duration(notes: list) -> float:
    if not notes:
        return 0.0
    return max(n["start_time"] + n["duration"] for n in notes)


def detect_chorus_bounds(notes: list, window: float = 28.0) -> tuple[float, float]:
    """
    以音符密度啟發式估算副歌段落（常見於中後段高密度區）。
    回傳 (start_sec, end_sec)。
    """
    if not notes:
        return 0.0, 30.0

    total = get_song_duration(notes)
    if total < window + 5:
        return 0.0, total

    search_from = total * 0.22
    search_to = max(search_from + window, total * 0.88)
    step = 4.0

    best_start = search_from
    best_score = -1.0
    t = search_from
    while t + window <= search_to:
        seg = [n for n in notes if t <= n["start_time"] < t + window]
        if not seg:
            t += step
            continue
        density = len(seg) / window
        pitch_variety = len({n["pitch"] for n in seg}) / 14.0
        center_bias = 1.0 - abs((t + window / 2) - total * 0.55) / (total * 0.5)
        score = density * 0.55 + pitch_variety * 0.25 + center_bias * 0.2
        if score > best_score:
            best_score = score
            best_start = t
        t += step

    end = min(best_start + window, total)
    return round(best_start, 2), round(end, 2)


def extract_section(notes: list, start: float, end: float) -> list:
    """截取段落並將時間軸归零。"""
    sliced = []
    for n in notes:
        if n["start_time"] < start or n["start_time"] >= end:
            continue
        item = dict(n)
        item["start_time"] = round(n["start_time"] - start, 3)
        item["end_time"] = round(n.get("end_time", n["start_time"] + n["duration"]) - start, 3)
        item["duration"] = round(n["duration"], 3)
        item["isHit"] = False
        item["isMissed"] = False
        sliced.append(item)
    return sliced
