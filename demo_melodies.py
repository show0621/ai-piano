"""
內建示範曲主旋律（C 調簡譜，節奏與旋律貼近原曲）。

記號：1' = 高八度；.1 = 低八度；5# / 5b；5_ = 半拍；5. = 附點；5-- = 兩拍
K: Am = A 小調；Q: = BPM；| = 小節；- = 休止一拍
"""

from __future__ import annotations

from audio_processor import _build_jianpu_score

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


def _score(jianpu: str, default_bpm: float = 120, *, repeat: int = 1) -> list:
    return _build_jianpu_score(jianpu, 60.0 / default_bpm, repeat=repeat)


def build_jianndanai() -> list:
    """後備簡譜；正式示範請用 scores/jianndanai.json（由 周杰倫簡單愛.mid 轉出）。"""
    return _score(_JIAN_DANAI, 85)


DEMO_BUILDERS = {
    "jianndanai": build_jianndanai,
}
