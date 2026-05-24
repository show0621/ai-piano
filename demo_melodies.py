"""
內建示範曲主旋律（C 調簡譜，節奏與旋律貼近原曲）。

記號：1' = 高八度；.1 = 低八度；5# / 5b；5_ = 半拍；5. = 附點；5-- = 兩拍
K: Am = A 小調；Q: = BPM；| = 小節；- = 休止一拍
"""

from __future__ import annotations

from audio_processor import _build_jianpu_score

# ── 範例保留 ──────────────────────────────────────────────

_TWINKLE = """
Q: 120
| 1 1 5 5 | 6 6 5 - |
| 4 4 3 3 | 2 2 1 - |
| 5 5 4 4 | 3 3 2 - |
| 5 5 4 4 | 3 3 2 - |
| 1 1 5 5 | 6 6 5 - |
| 4 4 3 3 | 2 2 1-- |
"""

_JIAN_DANAI = """
Q: 85
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

# ── 兒歌 ─────────────────────────────────────────────────

_LIANG_ZHI_LAO_HU = """
Q: 120
| 1 2 3 1 | 1 2 3 1 |
| 3 4 5 - | 3 4 5 - |
| 5_ 6_ 5_ 4_ 3_ 1_ | 5_ 6_ 5_ 4_ 3_ 1_ |
| 1' - 5 - | 1' - 5 - |
"""

_XIAO_MI_FENG = """
Q: 176
| 5_ 3_ 5_ 3_ | 4_ 2_ 4_ 2_ |
| 5_ 5_ 5_ 5_ 5_ 5_ | 3_ 3_ 3_ 3_ 3_ 3_ |
| 5_ 3_ 5_ 3_ | 4_ 2_ 4_ 2_ |
| 5_ 5_ 5_ 5_ 5_ 5_ | 3_ 3_ 3_ 3_ 3_ 3_ |
"""

_HAPPY_BIRTHDAY = """
Q: 120
| 5 5 6 5 | 1' 7 - |
| 5 5 6 5 | 2' 1' - |
| 5 5 1' 6 | 7 1' - |
| 4 4 3 1 | 2 1'-- |
"""

_FEN_SHUA_JIANG = """
Q: 120
| 5_ 3_ 5_ 3_ | 5_ 3_ 5_ 3_ |
| 1 2 3 4 | 3 2 1 - |
| 4 4 3 3 | 2 2 1 - |
| 4 4 3 3 | 2 2 1-- |
"""

_MO_LI_HUA = """
Q: 76
| 3 3 5 6 | 1' 6 5 3 |
| 2 3 5 6 | 1' 6 5 3 |
| 3 3 5 6 | 1' 6 5 3 |
| 2 3 2 1 | 6 5 3-- |
"""

# ── 動畫主題 ─────────────────────────────────────────────

# 哆啦A夢（經典主題歌 · 小叮噹旋律）
_DORAEMON = """
Q: 120
| 6 7 1' 2' | 3' 2' 1' 7 |
| 6 5 3 5 | 6 7 1' - |
| 6 7 1' 2' | 3' 2' 1' 7 |
| 6 5 3 2 | 3 5 6 - |
| 2' 2' 1' 7 | 6 5 4 3 |
| 2 3 5 6 | 5-- - - |
"""

# 櫻桃小丸子（おどるポンポコリン 副歌）
_MARUKO = """
Q: 128
| 5 3 5 6 | 1' 2' 1' 6 |
| 5 3 5 6 | 1' 6 5 3 |
| 2 3 4 5 | 6 5 4 3 |
| 2 2 3 5 | 6 5 3 2 |
| 1 2 3 4 | 5-- - - |
"""

# 龍貓（となりのトトロ · 散步主題）
_TOTORO = """
Q: 96
| 3. 3. 4. 3. 2. | 1. 2. 3. 5. |
| 3. 4. 5. 3. | 2. 3. 5. - |
| 3. 3. 4. 3. 2. | 1. 2. 3. 1' |
| 6. 5. 3. | 2. - - |
| 3 5 6 1' | 6 5 3 2 |
| 3 5 6 1' | 2 3 5-- |
"""

# 名偵探柯南（メインテーマ 經典前奏 · E 小調）
_CONAN = """
K: Em
Q: 138
| 1 - - - | 1 - 2 - |
| 1 - 1b - | 1 - 5' - |
| 5' - 4' - | 3 - 2 - |
| 1b - 1 - | 1 - - - |
| 1 - - - | 1 - 2 - |
| 1 - 1b - | 1 - 5' - |
| 5' 4' 3 2 | 1b 1-- - |
"""

# 麵包超人（それいけ！アンパンマン）
_ANPANMAN = """
Q: 140
| 1 2 3 4 | 5 - - |
| 6 5 4 3 | 2 - - |
| 1 2 3 4 | 5 - - |
| 6 5 4 3 | 2 - - |
| 3 4 5 6 | 5 - - |
| 1 - - - | - - - |
"""

# ── 古典（公版）──────────────────────────────────────────

# 卡農（Pachelbel · 著名低音進行，C 調）
_CANON = """
Q: 56
| 1 - 5 - | 6 - 3 - |
| 4 - 1 - | 4 - 3 - |
| 2 - 6 - | 7 - 4 - |
| 5 - 2 - | 5 - 1 - |
| 1 - 5 - | 6 - 3 - |
| 4 - 1 - | 4 - 3 - |
| 2 - 6 - | 7 - 4 - |
| 5 - 2 - | 5 - 1-- |
"""

# 致愛麗絲（開頭著名動機 · 原調音程）
_FUR_ELISE = """
Q: 76
| 3_ 2#_ 3_ 2#_ | 3_ 7_ 2_ 1_ |
| 6_ - - - | - - - - |
| 6_ 5_ 4_ 3_ | 2_ 3_ 4_ - |
| 4_ 3_ 2_ 1_ | 6_ - - - |
| 3_ 2#_ 3_ 2#_ | 3_ 7_ 2_ 1_ |
| 6_ - - - | - - - - |
"""

# 歡樂頌（交響曲第九號主題）
_ODE_TO_JOY = """
Q: 104
| 3 3 4 5 | 5 4 3 2 |
| 1 1 2 3 | 3_ 2_ 2 - |
| 3 3 4 5 | 5 4 3 2 |
| 1 1 2 3 | 2_ 1_ 1 - |
| 3 3 4 5 | 5 4 3 2 |
| 1 2 3 2 | 1-- - - |
"""

# 命運交響曲（短短短長＋副題片段）
_BEETHOVEN_FIFTH = """
Q: 108
| 5_ 5_ 5_ 1'-- | 5_ 5_ 5_ 1'-- |
| 5_ 5_ 5_ 1'-- | 3_ 3_ 3_ 1'-- |
| 5 4 3 2 | 3 2 1 - |
| 2 3 4 5 | 5 4 3 2 |
| 1 1 2 3 | 3_ 2_ 2-- |
"""


def _score(jianpu: str, default_bpm: float = 120, *, repeat: int = 1) -> list:
    return _build_jianpu_score(jianpu, 60.0 / default_bpm, repeat=repeat)


def build_twinkle() -> list:
    return _score(_TWINKLE, 120)


def build_jianndanai() -> list:
    return _score(_JIAN_DANAI, 85)


def build_liangzhilaohu() -> list:
    return _score(_LIANG_ZHI_LAO_HU, 120)


def build_xiaomifeng() -> list:
    return _score(_XIAO_MI_FENG, 176)


def build_happy_birthday() -> list:
    return _score(_HAPPY_BIRTHDAY, 120)


def build_fenshuajiang() -> list:
    return _score(_FEN_SHUA_JIANG, 120)


def build_molihua() -> list:
    return _score(_MO_LI_HUA, 76)


def build_doraemon() -> list:
    return _score(_DORAEMON, 120)


def build_maruko() -> list:
    return _score(_MARUKO, 128)


def build_totoro() -> list:
    return _score(_TOTORO, 96)


def build_conan() -> list:
    return _score(_CONAN, 138)


def build_anpanman() -> list:
    return _score(_ANPANMAN, 132)


def build_canon() -> list:
    return _score(_CANON, 56)


def build_fur_elise() -> list:
    return _score(_FUR_ELISE, 76)


def build_ode_to_joy() -> list:
    return _score(_ODE_TO_JOY, 104)


def build_beethoven_fifth() -> list:
    return _score(_BEETHOVEN_FIFTH, 108)


DEMO_BUILDERS = {
    "twinkle": build_twinkle,
    "jianndanai": build_jianndanai,
    "liangzhilaohu": build_liangzhilaohu,
    "xiaomifeng": build_xiaomifeng,
    "happy_birthday": build_happy_birthday,
    "fenshuajiang": build_fenshuajiang,
    "molihua": build_molihua,
    "doraemon": build_doraemon,
    "maruko": build_maruko,
    "totoro": build_totoro,
    "conan": build_conan,
    "anpanman": build_anpanman,
    "canon": build_canon,
    "fur_elise": build_fur_elise,
    "ode_to_joy": build_ode_to_joy,
    "beethoven_fifth": build_beethoven_fifth,
}
