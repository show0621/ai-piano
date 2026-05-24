import inspect
import os

import pretty_midi

# basic-pitch 體積大，允許未安裝時降級
try:
    from basic_pitch.inference import predict_and_save

    HAS_BASIC_PITCH = True
    _PREDICT_AND_SAVE_SIG = inspect.signature(predict_and_save)
except ImportError:
    HAS_BASIC_PITCH = False
    predict_and_save = None  # type: ignore[misc, assignment]
    _PREDICT_AND_SAVE_SIG = None

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

    predict_kwargs = {
        "audio_path_list": [audio_file_path],
        "output_directory": output_dir,
        "save_midi": True,
        "sonify_midi": False,
        "save_model_outputs": False,
        "save_notes": False,
    }
    if _PREDICT_AND_SAVE_SIG and "model_or_model_path" in _PREDICT_AND_SAVE_SIG.parameters:
        from basic_pitch import ICASSP_2022_MODEL_PATH

        predict_kwargs["model_or_model_path"] = ICASSP_2022_MODEL_PATH
    predict_and_save(**predict_kwargs)

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
_JIANPU_HIGH = {1: 12, 2: 12, 3: 12, 4: 12, 5: 12, 6: 12, 7: 12}  # x' → 高八度

# 調性：1=主音所在八度（midi），其後為 1〜7 音程（半音）
_KEY_SCALES: dict[str, tuple[int, list[int]]] = {
    "C": (60, [0, 2, 4, 5, 7, 9, 11]),
    "Dm": (62, [0, 2, 3, 5, 7, 8, 10]),
    "Am": (69, [0, 2, 3, 5, 7, 8, 10]),  # 主歌音域偏高，A4 起
    "Em": (64, [0, 2, 3, 5, 7, 8, 10]),  # E4 起（柯南主題等）
}

DEMO_CATALOG = [
    {"id": "twinkle", "title": "小星星", "artist": "兒歌 · 範例", "full": False},
    {"id": "jianndanai", "title": "簡單愛", "artist": "周杰倫 · 範例", "full": True},
    # 兒歌
    {"id": "liangzhilaohu", "title": "兩隻老虎", "artist": "兒歌", "full": False},
    {"id": "xiaomifeng", "title": "小蜜蜂", "artist": "兒歌", "full": False},
    {"id": "happy_birthday", "title": "生日快樂", "artist": "兒歌", "full": False},
    {"id": "fenshuajiang", "title": "粉刷匠", "artist": "兒歌", "full": False},
    {"id": "molihua", "title": "茉莉花", "artist": "民歌", "full": False},
    # 動畫
    {"id": "doraemon", "title": "哆啦A夢", "artist": "動畫主題", "full": False},
    {"id": "maruko", "title": "櫻桃小丸子", "artist": "動畫主題", "full": False},
    {"id": "totoro", "title": "龍貓", "artist": "吉卜力", "full": False},
    {"id": "conan", "title": "名偵探柯南", "artist": "動畫主題", "full": False},
    {"id": "anpanman", "title": "麵包超人", "artist": "動畫主題", "full": False},
    # 古典（公版）
    {"id": "canon", "title": "卡農", "artist": "Pachelbel", "full": False},
    {"id": "fur_elise", "title": "致愛麗絲", "artist": "Beethoven", "full": False},
    {"id": "ode_to_joy", "title": "歡樂頌", "artist": "Beethoven", "full": False},
    {"id": "beethoven_fifth", "title": "命運交響曲（主題）", "artist": "Beethoven", "full": False},
]


def _parse_note_token(
    token: str,
    *,
    key: str = "C",
) -> tuple[int, float] | None:
    """解析單音：5、5'、5#、5b、5_、5.、5--。回傳 (midi, 時值倍率)。"""
    if not token or token in ("|",):
        return None
    if token in ("-", "0", "·"):
        return None

    high = "'" in token or "’" in token
    low = False
    body = token.replace("'", "").replace("’", "")
    if body.startswith("."):
        low = True
        body = body[1:]
    mult = 1.0
    acc = 0

    for ch in ("#", "＃", "♯"):
        if ch in body:
            acc += 1
            body = body.replace(ch, "")
    for ch in ("b", "B", "♭"):
        if ch in body:
            acc -= 1
            body = body.replace(ch, "")

    if body.endswith("--"):
        mult *= 2.0
        body = body[:-2]
    if body.endswith("."):
        mult *= 1.5
        body = body[:-1]
    while body.endswith("_"):
        mult *= 0.5
        body = body[:-1]

    if not body.isdigit():
        return None
    n = int(body)
    if n < 1 or n > 7:
        return None

    if key in _KEY_SCALES:
        base, steps = _KEY_SCALES[key]
        pitch = base + steps[n - 1] + acc
        if high:
            pitch += 12
        if low:
            pitch -= 12
    else:
        pitch = _JIANPU_PITCH[n] + acc
        if high:
            pitch += _JIANPU_HIGH.get(n, 0)
        if low:
            pitch -= 12

    while pitch > MAX_PITCH:
        pitch -= 12
    while pitch < MIN_PITCH:
        pitch += 12
    return pitch, mult


def _parse_jianpu(
    jianpu: str,
    beat_sec: float = 0.38,
    *,
    key: str = "C",
) -> list[tuple[int, float, float]]:
    """將簡譜字串轉為 (midi, start, duration)。beat_sec = 一拍秒數。"""
    t = 0.0
    out: list[tuple[int, float, float]] = []
    cur_key = key

    for line in jianpu.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("K:"):
            cur_key = line.split(":", 1)[1].strip()
            continue
        if line.upper().startswith("Q:"):
            try:
                bpm = float(line.split(":", 1)[1].strip())
                if bpm > 20:
                    beat_sec = 60.0 / bpm
            except ValueError:
                pass
            continue

        for token in line.replace("|", " ").split():
            token = token.strip()
            if not token:
                continue
            if token in ("-", "0", "·") or token == ".":
                t += beat_sec
                continue

            parsed = _parse_note_token(token, key=cur_key)
            if parsed is None:
                t += beat_sec
                continue
            pitch, mult = parsed
            dur = beat_sec * mult
            out.append((pitch, t, dur))
            t += dur

    return out


def _build_jianpu_score(
    jianpu: str,
    tempo: float = 0.45,
    *,
    repeat: int = 1,
    gap_beats: int = 2,
    key: str = "C",
) -> list:
    """將一段簡譜重複拼接為可練習曲。"""
    section = _parse_jianpu(jianpu, tempo, key=key)
    if not section:
        return []
    seg_len = section[-1][1] + section[-1][2]
    gap = tempo * gap_beats
    raw: list[tuple[int, float, float]] = []
    offset = 0.0
    for _ in range(max(1, repeat)):
        for pitch, start, dur in section:
            raw.append((pitch, start + offset, dur))
        offset += seg_len + gap
    return _raw_to_notes(raw)


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
    """內建示範曲（不依賴 AI）。簡單愛優先讀專案內 周杰倫簡單愛.mid，其次 scores/jianndanai.json。"""
    if demo_id == "jianndanai":
        root = os.path.dirname(os.path.abspath(__file__))
        user_mid = os.path.join(root, "周杰倫簡單愛.mid")
        if os.path.isfile(user_mid):
            notes = midi_to_web_notes(user_mid)
            notes = filter_notes(notes, max_notes=1200)
            return simplify_to_melody(notes)
        json_path = os.path.join(root, "scores", "jianndanai.json")
        if os.path.isfile(json_path):
            from score_library import load_score

            return load_score("jianndanai")

    from demo_melodies import DEMO_BUILDERS

    build = DEMO_BUILDERS.get(demo_id)
    if build:
        return build()
    raise KeyError(f"未知示範曲：{demo_id}")


def get_demo_meta(demo_id: str) -> dict | None:
    for item in DEMO_CATALOG:
        if item["id"] == demo_id:
            return item
    return None


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
