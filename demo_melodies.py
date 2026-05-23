"""
內建示範曲主旋律（C 調簡譜，接近原曲輪廓與節奏）。

記號：1' = 高八度；.1 = 低八度；5# / 5b = 升／降半音；5_ = 半拍；5. = 附點；5-- = 兩拍
K: Dm = D 小調；Q: = BPM；| = 小節；- = 休止一拍
"""

from __future__ import annotations

from audio_processor import (
    _build_jianpu_score,
    _parse_jianpu,
    _raw_to_notes,
)

# ── 簡單愛（周杰倫 · C 調 · 副歌 hook ＋ 主歌 ＋ 橋）──
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
| 6 5 4 3 | 2 3 5 6 5 |
| 3 2 1 2 | 3 5 6 5 3 |
| 5 5 6 5 | 3 2 3 2 1 6 |
| 6 6 5 4 | 3 2 1 6 5 |
| 1 1 2 3 | 4 3 2 1 6 5 |
| 5 5 6 5 3 | 2 3 2 1 2 1 |
| 5 5 6 5 | 3 2 1-- - |
"""

# ── 安靜（周杰倫 · C 調 · 前奏＋主歌＋副歌）──
_ANJING = """
| 1'-- 1'-- | 7'-- 6'-- | 5-- - - |
| 1' 1' 7' 6' | 5-- - - - |
| 5 5 6 5 | 3 2 1 2 3 |
| 1' 7' 6' 5 | 3 2 1-- - - |
| 6 5 3 2 | 3 2 1 6 |
| 6 5 3 2 | 1 2 3 5 |
| 6 5 3 2 | 3 2 1 6 5 |
| 1' 1' 7' 6' | 5-- - 3 2 |
| 1' 7' 6' 5 | 3 2 1-- - - |
| 6 5 3 2 | 3 2 1 6 |
| 6 5 3 5 | 6 1' 7' 6' |
| 5 3 2 1 | 2 3 2 1 6 |
| 1' 1' 7' 6' | 5-- - - - |
| 1' 7' 6' 5 | 3 2 1 - - |
| 6 5 3 2 | 3 2 1 6 |
| 5 3 2 1 | 2 3 5 6 5 |
"""

# ── 開不了口（周杰倫 · C 調 · 主歌＋副歌）──
_KAIBULEKOU = """
| 6 5 3 2 | 3 5 6 5 |
| 5 3 2 1 | 2 3 5 6 |
| 6 5 3 5 | 6 1' 1' 7' |
| 6 5 3 2 | 1 2 3 2 1 |
| 3 5 6 5 | 3 2 3 2 1 |
| 2 3 5 6 | 5 3 5 6 |
| 6 5 3 2 | 3 5 6 5 |
| 5 3 2 1 | 2 3 5 6 |
| 1' 7' 6' 5 | 3 2 1 - - |
| 6 5 3 2 | 3 5 6 5 |
| 5 3 2 1 | 2 3 5 6 |
| 6 5 3 5 | 6 1'-- - - |
| 6 5 3 2 | 3 5 6 5 |
| 5 3 2 1 | 2 3 5 6 |
| 3 5 6 5 | 3 2 1 2 3 |
| 2 3 5 6 | 5 3 2 1-- |
"""

# ── 綠光（孫燕姿 · C 調 · 副歌，快板）──
_LVGuang = """
| 5 5 6 5 3 | 5 6 1' 1' |
| 5 5 6 5 3 | 2 3 2 1 6 |
| 3 3 4 5 6 | 5 3 2 3 5 |
| 6 5 3 5 6 | 1' 1' 2' 1' |
| 5 5 6 5 3 | 5 6 1' 1' |
| 5 5 6 5 3 | 2 3 2 1 6 |
| 3 3 4 5 6 | 5 3 2 3 5 |
| 6 5 4 3 2 | 3 5 6 1'-- |
| 5 5 6 5 3 | 5 6 1' 1' |
| 5 5 6 5 3 | 2 3 2 1 6 |
| 6 5 3 5 | 6 1' 7' 6' |
| 5 3 2 1 | 2 3 5 6 5 |
"""

# ── 滄海一聲笑（黃霑 · C 調 · 主段＋尾奏）──
_XIAOAO_MAIN = """
| 6. 6. 5 3 | 5 6 1' 1' |
| 2'_ 1'_ 6 | 5-- - |
| 5. 5. 3 2 | 3 5 6 5 |
| 3-- - |
| 2 3 2 3 | 5 6 1' 2' |
| 1' 6 5 3 |
| 5. 5. 3 2 | 3 5 6 5 |
| 3 2 1 2 3 |
| 6. 6. 5 3 | 5 6 1' 1' |
| 2'_ 1'_ 6 | 5 3 2 3 |
| 5. 5. 3 2 | 3 5 6 5 |
| 3 2 1 2 3 |
"""

_XIAOAO_OUTRO = """
| 6-- - 5 3 | 5 6 1' - |
| 2'_ 1'_ 6 | - - |
| 5. 5. 3 2 | 3 5 6 - |
| 3 2 1-- | - - |
"""

# ── 我不難過（孫燕姿 · C 調 · 主歌＋副歌）──
_WOBUNANGUO = """
| 6 5 3 5 | 6 1' 1' |
| 7' 6' 5 3 | 2 3 5 |
| 6 5 3 5 | 6 1' - - |
| 7' 6' 5 3 | 2 1 - - |
| 6 5 3 2 | 3 5 6 - |
| 5 3 2 1 | 2 3 5 6 |
| 6 5 3 5 | 6 1' 7' 6' |
| 5 3 2 1 | 2 1 - - |
| 3 5 6 5 | 3 2 1 6 |
| 6 5 3 2 | 3 5 6 5 |
| 5 3 2 1 | 2 3 5 6 |
| 6 5 3 5 | 6 1' 1' |
| 7' 6' 5 3 | 2 3 5 |
| 6 5 3 2 | 3 5 6 - |
| 5 3 2 1 | 2 3 5 6 |
| 6 5 3 5 | 6 1'-- - - |
"""

# ── 残酷天使のテーゼ（EVA OP · D 小調 · 經典主旋律）──
_CRUEL_ANGEL = """
K: Dm
Q: 126
| 1_ 1_ 2_ 1_ | .7_ .6_ - - |
| 5_ 4_ 3_ 2_ | 1_ .7_ .6_ - |
| 1_ 2_ 3_ 4_ | 5_ 6_ 5_ 4_ |
| 3_ 2_ 1_ .7_ | .6_ 5_ 4_ 3_ |
| 2_ 3_ 4_ 5_ | 6_ 5_ 4_ 3_ |
| 2_ 1_ .7_ .6_ | 5_ 4_ 3_ 2_ |
| 1_ 2_ 3_ 4_ | 5_ 6_ 5_ 4_ |
| 3_ 2_ 1_ 2_ | 3_ 5_ 6_ - |
| 1' 1' 2' 1' | 7' 6' 5_ 4_ |
| 3' 2' 1' .7_ | .6_ 5_ 4_ 3_ |
| 2_ 3_ 4_ 5_ | 6_ 5_ 6_ 5_ |
| 4_ 3_ 2_ 1_ | .7_ .6_ 5_ 4_ |
| 3_ 2_ 1_ .7_ | .6_ 5_ 4_ 3_ |
| 2_ 3_ 4_ 5_ | 6_ 5_ 4_ 3_ |
| 2_ 1_ .7_ .6_ | 5_ 4_ 3_ 2_ |
| 1-- - - |
"""


def _xiaoaojianghu_rhythm_full() -> list:
    beat = 60.0 / 76
    main = _parse_jianpu(_XIAOAO_MAIN, beat)
    outro = _parse_jianpu(_XIAOAO_OUTRO, beat)
    if not main:
        return []
    main_len = main[-1][1] + main[-1][2]
    gap = beat * 2
    raw: list = []
    off = 0.0
    for _ in range(3):
        for p, s, d in main:
            raw.append((p, s + off, d))
        off += main_len + gap
    for p, s, d in main:
        raw.append((p, s + off, d))
    off += main_len + gap * 2
    for p, s, d in outro:
        raw.append((p, s + off, d))
    return raw


def build_jianndanai() -> list:
    return _build_jianpu_score(_JIAN_DANAI, 60.0 / 85, repeat=1)


def build_anjing() -> list:
    return _build_jianpu_score(_ANJING, 60.0 / 72, repeat=1)


def build_kaibulekou() -> list:
    return _build_jianpu_score(_KAIBULEKOU, 60.0 / 76, repeat=1)


def build_lvguang() -> list:
    return _build_jianpu_score(_LVGuang, 60.0 / 105, repeat=1)


def build_wobunanguo() -> list:
    return _build_jianpu_score(_WOBUNANGUO, 60.0 / 68, repeat=1)


def build_cruelangel() -> list:
    # Q: 126 寫在簡譜內；此處 beat 僅作後備
    return _build_jianpu_score(_CRUEL_ANGEL, 60.0 / 126, repeat=1, key="Dm")


def build_xiaoaojianghu() -> list:
    return _raw_to_notes(_xiaoaojianghu_rhythm_full())


DEMO_BUILDERS = {
    "twinkle": lambda: _raw_to_notes([
        (60, 0.0, 0.4), (60, 0.5, 0.4), (67, 1.0, 0.4), (67, 1.5, 0.4),
        (69, 2.0, 0.4), (69, 2.5, 0.4), (67, 3.0, 0.8),
    ]),
    "xiaoaojianghu": build_xiaoaojianghu,
    "jianndanai": build_jianndanai,
    "anjing": build_anjing,
    "kaibulekou": build_kaibulekou,
    "lvguang": build_lvguang,
    "wobunanguo": build_wobunanguo,
    "cruelangel": build_cruelangel,
}
