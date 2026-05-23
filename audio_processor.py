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


def download_youtube_audio(url: str, output_path: str) -> str:
    """將 YouTube 連結下載為 MP3，回傳實際檔案路徑。"""
    import yt_dlp

    out_base = output_path.rsplit(".", 1)[0]
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_base + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    mp3_path = out_base + ".mp3"
    if os.path.exists(mp3_path):
        return mp3_path

    # 若未轉檔成功，找同目錄最新音檔
    folder = os.path.dirname(out_base) or "."
    base = os.path.basename(out_base)
    for name in os.listdir(folder):
        if name.startswith(base) and name.endswith((".mp3", ".m4a", ".wav", ".webm")):
            return os.path.join(folder, name)
    raise FileNotFoundError("無法下載 YouTube 音檔，請確認已安裝 ffmpeg。")


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


def get_demo_score(demo_id: str) -> list:
    """內建示範曲（不依賴 AI）。"""
    demos = {
        "twinkle": [
            (60, 0.0, 0.4), (60, 0.5, 0.4), (67, 1.0, 0.4), (67, 1.5, 0.4),
            (69, 2.0, 0.4), (69, 2.5, 0.4), (67, 3.0, 0.8),
        ],
        "xiaoaojianghu": [
            (69, 0.0, 0.42), (69, 0.42, 0.42), (67, 0.84, 0.42), (64, 1.26, 0.42),
            (67, 1.68, 0.42), (69, 2.10, 0.42), (72, 2.52, 0.42), (72, 2.94, 0.42),
            (74, 3.36, 0.42), (72, 3.78, 0.42), (69, 4.20, 0.42),
            (67, 4.62, 0.42), (67, 5.04, 0.42), (64, 5.46, 0.42), (62, 5.88, 0.42),
            (64, 6.30, 0.42), (67, 6.72, 0.42), (69, 7.14, 0.42), (67, 7.56, 0.42),
            (64, 7.98, 0.42),
        ],
    }
    raw = demos.get(demo_id, demos["twinkle"])
    notes = []
    for pitch, start, dur in raw:
        notes.append({
            "pitch": pitch,
            "note_name": pretty_midi.note_number_to_name(pitch),
            "start_time": start,
            "end_time": round(start + dur, 3),
            "duration": dur,
            "isHit": False,
            "isMissed": False,
        })
    return notes
