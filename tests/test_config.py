"""Tests for miopds_common._config.
miopds_common._config のテスト。
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from config_factory import dataset_dict

from miopds_common._config import (
    ConfigError,
    DatasetConfig,
    MissionConfig,
    MissionPhase,
    MissionTimeline,
    load_authors,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "config"


def _write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# -- examples/config must stay loadable / 見本の設定ファイルは常に読めること ----


def test_example_mission_loads():
    mission = MissionConfig.load(EXAMPLES / "mission.json")
    assert mission.default_mission_phase == MissionPhase("Mercury Science Phase", "msp")


def test_example_dataset_must_be_filled_in():
    # The example still has placeholders, so using it as it is fails
    # 見本はプレースホルダーのままなので、そのまま使うとエラーになる
    with pytest.raises(ConfigError, match="placeholder 'REPLACE_COLLECTION_TITLE'"):
        DatasetConfig.load(EXAMPLES / "dataset_pwi_efd.json")


def test_dataset_paths_are_relative_to_the_json_file(tmp_path):
    dataset = DatasetConfig.load(_write_json(tmp_path / "d.json", dataset_dict()))
    assert dataset.instrument_file == (tmp_path / "instrument_pwi.json").resolve()
    assert dataset.authors_file == (tmp_path / "authors_pwi_efd.json").resolve()


def test_example_authors_load():
    authors = load_authors(EXAMPLES / "authors_pwi_efd.json")
    assert authors[0].family_name == "Shinbori"


# -- strict checks / 厳密なチェック ---------------------------------------------


def test_unknown_key_is_an_error(tmp_path):
    data = dataset_dict()
    data["procesing_level"] = "Raw"  # Typo / 打ち間違い
    with pytest.raises(ConfigError, match="unknown keys"):
        DatasetConfig.load(_write_json(tmp_path / "d.json", data))


def test_missing_required_key_is_an_error(tmp_path):
    data = dataset_dict()
    del data["purpose"]
    with pytest.raises(ConfigError, match="purpose: required key is missing"):
        DatasetConfig.load(_write_json(tmp_path / "d.json", data))


def test_wrong_type_is_an_error(tmp_path):
    data = dataset_dict()
    data["science_facets"]["domains"] = "Magnetosphere"  # Must be a list / リストであるべき
    with pytest.raises(ConfigError, match="domains"):
        DatasetConfig.load(_write_json(tmp_path / "d.json", data))


def test_placeholder_in_a_list_is_an_error(tmp_path):
    data = dataset_dict()
    data["science_facets"]["domains"] = ["Magnetosphere", "REPLACE_DOMAIN"]
    with pytest.raises(ConfigError, match=r"domains\[2\]: placeholder"):
        DatasetConfig.load(_write_json(tmp_path / "d.json", data))


def test_optional_facets_can_be_omitted(tmp_path):
    data = dataset_dict()
    del data["science_facets"]["facet2"]
    dataset = DatasetConfig.load(_write_json(tmp_path / "d.json", data))
    assert dataset.science_facets.facet2 == ""


def test_invalid_json_is_an_error(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"a": 1,}', encoding="utf-8")  # Trailing comma / 末尾のカンマ
    with pytest.raises(ConfigError, match="invalid JSON"):
        MissionConfig.load(path)


def test_missing_file_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        MissionConfig.load(tmp_path / "no_such.json")


def test_empty_authors_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="non-empty"):
        load_authors(_write_json(tmp_path / "a.json", []))


# -- timeline -----------------------------------------------------------------


def _timeline(tmp_path, data) -> MissionTimeline:
    return MissionTimeline.load(_write_json(tmp_path / "t.json", data))


PHASES = [
    {"start": "2026-01-01T00:00:00Z", "stop": "2027-01-01T00:00:00Z",
     "name": "Cruise", "id": "cruise"},
    {"start": "2027-01-01T00:00:00Z", "stop": "2030-01-01T00:00:00Z",
     "name": "Mercury Science Phase", "id": "msp"},
]


def test_timeline_finds_the_phase(tmp_path):
    timeline = _timeline(tmp_path, {"mission_phases": PHASES})
    when = datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert timeline.phase_at(when) == MissionPhase("Cruise", "cruise")


def test_timeline_stop_is_exclusive(tmp_path):
    # start <= t < stop: the boundary belongs to the next period / 境界は次の期間に入る
    timeline = _timeline(tmp_path, {"mission_phases": PHASES})
    when = datetime(2027, 1, 1, tzinfo=timezone.utc)
    assert timeline.phase_at(when).id == "msp"


def test_timeline_without_a_matching_period_is_an_error(tmp_path):
    timeline = _timeline(tmp_path, {"mission_phases": PHASES})
    with pytest.raises(ConfigError, match="No mission phase period"):
        timeline.phase_at(datetime(2031, 1, 1, tzinfo=timezone.utc))


def test_omitted_timeline_list_returns_none(tmp_path):
    timeline = _timeline(tmp_path, {"mission_phases": PHASES})
    assert timeline.target_at(datetime(2026, 6, 1, tzinfo=timezone.utc)) is None


def test_overlapping_periods_are_an_error(tmp_path):
    overlapping = [dict(PHASES[0], stop="2027-06-01T00:00:00Z"), PHASES[1]]
    with pytest.raises(ConfigError, match="overlap"):
        _timeline(tmp_path, {"mission_phases": overlapping})


def test_start_after_stop_is_an_error(tmp_path):
    reversed_period = [dict(PHASES[0], start="2027-06-01T00:00:00Z")]
    with pytest.raises(ConfigError, match="start must be before stop"):
        _timeline(tmp_path, {"mission_phases": reversed_period})


def test_time_without_zone_is_utc(tmp_path):
    naive = [dict(PHASES[0], start="2026-01-01T00:00:00")]
    timeline = _timeline(tmp_path, {"mission_phases": naive})
    assert timeline.mission_phases[0].start == datetime(2026, 1, 1, tzinfo=timezone.utc)
