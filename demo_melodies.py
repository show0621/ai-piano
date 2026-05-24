"""
內建示範曲主旋律（C 調簡譜，接近原曲輪廓與節奏）。

記號：1' = 高八度；.1 = 低八度；5# / 5b = 升／降半音；5_ = 半拍；5. = 附點；5-- = 兩拍
K: Dm = D 小調；Q: = BPM；| = 小節；- = 休止一拍
"""

from __future__ import annotations

from audio_processor import _build_jianpu_score, _raw_to_notes

# ── 範例保留 ──────────────────────────────────────────────

_TWINKLE = """
| 1 1 5 5 | 6 6 5 - |
| 4 4 3 3 | 2 2 1 - |
| 5 5 4 4 | 3 3 2 - |
| 5 5 4 4 | 3 3 2 - |
| 1 1 5 5 | 6 6 5 - |
| 4 4 3 3 | 2 2 1-- |
"""

_JIAN_DANAI = """
| 5 5 6 5 | 3 2 3 2 1 6 |
| 5 5 6 5 | 3 2 3 2 1 2 3 |
| 3 3 4 5 | 6 5 4 3 2 |
| 3 3 4 5 | 6 5 4 5 3 |
| 6 6 5 3 5 | 6 1 1 2 1 6 |
| 5 5 3 2 3 | 5 6 5 3 2 1 |
| 1 1 2 3 | 4 3 2 1 6 5 |
| 5 5 6 5 3 | 2 3 2 1 2 1 |
| 5 5 6 5 | 3 2 3 2 1 6 |
| 5 5 6 5 | 3 2 3 2 1 2 3 |
| 6 5 4 3 2 | 3 5 6 5 3 |
| 2 3 2 1 | 6 5 4 3 2 |
| 5 5 6 5 | 3 2 1-- - |
"""

# ── 兒歌（10 首）────────────────────────────────────────

_LIANG_ZHI_LAO_HU = """
| 1 2 3 1 | 1 2 3 1 |
| 3 4 5 - | 3 4 5 - |
| 5 6 5 4 3 1 | 5 6 5 4 3 1 |
| 1' 5 1 - | 1' 5 1 - |
"""

_XIAO_MI_FENG = """
| 5 3 5 3 | 1' 1' 1' - |
| 5 3 5 3 | 1' 1' 1' - |
| 5 6 5 3 2 5 | 5 6 5 3 2 5 |
| 1' 1' 1' 1' 1' 1' | 5 3 5 3 1' - |
"""

_HAPPY_BIRTHDAY = """
| 5 5 6 5 | 1' 7 - |
| 5 5 6 5 | 2' 1' - |
| 5 5 1' 6 | 7 1' - |
| 4 4 3 1 | 2 1'-- |
"""

_FEN_SHUA_JIANG = """
| 5 3 5 3 | 5 3 5 3 |
| 1 2 3 4 | 3 2 1 - |
| 4 4 3 3 | 2 2 1 - |
| 4 4 3 3 | 2 2 1 - |
"""

_MO_LI_HUA = """
| 3 3 5 6 | 1' 6 5 3 |
| 2 3 5 6 | 1' 6 5 3 |
| 3 3 5 6 | 1' 6 5 3 |
| 2 3 2 1 | 6 5 3-- |
"""

# ── 動畫主題（與兒歌合計 10 首熱門）──────────────────────

_DORAEMON = """
| 6 7 1' 2' | 3' 2' 1' 6 |
| 5 3 2 3 | 5 6 1' - |
| 6 7 1' 2' | 3' 2' 1' 6 |
| 5 3 5 6 | 1'-- - |
| 5 5 6 5 | 3 2 3 5 |
| 6 1' 7' 6' | 5 3 2 1 |
"""

_MARUKO = """
| 5 3 5 6 | 1' 1' 6 5 |
| 3 2 3 5 | 6 5 3 2 |
| 1 2 3 5 | 6 5 3 2 |
| 5 6 1' 6 | 5 3 2 1-- |
"""

_TOTORO = """
| 3 5 6 1' | 6 5 3 2 |
| 3 5 6 1' | 2 3 5 - |
| 3 5 6 1' | 6 5 3 2 |
| 1 2 3 5 | 6 5 3-- |
"""

_CONAN = """
| 3 5 6 5 | 3 2 1 2 |
| 3 5 6 1' | 6 5 3 2 |
| 3 5 6 5 | 3 2 3 5 |
| 6 5 3 2 | 1-- - |
"""

_ANPANMAN = """
| 1 2 3 4 | 5 5 5 - |
| 6 5 4 3 | 2 2 2 - |
| 3 4 5 6 | 5 4 3 2 |
| 1 1 1 - | 5 5 5-- |
"""

# ── 古典（公版）──────────────────────────────────────────

_CANON = """
| 1 5 6 3 | 4 1 4 3 |
| 2 6 7 4 | 5 2 5 4 |
| 3 7 1' 5 | 6 3 6 5 |
| 4 1 2 6 | 7 4 7 6 |
| 1 5 6 3 | 4 1 4 3 |
| 2 6 7 4 | 5 2 5 1-- |
"""

_FUR_ELISE = """
| 3 3 3 3 | 2 3 4 - |
| 3 2 1 2 | 3 - - - |
| 3 3 3 3 | 2 3 4 - |
| 3 2 1 1 | 7 6 5 - |
| 4 4 4 4 | 3 4 5 - |
| 4 3 2 3 | 4 - - - |
"""

_ODE_TO_JOY = """
| 3 3 4 5 | 5 4 3 2 |
| 1 1 2 3 | 3. 2. 2 - |
| 3 3 4 5 | 5 4 3 2 |
| 1 1 2 3 | 2. 1. 1 - |
| 3 3 4 5 | 5 4 3 2 |
| 1 2 3 1 | 1 - - - |
"""

_BEETHOVEN_FIFTH = """
| 3 3 3 5 | 1' 1' 1' 5 |
| 3 3 3 5 | 1' 1' 1' 5 |
| 3 3 3 5 | 6 5 4 3 |
| 2 2 2 4 | 3 2 1-- |
"""


def _score(jianpu: str, bpm: float, *, repeat: int = 1) -> list:
    return _build_jianpu_score(jianpu, 60.0 / bpm, repeat=repeat)


def build_twinkle() -> list:
    return _score(_TWINKLE, 120)


def build_jianndanai() -> list:
    return _score(_JIAN_DANAI, 85)


def build_liangzhilaohu() -> list:
    return _score(_LIANG_ZHI_LAO_HU, 100)


def build_xiaomifeng() -> list:
    return _score(_XIAO_MI_FENG, 160)


def build_happy_birthday() -> list:
    return _score(_HAPPY_BIRTHDAY, 120)


def build_fenshuajiang() -> list:
    return _score(_FEN_SHUA_JIANG, 120)


def build_molihua() -> list:
    return _score(_MO_LI_HUA, 72)


def build_doraemon() -> list:
    return _score(_DORAEMON, 120)


def build_maruko() -> list:
    return _score(_MARUKO, 110)


def build_totoro() -> list:
    return _score(_TOTORO, 90)


def build_conan() -> list:
    return _score(_CONAN, 140)


def build_anpanman() -> list:
    return _score(_ANPANMAN, 130)


def build_canon() -> list:
    return _score(_CANON, 60)


def build_fur_elise() -> list:
    return _score(_FUR_ELISE, 100)


def build_ode_to_joy() -> list:
    return _score(_ODE_TO_JOY, 108)


def build_beethoven_fifth() -> list:
    return _score(_BEETHOVEN_FIFTH, 108)


DEMO_BUILDERS = {
    "twinkle": build_twinkle,
    "jianndanai": build_jianndanai,
    # 兒歌
    "liangzhilaohu": build_liangzhilaohu,
    "xiaomifeng": build_xiaomifeng,
    "happy_birthday": build_happy_birthday,
    "fenshuajiang": build_fenshuajiang,
    "molihua": build_molihua,
    # 動畫
    "doraemon": build_doraemon,
    "maruko": build_maruko,
    "totoro": build_totoro,
    "conan": build_conan,
    "anpanman": build_anpanman,
    # 古典公版
    "canon": build_canon,
    "fur_elise": build_fur_elise,
    "ode_to_joy": build_ode_to_joy,
    "beethoven_fifth": build_beethoven_fifth,
}
