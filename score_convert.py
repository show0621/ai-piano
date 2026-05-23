"""將 MIDI / ABC / 和弦譜等轉為 App 使用的鋼琴音符 JSON。"""

from __future__ import annotations

import io
import re
import tempfile
from typing import BinaryIO
from urllib.parse import urlparse

import pretty_midi

from audio_processor import MIN_PITCH, MAX_PITCH, filter_notes, midi_to_web_notes

# 常見和弦 → MIDI（C4–G4 區域，可彈）
_CHORD_PATTERNS: list[tuple[re.Pattern, list[int]]] = [
    (re.compile(r"^A#m$|^Bbmin$", re.I), [58, 61, 65]),
    (re.compile(r"^Am$|^Amin$", re.I), [57, 60, 64]),
    (re.compile(r"^A$", re.I), [57, 61, 64]),
    (re.compile(r"^Bbm$", re.I), [58, 61, 65]),
    (re.compile(r"^Bm$", re.I), [59, 62, 66]),
    (re.compile(r"^B$", re.I), [59, 63, 66]),
    (re.compile(r"^C#m$", re.I), [61, 64, 67]),
    (re.compile(r"^Cm$", re.I), [60, 63, 67]),
    (re.compile(r"^C$", re.I), [60, 64, 67]),
    (re.compile(r"^D#m$|^Ebm$", re.I), [63, 66, 70]),
    (re.compile(r"^Dm$", re.I), [62, 65, 69]),
    (re.compile(r"^D$", re.I), [62, 66, 69]),
    (re.compile(r"^Em$", re.I), [64, 67, 71]),
    (re.compile(r"^E$", re.I), [64, 68, 71]),
    (re.compile(r"^F#m$|^Gbm$", re.I), [66, 69, 73]),
    (re.compile(r"^Fm$", re.I), [65, 68, 72]),
    (re.compile(r"^F$", re.I), [65, 69, 72]),
    (re.compile(r"^G#m$|^Abm$", re.I), [68, 71, 75]),
    (re.compile(r"^Gm$", re.I), [67, 70, 74]),
    (re.compile(r"^G$", re.I), [67, 71, 74]),
]

_ABC_PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_CHORD_TOKEN = re.compile(
    r"\[([A-G][#b]?m?(?:aj|in|sus\d?|dim|aug)?)\]|"
    r"\b([A-G][#b]?m?(?:7|maj7|m7|sus4|dim)?)\b",
    re.I,
)


def _clamp_pitch(p: int) -> int | None:
    if MIN_PITCH <= p <= MAX_PITCH:
        return p
    return None


def notes_from_midi_bytes(data: bytes, simplify: bool = True) -> list:
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        path = tmp.name
    try:
        notes = midi_to_web_notes(path)
    finally:
        import os

        try:
            os.unlink(path)
        except OSError:
            pass
    if simplify:
        from audio_processor import simplify_to_melody

        notes = simplify_to_melody(notes)
    return filter_notes(notes)


def notes_from_midi_stream(stream: BinaryIO, simplify: bool = True) -> list:
    return notes_from_midi_bytes(stream.read(), simplify=simplify)


def _chord_to_pitches(name: str) -> list[int]:
    raw = name.strip().replace("min", "m").replace("maj", "")
    for pat, pitches in _CHORD_PATTERNS:
        if pat.match(raw):
            return pitches
    m = re.match(r"^([A-G])([#b]?)(m)?$", raw, re.I)
    if not m:
        return [60, 64, 67]
    root, acc, minor = m.group(1).upper(), m.group(2), m.group(3)
    semi = _ABC_PITCH.get(root, 0)
    if acc == "#":
        semi += 1
    elif acc == "b":
        semi -= 1
    base = 60 + semi
    if minor:
        return [base, base + 3, base + 7]
    return [base, base + 4, base + 7]


def notes_from_chord_chart(text: str, seconds_per_chord: float = 0.55) -> list:
    """吉他和弦 / 和弦譜 → 分解和弦鋼琴音（教學用）。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("和弦內容為空")

    chords: list[str] = []
    for line in lines:
        if line.startswith(("#", "//", "[")):
            continue
        found = _CHORD_TOKEN.findall(line)
        if found:
            for a, b in found:
                chords.append((a or b).strip())
        else:
            parts = re.split(r"\s+", line)
            for p in parts:
                if re.match(r"^[A-G][#b]?m?(?:7|maj7)?$", p, re.I):
                    chords.append(p)

    if not chords:
        raise ValueError("找不到和弦符號（例：Am G C F 或 [Am]）")

    notes: list = []
    t = 0.0
    for ch in chords:
        pitches = _chord_to_pitches(ch)
        step = seconds_per_chord / max(len(pitches), 1)
        for i, p in enumerate(pitches):
            cp = _clamp_pitch(p)
            if cp is None:
                continue
            st = round(t + i * step, 3)
            notes.append({
                "pitch": cp,
                "note_name": pretty_midi.note_number_to_name(cp),
                "start_time": st,
                "end_time": round(st + step * 0.9, 3),
                "duration": round(step * 0.9, 3),
                "isHit": False,
            })
        t += seconds_per_chord

    return filter_notes(notes)


def _abc_octave(letter: str, commas: str, apostrophes: str) -> int:
    """ABC：大寫=C4 基準，小寫高八度，',' 降低，\"'\" 升高。"""
    if letter.islower():
        oct = 5
    else:
        oct = 4
    oct -= commas.count(",")
    oct += apostrophes.count("'")
    return oct


def _abc_accidental(prefix: str, letter: str) -> int:
    semi = _ABC_PITCH[letter.upper()]
    if "^" in prefix:
        semi += prefix.count("^")
    if "_" in prefix:
        semi -= prefix.count("_")
    if "=" in prefix:
        pass
    return semi


def parse_abc_to_notes(abc_text: str) -> list:
    """簡化 ABC 主旋律解析（單聲部，適合民謠 / 傳統曲）。"""
    if not abc_text or len(abc_text.strip()) < 3:
        raise ValueError("ABC 內容過短")

    tempo_q = 120
    default_len = 0.5
    m_q = re.search(r"Q:.*?(\d+)", abc_text, re.I)
    if m_q:
        tempo_q = int(m_q.group(1))
    m_l = re.search(r"L:\s*(\d+)/(\d+)", abc_text, re.I)
    if m_l:
        num, den = int(m_l.group(1)), int(m_l.group(2))
        default_len = (num / den) * (60.0 / tempo_q) * 4

    body_lines: list[str] = []
    for line in abc_text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        if re.match(r"^[A-Za-z]:", s) and not s.startswith("w:"):
            continue
        if s.startswith("w:"):
            continue
        body_lines.append(s)

    body = " ".join(body_lines)
    body = re.sub(r'"[^"]*"', "", body)
    body = body.replace("|", " ").replace(":", " ")

    token_re = re.compile(
        r"([_^=]*)([A-Ga-g])([',]*)(\d*/\d+|\d+)?|z(\d*/\d+|\d+)?",
    )

    notes: list = []
    t = 0.0
    for m in token_re.finditer(body):
        if m.group(2):
            prefix, letter, oct_mark, length = (
                m.group(1) or "",
                m.group(2),
                m.group(3) or "",
                m.group(4),
            )
            commas = "".join(c for c in oct_mark if c == ",")
            apost = "".join(c for c in oct_mark if c == "'")
            oct = _abc_octave(letter, commas, apost)
            semi = _abc_accidental(prefix, letter)
            pitch = 12 * (oct + 1) + semi
            cp = _clamp_pitch(pitch)
            if cp is None:
                continue
            dur = default_len
            if length:
                if "/" in length:
                    a, b = length.split("/")
                    dur = default_len * int(a) / int(b)
                else:
                    dur = default_len * int(length)
            st = round(t, 3)
            notes.append({
                "pitch": cp,
                "note_name": pretty_midi.note_number_to_name(cp),
                "start_time": st,
                "end_time": round(st + dur * 0.92, 3),
                "duration": round(dur * 0.92, 3),
                "isHit": False,
            })
            t += dur
        elif m.group(0).startswith("z"):
            zlen = m.group(5)
            rest = default_len
            if zlen:
                if "/" in zlen:
                    a, b = zlen.split("/")
                    rest = default_len * int(a) / int(b)
                else:
                    rest = default_len * int(zlen)
            t += rest

    if not notes:
        raise ValueError("無法從 ABC 解析出音符（格式可能過於複雜）")
    return filter_notes(notes)


def convert_sheet(
    data: bytes | str,
    fmt: str,
    *,
    simplify: bool = True,
) -> list:
    fmt = fmt.lower()
    if fmt in ("mid", "midi"):
        raw = data if isinstance(data, bytes) else data.encode()
        return notes_from_midi_bytes(raw, simplify)
    if fmt == "abc":
        text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
        return parse_abc_to_notes(text)
    if fmt in ("chord", "chords", "txt"):
        text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
        return notes_from_chord_chart(text)
    raise ValueError(f"不支援的格式：{fmt}")


def guess_format_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.endswith((".mid", ".midi")):
        return "midi"
    if path.endswith(".abc"):
        return "abc"
    if path.endswith((".mxl", ".musicxml", ".xml")):
        return "musicxml"
    return "midi"
