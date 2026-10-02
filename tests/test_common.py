"""Tests for miopds_common._common.
miopds_common._common のテスト。
"""

import xml.etree.ElementTree as ET

import pytest
from jinja2 import UndefinedError

from miopds_common._common import (
    PDS_NS,
    PDS_NSMAP,
    check_well_formed,
    render_template,
)


def test_render_template_escapes_xml_characters(tmp_path):
    # "&" must become "&amp;" or the XML breaks / "&" は "&amp;" にしないと XML が壊れる
    template = tmp_path / "t.xml.j2"
    template.write_text("<title>{{ title }}</title>\n", encoding="utf-8")
    assert render_template(template, {"title": "A & B"}) == "<title>A &amp; B</title>\n"


def test_render_template_missing_variable_is_error(tmp_path):
    # A forgotten value must not silently become empty / 渡し忘れを空文字にしない
    template = tmp_path / "t.xml.j2"
    template.write_text("<title>{{ title }}</title>\n", encoding="utf-8")
    with pytest.raises(UndefinedError):
        render_template(template, {})


def test_render_template_block_lines_leave_no_blank_lines(tmp_path):
    # Lines with only {% ... %} disappear from the output
    # {% ... %} だけの行は出力に残らない
    template = tmp_path / "t.xml.j2"
    template.write_text(
        "<list>\n"
        "  {% for x in items %}\n"
        "  <i>{{ x }}</i>\n"
        "  {% endfor %}\n"
        "</list>\n",
        encoding="utf-8",
    )
    expected = "<list>\n  <i>1</i>\n  <i>2</i>\n</list>\n"
    assert render_template(template, {"items": [1, 2]}) == expected


def test_check_well_formed_accepts_valid_xml():
    check_well_formed("<a><b/></a>")  # No exception / 例外が出なければ成功


def test_check_well_formed_rejects_broken_xml():
    with pytest.raises(ValueError, match="label.xml"):
        check_well_formed("<a><b></a>", source="label.xml")


def test_pds_nsmap_finds_namespaced_elements():
    # PDS_NSMAP lets find() use the "pds:" prefix / "pds:" 接頭辞で要素を探せる
    root = ET.fromstring(f'<Product xmlns="{PDS_NS}"><title>T</title></Product>')
    assert root.findtext("pds:title", namespaces=PDS_NSMAP) == "T"
