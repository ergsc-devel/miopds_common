"""Tests for miopds_common.labels2collection and the miopds-collection command.
miopds_common.labels2collection と miopds-collection コマンドのテスト。
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from cdf_factory import make_test_cdf
from config_factory import filled_dataset

from miopds_common import cdf2pdslabel, labels2collection
from miopds_common._cli import collection_main
from miopds_common.filetool import md5_of_bytes

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "config"
TEMPLATES = ROOT / "examples" / "templates"
LABEL_TEMPLATE = TEMPLATES / "mmo_cdf_label_template_multi_dataset.xml.j2"
COLLECTION_TEMPLATE = TEMPLATES / "collection_template.xml.j2"

COLLECTION_LID = "urn:jaxa:darts:bc_mmo_pwi:data_calibrated_efd"
MEMBER_LID = COLLECTION_LID + ":bc_mmo_pwi-efd_l2_20270101"
OTHER_LID = "urn:jaxa:darts:bc_mmo_pwi:other_collection:bc_mmo_pwi-efd_l2_20270101"
NS = {"pds": "http://pds.nasa.gov/pds4/pds/v1"}


def _make_labels(tmp_path: Path) -> Path:
    """Create four labels: member, missing CDF, other collection, broken XML.
    4種類のラベルを作る：通常、CDF なし、別の Collection、壊れた XML。
    """
    science = tmp_path / "science"
    science.mkdir()
    cdf = make_test_cdf(science)
    generator = cdf2pdslabel.CDFLabelGenerator(
        LABEL_TEMPLATE, CONFIG / "mission.json", filled_dataset(tmp_path)
    )
    text = generator.write(cdf, science).read_text(encoding="utf-8")

    missing = text.replace(cdf.name, "no_such_20270102.cdf").replace(
        "l2_20270101<", "l2_20270102<"
    )
    (science / "missing.lblx").write_text(missing, encoding="utf-8")
    other = text.replace(MEMBER_LID, OTHER_LID)
    (science / "other.lblx").write_text(other, encoding="utf-8")
    (science / "broken.lblx").write_text("<Product_Observational><broken>")
    return science


def _builder(tmp_path: Path, template: Path = COLLECTION_TEMPLATE):
    return labels2collection.CollectionBuilder(
        template,
        CONFIG / "mission.json",
        filled_dataset(tmp_path),
        collection_lid=COLLECTION_LID,
        publication_year=2027,
    )


def test_inventory_and_label(tmp_path):
    result = _builder(tmp_path).write(_make_labels(tmp_path), tmp_path / "out", "coll")

    # CRLF, sorted by LID, primary/secondary by LID prefix
    # CRLF 区切り、LID の順、LID の接頭辞で P/S を判定
    inventory = result.inventory_path.read_bytes()
    assert inventory == (
        f"P,{MEMBER_LID}::1.0\r\nS,{OTHER_LID}::1.0\r\n".encode("utf-8")
    )
    assert (result.labels_found, result.members, len(result.skipped)) == (4, 2, 1)

    root = ET.fromstring(result.label_path.read_text(encoding="utf-8"))
    area = "pds:Identification_Area/"
    lid = root.findtext(area + "pds:logical_identifier", namespaces=NS)
    assert lid == COLLECTION_LID
    # Texts come from the dataset config; "&" is escaped correctly
    # 文は dataset の設定から入り、"&" も正しく置き換わる
    assert root.findtext(area + "pds:title", namespaces=NS) == "Test collection & more"
    assert root.findtext("pds:Collection/pds:collection_type", namespaces=NS) == "Data"
    assert root.findtext(area + "pds:information_model_version", namespaces=NS) == (
        "1.22.0.0"
    )
    # File size, checksum and record count match the CSV / CSV と一致すること
    file_area = "pds:File_Area_Inventory/"
    size = root.findtext(file_area + "pds:File/pds:file_size", namespaces=NS)
    md5 = root.findtext(file_area + "pds:File/pds:md5_checksum", namespaces=NS)
    records = root.findtext(file_area + "pds:Inventory/pds:records", namespaces=NS)
    assert int(size) == len(inventory)
    assert md5 == md5_of_bytes(inventory)
    assert int(records) == 2


def test_skip_report_is_written_where_requested(tmp_path):
    # The report goes to the given place, outside the archive
    # 一覧は指定した場所（アーカイブの外）に書かれる
    report_path = tmp_path / "reports" / "skipped.txt"
    result = _builder(tmp_path).write(
        _make_labels(tmp_path), tmp_path / "out", "coll", skip_report=report_path
    )
    assert result.skip_report_path == report_path.resolve()
    report = report_path.read_text(encoding="utf-8")
    assert "missing.lblx" in report
    assert "Missing CDF:" in report and "no_such_20270102.cdf" in report
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "coll.csv",
        "coll.lblx",
    ]


def test_no_skip_report_by_default(tmp_path):
    # Without skip_report: no file, but a warning / 指定しなければファイルは作らず警告だけ
    messages = []
    handler = logging.Handler()
    handler.emit = lambda record: messages.append(record.getMessage())
    logger = logging.getLogger("miopds_common.labels2collection.builder")
    logger.addHandler(handler)
    try:
        result = _builder(tmp_path).write(
            _make_labels(tmp_path), tmp_path / "out", "coll"
        )
    finally:
        logger.removeHandler(handler)
    assert result.skip_report_path is None
    assert not list((tmp_path / "out").glob("*skipped*"))
    assert any("missing CDF; skipped" in message for message in messages)


def test_broken_label_gives_a_warning(tmp_path):
    messages = []
    handler = logging.Handler()
    handler.emit = lambda record: messages.append(record.getMessage())
    logger = logging.getLogger("miopds_common.labels2collection.builder")
    logger.addHandler(handler)
    try:
        _builder(tmp_path).write(_make_labels(tmp_path), tmp_path / "out", "coll")
    finally:
        logger.removeHandler(handler)
    assert any("malformed XML skipped" in message for message in messages)


def test_collection_label_is_not_a_member(tmp_path):
    # The collection label is .lblx too; written into the label directory,
    # it must not become a member on the next run
    # Collection のラベルも .lblx。ラベルのディレクトリに書いても、
    # 次の実行でメンバーにならないこと
    labels = _make_labels(tmp_path)
    first = _builder(tmp_path).write(labels, labels, "coll")
    second = _builder(tmp_path).write(labels, labels, "coll")
    assert first.label_path.suffix == ".lblx"
    assert second.inventory_path.read_bytes() == first.inventory_path.read_bytes()
    assert second.members == 2


def test_no_member_is_an_error(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="No eligible"):
        _builder(tmp_path).write(empty, tmp_path / "out", "coll")


def test_nothing_is_written_when_the_xml_is_broken(tmp_path):
    # A template that produces broken XML / 壊れた XML を作るテンプレート
    template = tmp_path / "broken.xml.j2"
    template.write_text("<a>{{ collection_lid }}</b>\n", encoding="utf-8")
    labels = _make_labels(tmp_path)
    with pytest.raises(ValueError, match="not well-formed"):
        _builder(tmp_path, template).write(labels, tmp_path / "out", "coll")
    assert not (tmp_path / "out" / "coll.csv").exists()


def test_command_succeeds(tmp_path):
    labels = _make_labels(tmp_path)
    status = collection_main([
        str(labels), str(tmp_path / "out"), str(COLLECTION_TEMPLATE),
        COLLECTION_LID, "coll",
        "--mission-config", str(CONFIG / "mission.json"),
        "--dataset-config", str(filled_dataset(tmp_path)),
        "--publication-year", "2027",
    ])
    assert status == 0
    assert (tmp_path / "out" / "coll.lblx").is_file()


def test_command_requires_publication_year(tmp_path):
    with pytest.raises(SystemExit):
        collection_main([
            "labels", "out", str(COLLECTION_TEMPLATE), COLLECTION_LID, "coll",
            "--mission-config", str(CONFIG / "mission.json"),
            "--dataset-config", str(CONFIG / "dataset_pwi_efd.json"),
        ])
