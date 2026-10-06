"""Tests for pdf2pdslabel, CollectionBuilder.for_documents and the document commands.
pdf2pdslabel、CollectionBuilder.for_documents、Document 用コマンドのテスト。
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from miopds_common import labels2collection, pdf2pdslabel
from miopds_common._cli import document_main, document_set_main

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "config"
TEMPLATES = ROOT / "examples" / "templates"
DOCUMENT_TEMPLATE = TEMPLATES / "document_template.xml.j2"
COLLECTION_TEMPLATE = TEMPLATES / "document_collection_template.xml.j2"

COLLECTION_LID = "urn:jaxa:darts:bc_mmo_pwi:document"
DOCUMENT_LID = COLLECTION_LID + ":bc_mmo_pwi_data_user_guide"
PDF_NAME = "bc_mmo_pwi_data_user_guide.pdf"
NS = {"pds": "http://pds.nasa.gov/pds4/pds/v1"}


def _pdf(tmp_path: Path, name: str = PDF_NAME) -> Path:
    path = tmp_path / name
    path.write_bytes(b"%PDF-1.4\n% dummy for tests\n")
    return path


def _document_generator(**options) -> pdf2pdslabel.DocumentLabelGenerator:
    values = {
        "document_lid": DOCUMENT_LID,
        "title": "PWI Data User Guide & notes",
        "description": "A guide.",
        "publication_year": 2027,
        "publication_date": "2027",
    }
    values.update(options)
    return pdf2pdslabel.DocumentLabelGenerator(
        DOCUMENT_TEMPLATE, CONFIG / "mission.json", **values
    )


def _collection_builder() -> labels2collection.CollectionBuilder:
    return labels2collection.CollectionBuilder.for_documents(
        COLLECTION_TEMPLATE,
        CONFIG / "mission.json",
        CONFIG / "instrument_pwi.json",
        collection_lid=COLLECTION_LID,
        publication_year=2027,
    )


# -- Product_Document label ---------------------------------------------------


def test_document_label_contents(tmp_path):
    label = _document_generator().write(_pdf(tmp_path))
    # Compare real paths (/var is a link to /private/var on macOS)
    # 実体のパスで比べる（macOS では /var は /private/var へのリンク）
    assert label == (tmp_path / "bc_mmo_pwi_data_user_guide.lblx").resolve()
    root = ET.fromstring(label.read_text(encoding="utf-8"))
    area = "pds:Identification_Area/"
    assert root.findtext(area + "pds:logical_identifier", namespaces=NS) == DOCUMENT_LID
    # "&" in the title survives / タイトルの "&" が文字として残る
    title = root.findtext(area + "pds:title", namespaces=NS)
    assert title == "PWI Data User Guide & notes"
    version = root.findtext(area + "pds:information_model_version", namespaces=NS)
    assert version == "1.22.0.0"  # From mission.json / mission.json から
    file_name = root.findtext(".//pds:Document_File/pds:file_name", namespaces=NS)
    assert file_name == PDF_NAME


def test_document_label_custom_name(tmp_path):
    label = _document_generator().write(_pdf(tmp_path), "guide_label.lblx")
    assert label.name == "guide_label.lblx"


def test_missing_pdf_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        _document_generator().write(tmp_path / "no_such.pdf")


# -- Document Collection (labels2collection) ------------------------------------


def test_document_collection(tmp_path):
    _document_generator().write(_pdf(tmp_path))
    result = _collection_builder().write(tmp_path, tmp_path, "collection_document")

    assert result.inventory_path.read_bytes() == f"P,{DOCUMENT_LID}::1.0\r\n".encode()
    # No skip report in the delivered directory / 配信されるディレクトリに余分なファイルを作らない
    assert result.skip_report_path is None
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "bc_mmo_pwi_data_user_guide.lblx",
        "bc_mmo_pwi_data_user_guide.pdf",
        "collection_document.csv",
        "collection_document.lblx",
    ]
    root = ET.fromstring(result.label_path.read_text(encoding="utf-8"))
    # Texts and context come from the config files / 文と文脈情報は設定ファイルから
    title = root.findtext("pds:Identification_Area/pds:title", namespaces=NS)
    assert title == "BepiColombo MMO PWI document collection"
    component = ".//pds:Observing_System_Component/pds:name"
    instrument = root.findtext(component, namespaces=NS)
    assert instrument == "PWI"
    investigation = root.findtext(".//pds:Investigation_Area/pds:name", namespaces=NS)
    assert investigation == "BepiColombo"


def test_document_collection_can_be_rebuilt(tmp_path):
    # The collection label from the first run must not become a member
    # 1回目に作った Collection のラベルを、2回目にメンバーにしないこと
    _document_generator().write(_pdf(tmp_path))
    first = _collection_builder().write(tmp_path, tmp_path, "collection_document")
    inventory = first.inventory_path.read_bytes()
    second = _collection_builder().write(tmp_path, tmp_path, "collection_document")
    assert second.inventory_path.read_bytes() == inventory


def test_document_with_missing_file_is_skipped(tmp_path):
    _document_generator().write(_pdf(tmp_path))
    orphan = _document_generator(document_lid=COLLECTION_LID + ":orphan").write(
        _pdf(tmp_path, "orphan.pdf")
    )
    (tmp_path / "orphan.pdf").unlink()  # The label now points to a missing file
    result = _collection_builder().write(tmp_path, tmp_path, "collection_document")
    assert result.members == 1
    assert [label for label, _ in result.skipped] == [orphan]


# -- commands / コマンド ---------------------------------------------------------


def _document_options() -> list[str]:
    return [
        "--mission-config", str(CONFIG / "mission.json"),
        "--document-lid", DOCUMENT_LID,
        "--title", "Guide", "--description", "A guide.",
        "--publication-year", "2027", "--publication-date", "2027",
    ]


def test_document_command(tmp_path):
    pdf = _pdf(tmp_path)
    status = document_main(
        [str(pdf), "--template", str(DOCUMENT_TEMPLATE)] + _document_options()
    )
    assert status == 0
    assert (tmp_path / "bc_mmo_pwi_data_user_guide.lblx").is_file()


def _document_set_args(tmp_path: Path) -> list[str]:
    return [
        str(tmp_path),
        "--document-template", str(DOCUMENT_TEMPLATE),
        "--collection-template", str(COLLECTION_TEMPLATE),
        "--instrument-config", str(CONFIG / "instrument_pwi.json"),
        "--collection-lid", COLLECTION_LID,
        "--pdf-file", PDF_NAME,
        "--collection-output", "collection_bc_mmo_pwi_document.lblx",
    ] + _document_options()


def test_document_set_command(tmp_path):
    _pdf(tmp_path)
    assert document_set_main(_document_set_args(tmp_path)) == 0
    assert (tmp_path / "collection_bc_mmo_pwi_document.csv").is_file()
    assert (tmp_path / "collection_bc_mmo_pwi_document.lblx").is_file()


def test_document_set_rejects_mismatched_inventory_name(tmp_path):
    _pdf(tmp_path)
    args = _document_set_args(tmp_path) + ["--inventory-output", "other.csv"]
    assert document_set_main(args) == 1
