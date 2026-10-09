"""Convert the mission phase table (*.tab) into mission_timeline.json.
ミッションフェーズの表（*.tab）を mission_timeline.json に変換する。

The table has one row per phase start, comma-separated and padded with spaces:
表は、フェーズの開始ごとに1行。カンマ区切りで、空白で幅をそろえてある:

    # Start Time            ,Mission Phase Acronym ,Mission Phase Name ,Path to folder
    YYYY-MM-DDThh:mm:ss.sssZ ,cruise                ,Cruise             ,cruise

The phase dates are not public: keep the table and the output only on the server.
フェーズの日付は非公開なので、表も出力もサーバーにだけ置くこと。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from miopds_common._config import ConfigError, MissionTimeline, parse_utc

# Only this phase has no known end. Its stop is `end` (default DEFAULT_END).
# 終わりが決まっていないのはこのフェーズだけ。stop は end（既定は DEFAULT_END）。
OPEN_ENDED_PHASE_ID = "msp"
DEFAULT_END = "2100-01-01T00:00:00Z"

# Start Time, Mission Phase Acronym, Mission Phase Name, Path to folder
_COLUMNS = 4


@dataclass(frozen=True)
class TimelineResult:
    """What TimelineConverter.write() did / TimelineConverter.write() の結果。"""

    path: Path
    #: False when the file already had the same content and was left as it is
    #: 同じ内容のファイルがすでにあり、書き換えなかった場合は False
    changed: bool


@dataclass(frozen=True)
class _Row:
    line_no: int
    start: str
    id: str
    name: str


class TimelineConverter:
    """Convert a mission phase table into the content of mission_timeline.json.
    ミッションフェーズの表を mission_timeline.json の内容に変換する。

    - Each phase lasts until the start of the next phase.
      各フェーズは、次のフェーズの開始まで続く。
    - Rows that repeat the previous phase are merged into one period.
      前の行と同じフェーズの行は、1つの期間にまとめる。
    - The last phase must be msp; its stop is `end` (default 2100-01-01).
      To end the table with another phase, give `end` explicitly.
      最後のフェーズは msp で、その stop は end（既定 2100-01-01）。
      ほかのフェーズで終わる表では、end を明示する。
    - Column 2 (acronym) becomes the id, column 3 the name; column 4 is not used.
      2列目（略称）を id、3列目を name にする。4列目は使わない。
    """

    def __init__(self, *, end: str | None = None) -> None:
        if end is not None:
            parse_utc(end)  # Check the format early / 書式を先に確認する
        self.end = end

    def convert(self, table_path: Path | str) -> dict:
        """Return the checked content of mission_timeline.json for the table.
        表から、確認済みの mission_timeline.json の内容を返す。
        """
        table_path = Path(table_path)
        rows = _merge(_read_rows(table_path))
        if not rows:
            raise ConfigError(f"{table_path}: no phase rows")

        end = self.end
        last = rows[-1]
        if end is None:
            if last.id != OPEN_ENDED_PHASE_ID:
                # Do not guess when another phase ends / 他のフェーズの終わりは推測しない
                raise ConfigError(
                    f"{table_path}:{last.line_no}: the last phase is {last.name!r} "
                    f"({last.id}), not {OPEN_ENDED_PHASE_ID}, so its stop is unknown. "
                    "Add the next phase to the table, or give --end."
                )
            end = DEFAULT_END

        stops = [row.start for row in rows[1:]] + [end]
        data = {
            "mission_phases": [
                {"start": row.start, "stop": stop, "name": row.name, "id": row.id}
                for row, stop in zip(rows, stops)
            ]
        }
        # The same checks as when the timeline is used / 使うときと同じ確認をする
        MissionTimeline.from_data(data, str(table_path))
        return data

    def write(self, table_path: Path | str, output: Path | str) -> TimelineResult:
        """Write mission_timeline.json, unless it already has the same content.
        mission_timeline.json を書き出す。同じ内容のファイルがあれば書き換えない。

        Leaving an unchanged file alone keeps its time stamp, so running this
        every time (e.g. from cron) does not make cron_mk_cdf_to_pds.sh
        rebuild all the labels.
        変わらないファイルは日時もそのままなので、cron などで毎回実行しても、
        cron_mk_cdf_to_pds.sh がすべてのラベルを作り直すことはない。
        """
        data = self.convert(table_path)
        output = Path(output)
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if output.is_file() and output.read_text(encoding="utf-8") == text:
            return TimelineResult(output, changed=False)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
        return TimelineResult(output, changed=True)


def _read_rows(path: Path) -> list[_Row]:
    """Read the data rows; blank lines and lines starting with # are skipped.
    データの行を読む。空行と # で始まる行（ヘッダー）は飛ばす。
    """
    rows: list[_Row] = []
    previous = None
    # utf-8-sig also accepts a file that starts with a BOM
    # utf-8-sig は、先頭に BOM が付いたファイルも読める
    with path.open(encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, start=1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            where = f"{path}:{line_no}"
            columns = [column.strip() for column in text.split(",")]
            if len(columns) != _COLUMNS or not all(columns):
                raise ConfigError(
                    f"{where}: expected {_COLUMNS} non-empty columns, got {text!r}"
                )
            start, phase_id, name, _folder = columns
            try:
                when = parse_utc(start)
            except ConfigError as error:
                raise ConfigError(f"{where}: {error}") from error
            if previous is not None and when <= previous:
                raise ConfigError(f"{where}: start times must increase: {start}")
            previous = when
            rows.append(_Row(line_no, start, phase_id, name))
    return rows


def _merge(rows: list[_Row]) -> list[_Row]:
    # Keep only the rows where the phase changes / フェーズが変わる行だけを残す
    merged: list[_Row] = []
    for row in rows:
        if merged and (merged[-1].id, merged[-1].name) == (row.id, row.name):
            continue
        merged.append(row)
    return merged
