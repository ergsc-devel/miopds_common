"""Mission phase table (*.tab) -> mission_timeline.json.
ミッションフェーズの表（*.tab）から mission_timeline.json を作る。

Usage / 使い方:
    from miopds_common import tab2timeline

    converter = tab2timeline.TimelineConverter()
    result = converter.write("<mission phase table>.tab", "mission_timeline.json")
"""

from .converter import (
    DEFAULT_END,
    OPEN_ENDED_PHASE_ID,
    TimelineConverter,
    TimelineResult,
)

__all__ = ["DEFAULT_END", "OPEN_ENDED_PHASE_ID", "TimelineConverter", "TimelineResult"]
