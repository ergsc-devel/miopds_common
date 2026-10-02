"""Tests for miopds_common.cdf2pdslabel and the miopds-label command.
miopds_common.cdf2pdslabel と miopds-label コマンドのテスト。

A synthetic CDF is used, so no real data is needed.
合成 CDF を使うので、実データは不要。
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from cdf_factory import TEST_TIMES, make_test_cdf
from config_factory import filled_dataset

from miopds_common import cdf2pdslabel
from miopds_common._cli import label_main
from miopds_common._config import ConfigError, MissionPhase

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "config"
TEMPLATES = ROOT / "examples" / "templates"
TEMPLATE = TEMPLATES / "mmo_cdf_label_template_multi_dataset.xml.j2"

NS = {"pds": "http://pds.nasa.gov/pds4/pds/v1", "psa": "http://psa.esa.int/psa/v1"}


def _generator(tmp_path: Path, **options) -> cdf2pdslabel.CDFLabelGenerator:
    return cdf2pdslabel.CDFLabelGenerator(
        TEMPLATE, CONFIG / "mission.json", filled_dataset(tmp_path), **options
    )


def _phase_id(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    return root.findtext(".//psa:Mission_Phase/psa:id", namespaces=NS)


def test_label_contents(tmp_path):
    cdf = make_test_cdf(tmp_path)
    root = ET.fromstring(_generator(tmp_path).render(cdf))

    # LID: YYYYMMDD is replaced by the date in the file name
    # LID の YYYYMMDD がファイル名の日付に置き換わる
    lid = root.findtext("pds:Identification_Area/pds:logical_identifier", namespaces=NS)
    assert lid.endswith("bc_mmo_pwi-efd_l2_20270101")
    # "&" in the CDF title survives as a character / CDF タイトルの "&" が文字として残る
    title = root.findtext("pds:Identification_Area/pds:title", namespaces=NS)
    assert title == "Synthetic PWI-EFD test product & check"
    # Time range from the time variable / 時刻変数から観測期間が入る
    assert root.findtext(".//pds:start_date_time", namespaces=NS) == TEST_TIMES[0]
    assert root.findtext(".//pds:stop_date_time", namespaces=NS) == TEST_TIMES[-1]
    # Instrument from instrument_pwi.json / 機器は instrument_pwi.json から
    components = root.findall(".//pds:Observing_System_Component/pds:name", NS)
    names = [component.text for component in components]
    assert names == ["Mercury Magnetospheric Orbiter", "PWI"]


def test_data_objects_are_in_offset_order(tmp_path):
    cdf = make_test_cdf(tmp_path)
    root = ET.fromstring(_generator(tmp_path).render(cdf))
    area = root.find("pds:File_Area_Observational", NS)
    objects = [child for child in area if not child.tag.endswith(("File", "Header"))]
    names = [obj.findtext("pds:name", namespaces=NS) for obj in objects]
    offsets = [int(obj.findtext("pds:offset", namespaces=NS)) for obj in objects]
    assert sorted(names) == ["E", "epoch", "freq", "strtime"]
    assert offsets == sorted(offsets)


# -- mission phase priority / ミッションフェーズの優先順位 ----------------------


def test_default_phase_comes_from_mission_json(tmp_path):
    cdf = make_test_cdf(tmp_path)
    assert _phase_id(_generator(tmp_path).render(cdf)) == "msp"


def test_timeline_is_used_when_given(tmp_path):
    cdf = make_test_cdf(tmp_path)
    timeline = tmp_path / "timeline.json"
    timeline.write_text(json.dumps({"mission_phases": [
        {"start": "2026-12-01T00:00:00Z", "stop": "2027-02-01T00:00:00Z",
         "name": "Cruise", "id": "cruise"},
    ]}), encoding="utf-8")
    assert _phase_id(_generator(tmp_path, timeline=timeline).render(cdf)) == "cruise"


def test_given_phase_wins_over_timeline(tmp_path):
    cdf = make_test_cdf(tmp_path)
    timeline = tmp_path / "timeline.json"
    timeline.write_text(json.dumps({"mission_phases": [
        {"start": "2026-12-01T00:00:00Z", "stop": "2027-02-01T00:00:00Z",
         "name": "Cruise", "id": "cruise"},
    ]}), encoding="utf-8")
    phase = MissionPhase("Mercury Gravity Assist 1", "mga1")
    generator = _generator(tmp_path, timeline=timeline, mission_phase=phase)
    assert _phase_id(generator.render(cdf)) == "mga1"


def test_timeline_without_matching_period_is_an_error(tmp_path):
    cdf = make_test_cdf(tmp_path)
    timeline = tmp_path / "timeline.json"
    timeline.write_text(json.dumps({"mission_phases": [
        {"start": "2026-01-01T00:00:00Z", "stop": "2026-02-01T00:00:00Z",
         "name": "Cruise", "id": "cruise"},
    ]}), encoding="utf-8")
    with pytest.raises(ConfigError, match="No mission phase period"):
        _generator(tmp_path, timeline=timeline).render(cdf)


# -- writing and the command / 書き出しとコマンド ------------------------------


def test_write_creates_lblx(tmp_path):
    cdf = make_test_cdf(tmp_path)
    output = _generator(tmp_path).write(cdf, tmp_path / "out")
    assert output == tmp_path / "out" / "bc_mmo_pwi-efd_l2_test_20270101_v01.lblx"
    assert output.is_file()


def test_command_succeeds(tmp_path):
    cdf = make_test_cdf(tmp_path)
    status = label_main([
        str(cdf), str(TEMPLATE), str(tmp_path / "out"),
        "--mission-config", str(CONFIG / "mission.json"),
        "--dataset-config", str(filled_dataset(tmp_path)),
        "--mission-phase-name", "Cruise", "--mission-phase-id", "cruise",
    ])
    assert status == 0
    label = (tmp_path / "out" / "bc_mmo_pwi-efd_l2_test_20270101_v01.lblx").read_text()
    assert _phase_id(label) == "cruise"


def test_command_rejects_half_given_phase(tmp_path):
    # --mission-phase-name without --mission-phase-id / 片方だけの指定はエラー
    cdf = make_test_cdf(tmp_path)
    status = label_main([
        str(cdf), str(TEMPLATE), str(tmp_path / "out"),
        "--mission-config", str(CONFIG / "mission.json"),
        "--dataset-config", str(filled_dataset(tmp_path)),
        "--mission-phase-name", "Cruise",
    ])
    assert status == 1
