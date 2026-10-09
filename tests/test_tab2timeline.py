"""Tests for miopds_common.tab2timeline.
miopds_common.tab2timeline のテスト。

All dates are made up: the real mission phase dates are not public.
日付はすべて架空のもの（本物のミッションフェーズの日付は非公開）。
"""

import json
import os
from datetime import datetime, timezone

import pytest

from miopds_common._cli import timeline_main
from miopds_common._config import ConfigError, MissionPhase, MissionTimeline
from miopds_common.tab2timeline import DEFAULT_END, TimelineConverter

HEADER = (
    "# Start Time            ,Mission Phase Acronym ,Mission Phase Name"
    "                         ,Path to folder\n"
)
# (start, acronym, name, path to folder)
CRUISE = ("2001-01-01T00:00:00.000Z", "cruise", "Cruise", "cruise")
MGA1 = ("2001-02-01T00:00:00.000Z", "mga1", "Mercury Gravity Assist 1", "mga1")
CRUISE_AGAIN = ("2001-02-10T00:00:00.000Z", "cruise", "Cruise", "cruise")
MSP = ("2001-03-01T00:00:00.000Z", "msp", "Mercury Science Phase", "msp")


def _table(tmp_path, *rows) -> str:
    # Padded with spaces like the real table / 本物の表と同じく空白で幅をそろえる
    lines = [HEADER] + [
        f"{start} ,{acronym:<22},{name:<43},{folder}\n"
        for start, acronym, name, folder in rows
    ]
    path = tmp_path / "phases.tab"
    path.write_text("".join(lines), encoding="utf-8")
    return str(path)


def _phases(data) -> list[tuple[str, str, str, str]]:
    return [(p["start"], p["stop"], p["name"], p["id"]) for p in data["mission_phases"]]


def test_each_phase_ends_at_the_next_start(tmp_path):
    path = _table(tmp_path, CRUISE, MGA1, CRUISE_AGAIN, MSP)
    data = TimelineConverter().convert(path)
    assert _phases(data) == [
        (CRUISE[0], MGA1[0], "Cruise", "cruise"),
        (MGA1[0], CRUISE_AGAIN[0], "Mercury Gravity Assist 1", "mga1"),
        (CRUISE_AGAIN[0], MSP[0], "Cruise", "cruise"),
        (MSP[0], DEFAULT_END, "Mercury Science Phase", "msp"),
    ]


def test_acronym_is_the_id_and_the_folder_is_not_used(tmp_path):
    row = ("2001-03-01T00:00:00.000Z", "msp", "Mercury Science Phase", "some/folder")
    data = TimelineConverter().convert(_table(tmp_path, row))
    assert data == {
        "mission_phases": [{
            "start": row[0], "stop": DEFAULT_END,
            "name": "Mercury Science Phase", "id": "msp",
        }]
    }


def test_repeated_rows_are_merged(tmp_path):
    same = ("2001-01-15T00:00:00.000Z", "cruise", "Cruise", "cruise")
    data = TimelineConverter().convert(_table(tmp_path, CRUISE, same, MSP))
    assert _phases(data) == [
        (CRUISE[0], MSP[0], "Cruise", "cruise"),
        (MSP[0], DEFAULT_END, "Mercury Science Phase", "msp"),
    ]


def test_end_changes_the_stop_of_msp(tmp_path):
    end = "2050-01-01T00:00:00Z"
    data = TimelineConverter(end=end).convert(_table(tmp_path, CRUISE, MSP))
    assert data["mission_phases"][-1]["stop"] == end


def test_last_phase_other_than_msp_needs_end(tmp_path):
    path = _table(tmp_path, CRUISE, MGA1)
    with pytest.raises(ConfigError, match="not msp, so its stop is unknown"):
        TimelineConverter().convert(path)
    # With an explicit end it is accepted / end を明示すれば受け付ける
    data = TimelineConverter(end="2001-02-05T00:00:00Z").convert(path)
    assert data["mission_phases"][-1]["stop"] == "2001-02-05T00:00:00Z"


def test_end_before_the_last_start_is_an_error(tmp_path):
    path = _table(tmp_path, CRUISE, MSP)
    with pytest.raises(ConfigError, match="start must be before stop"):
        TimelineConverter(end="2001-02-01T00:00:00Z").convert(path)


def test_bad_end_is_an_error():
    with pytest.raises(ConfigError, match="Not an ISO 8601 date-time"):
        TimelineConverter(end="next year")


def test_start_times_must_increase(tmp_path):
    path = _table(tmp_path, MSP, CRUISE)
    with pytest.raises(ConfigError, match=r"phases\.tab:3: start times must increase"):
        TimelineConverter().convert(path)


def test_wrong_number_of_columns_is_an_error(tmp_path):
    path = tmp_path / "phases.tab"
    row = "2001-01-01T00:00:00.000Z ,cruise ,Cruise\n"  # 3 columns / 3列しかない
    path.write_text(HEADER + row, encoding="utf-8")
    with pytest.raises(ConfigError, match=r"phases\.tab:2: expected 4 non-empty"):
        TimelineConverter().convert(path)


def test_bad_time_is_an_error(tmp_path):
    month_13 = ("2001-13-01T00:00:00Z", "msp", "Mercury Science Phase", "msp")
    path = _table(tmp_path, month_13)
    with pytest.raises(ConfigError, match=r"phases\.tab:2: Not an ISO 8601 date-time"):
        TimelineConverter().convert(path)


def test_table_without_rows_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="no phase rows"):
        TimelineConverter().convert(_table(tmp_path))


def test_written_file_is_a_usable_timeline(tmp_path):
    result = TimelineConverter().write(
        _table(tmp_path, CRUISE, MGA1, MSP), tmp_path / "out" / "mission_timeline.json"
    )
    assert result.changed
    timeline = MissionTimeline.load(result.path)
    when = datetime(2001, 2, 2, tzinfo=timezone.utc)
    assert timeline.phase_at(when) == MissionPhase("Mercury Gravity Assist 1", "mga1")
    assert result.path.read_text(encoding="utf-8").endswith("}\n")


def test_same_content_is_not_rewritten(tmp_path):
    # Keeping the time stamp avoids rebuilding every label in cron
    # 日時を変えなければ、cron ですべてのラベルが作り直されることはない
    output = tmp_path / "mission_timeline.json"
    converter = TimelineConverter()
    converter.write(_table(tmp_path, CRUISE, MSP), output)
    os.utime(output, (1_000_000_000, 1_000_000_000))  # An old time stamp / 古い日時
    result = converter.write(_table(tmp_path, CRUISE, MSP), output)
    assert not result.changed
    assert output.stat().st_mtime == 1_000_000_000
    # A changed table is written / 表が変われば書き直す
    assert converter.write(_table(tmp_path, CRUISE, MGA1, MSP), output).changed
    assert output.stat().st_mtime != 1_000_000_000


def test_command_writes_the_timeline(tmp_path):
    output = tmp_path / "mission_timeline.json"
    assert timeline_main([_table(tmp_path, CRUISE, MSP), str(output)]) == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["mission_phases"][0]["id"] == "cruise"


def test_command_returns_1_on_error(tmp_path):
    output = tmp_path / "mission_timeline.json"
    assert timeline_main([_table(tmp_path, CRUISE, MGA1), str(output)]) == 1
    assert not output.exists()
