"""Tests for miopds_common.collections2bundle and the miopds-bundle command.
miopds_common.collections2bundle と miopds-bundle コマンドのテスト。
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from miopds_common import collections2bundle
from miopds_common._cli import bundle_main

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "config"
TEMPLATE = ROOT / "examples" / "templates" / "bundle_template.xml.j2"
BUNDLE_LID = "urn:jaxa:darts:bc_mmo_pwi"
NS = {"pds": "http://pds.nasa.gov/pds4/pds/v1"}
PDS = "http://pds.nasa.gov/pds4/pds/v1"


def _collection_xml(lid: str, collection_type: str) -> str:
    # Minimal Product_Collection label / 最小限の Product_Collection ラベル
    return (
        f'<Product_Collection xmlns="{PDS}"><Identification_Area>'
        f"<logical_identifier>{lid}</logical_identifier></Identification_Area>"
        f"<Collection><collection_type>{collection_type}</collection_type>"
        "</Collection></Product_Collection>"
    )


def _make_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bc_mmo_pwi"
    (bundle / "data_calibrated_efd").mkdir(parents=True)
    (bundle / "document").mkdir()
    (bundle / "zz_copy").mkdir()
    (bundle / "data_calibrated_efd" / "collection.lblx").write_text(
        _collection_xml(BUNDLE_LID + ":data_calibrated_efd", "Data")
    )
    (bundle / "document" / "collection.lblx").write_text(
        _collection_xml(BUNDLE_LID + ":document", "Document")
    )
    # Same LID again: used only once / 同じ LID は1回だけ使う
    (bundle / "zz_copy" / "collection.lblx").write_text(
        _collection_xml(BUNDLE_LID + ":document", "Document")
    )
    # Not a collection, and broken XML: ignored / Collection 以外と壊れた XML は無視
    (bundle / "old_bundle.lblx").write_text(f'<Product_Bundle xmlns="{PDS}"/>')
    (bundle / "broken.lblx").write_text("<Product_Collection>")
    # .xml labels are not used (labels are .lblx) / .xml のラベルは使わない
    (bundle / "zz_copy" / "old_collection.xml").write_text(
        _collection_xml(BUNDLE_LID + ":old_xml", "Data")
    )
    return bundle


def _builder(**options) -> collections2bundle.BundleBuilder:
    options.setdefault("instrument", CONFIG / "instrument_pwi.json")
    return collections2bundle.BundleBuilder(
        TEMPLATE,
        CONFIG / "mission.json",
        bundle_lid=BUNDLE_LID,
        publication_year=2027,
        **options,
    )


def test_members(tmp_path):
    result = _builder().write(_make_bundle(tmp_path))
    # Default name: <bundle directory name>.lblx / 既定の名前は <Bundle ディレクトリ名>.lblx
    assert result.label_path.name == "bc_mmo_pwi.lblx"
    assert [(m.lid, m.collection_type) for m in result.members] == [
        (BUNDLE_LID + ":data_calibrated_efd", "data"),
        (BUNDLE_LID + ":document", "document"),
    ]


def test_label_contents(tmp_path):
    result = _builder(modification_date="2026-10-01").write(_make_bundle(tmp_path))
    root = ET.fromstring(result.label_path.read_text(encoding="utf-8"))
    area = "pds:Identification_Area/"
    assert root.findtext(area + "pds:logical_identifier", namespaces=NS) == BUNDLE_LID
    # Title from instrument_pwi.json / title は instrument_pwi.json から
    title = root.findtext(area + "pds:title", namespaces=NS)
    assert title == "BepiColombo Mio Plasma Wave Investigation Bundle"
    detail = area + "pds:Modification_History/pds:Modification_Detail/"
    date = root.findtext(detail + "pds:modification_date", namespaces=NS)
    assert date == "2026-10-01"
    references = [
        e.text for e in root.findall("pds:Bundle_Member_Entry/pds:reference_type", NS)
    ]
    assert references == [
        "bundle_has_data_collection",
        "bundle_has_document_collection",
    ]


def test_title_with_ampersand(tmp_path):
    # "&" must not break the XML / "&" で XML が壊れないこと
    data = json.loads((CONFIG / "instrument_pwi.json").read_text(encoding="utf-8"))
    data["bundle"]["title"] = "PWI Data & Documents"
    instrument = tmp_path / "instrument.json"
    instrument.write_text(json.dumps(data), encoding="utf-8")
    result = _builder(instrument=instrument).write(_make_bundle(tmp_path))
    root = ET.fromstring(result.label_path.read_text(encoding="utf-8"))
    title = root.findtext("pds:Identification_Area/pds:title", namespaces=NS)
    assert title == "PWI Data & Documents"


def test_default_modification_date_is_today(tmp_path):
    result = _builder().write(_make_bundle(tmp_path))
    text = result.label_path.read_text(encoding="utf-8")
    assert datetime.now(timezone.utc).date().isoformat() in text


def test_no_collection_is_an_error(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="No Product_Collection"):
        _builder().write(empty)


def test_command_succeeds(tmp_path):
    bundle = _make_bundle(tmp_path)
    status = bundle_main([
        str(bundle), "--template", str(TEMPLATE), "--bundle-lid", BUNDLE_LID,
        "--mission-config", str(CONFIG / "mission.json"),
        "--instrument-config", str(CONFIG / "instrument_pwi.json"),
        "--publication-year", "2027",
    ])
    assert status == 0
    assert (bundle / "bc_mmo_pwi.lblx").is_file()


def test_command_requires_instrument_config(tmp_path):
    with pytest.raises(SystemExit):
        bundle_main([
            str(tmp_path), "--template", str(TEMPLATE), "--bundle-lid", BUNDLE_LID,
            "--mission-config", str(CONFIG / "mission.json"),
            "--publication-year", "2027",
        ])
