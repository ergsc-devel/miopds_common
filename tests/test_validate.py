"""Tests for miopds_common._validate and the miopds-validate command.
miopds_common._validate と miopds-validate コマンドのテスト。

A fake Validate script is used, so Java and PDS Validate are not needed.
偽の Validate スクリプトを使うので、Java と PDS Validate は不要。
"""

import io
import logging
from pathlib import Path

import pytest

from miopds_common._cli import validate_main
from miopds_common._validate import build_validate_command, run_validate


def _fake_validate(tmp_path: Path, status: int = 0) -> Path:
    # Prints its arguments and a line on stderr, then exits with status
    # 引数と標準エラー出力の1行を表示し、指定の終了コードで終わる
    path = tmp_path / "fake_validate"
    path.write_text(
        f'#!/bin/sh\necho "ARGS: $*"\necho "from stderr" >&2\nexit {status}\n'
    )
    path.chmod(0o755)
    return path


def test_argument_order(tmp_path):
    # Same order as the bundle shell on main / main の bundle の shell と同じ順番
    validate = _fake_validate(tmp_path)
    catalog = tmp_path / "catalog.xml"
    catalog.write_text("<catalog/>")
    command = build_validate_command(
        validate, "bundle_dir", catalog=catalog, rule="pds4.bundle",
        label_extension="lblx", report_file="report.txt",
    )
    assert command == [
        str(validate),
        "--rule", "pds4.bundle",
        "--target", "bundle_dir",
        "--label-extension", "lblx",
        "--report-file", "report.txt",
        "--catalog", str(catalog),
    ]


def test_missing_catalog_is_left_out_with_a_warning(tmp_path):
    messages = []
    handler = logging.Handler()
    handler.emit = lambda record: messages.append(record.getMessage())
    logger = logging.getLogger("miopds_common._validate")
    logger.addHandler(handler)
    try:
        command = build_validate_command(
            _fake_validate(tmp_path), "x.xml", catalog=tmp_path / "no_such.xml"
        )
    finally:
        logger.removeHandler(handler)
    assert "--catalog" not in command
    assert any("XML catalog was not found" in message for message in messages)


def test_empty_catalog_means_none(tmp_path):
    command = build_validate_command(_fake_validate(tmp_path), "x.xml", catalog="")
    assert "--catalog" not in command


def test_validate_not_in_path_is_an_error():
    with pytest.raises(FileNotFoundError, match="not found in PATH"):
        build_validate_command("no-such-validate-command", "x.xml")


def test_run_saves_output_and_returns_status(tmp_path):
    command = build_validate_command(_fake_validate(tmp_path, status=3), "x.xml")
    report = tmp_path / "reports" / "report.txt"
    shown = io.StringIO()
    assert run_validate(command, report, stream=shown) == 3
    # stdout and stderr both go to the screen and the report
    # 標準出力と標準エラー出力の両方が、画面とレポートに出る
    saved = report.read_text(encoding="utf-8")
    assert "ARGS: --target x.xml" in saved and "from stderr" in saved
    assert shown.getvalue() == saved


def test_command_success(tmp_path):
    report = tmp_path / "report.txt"
    status = validate_main([
        "label.xml", "--report", str(report),
        "--validate-bin", str(_fake_validate(tmp_path)),
    ])
    assert status == 0
    assert report.is_file()


def test_command_returns_the_validate_status(tmp_path):
    status = validate_main([
        "label.xml", "--report", str(tmp_path / "report.txt"),
        "--validate-bin", str(_fake_validate(tmp_path, status=2)),
    ])
    assert status == 2


def test_command_passes_report_file(tmp_path):
    report = tmp_path / "screen.txt"
    status = validate_main([
        "bundle_dir", "--report", str(report),
        "--report-file", str(tmp_path / "validate_report.txt"),
        "--validate-bin", str(_fake_validate(tmp_path)),
    ])
    assert status == 0
    assert "--report-file" in report.read_text(encoding="utf-8")


def test_command_rejects_one_file_for_both_reports(tmp_path):
    # Two writers on one file would corrupt it / 1つのファイルに2か所から書くと壊れる
    report = tmp_path / "report.txt"
    status = validate_main([
        "bundle_dir", "--report", str(report), "--report-file", str(report),
        "--validate-bin", str(_fake_validate(tmp_path)),
    ])
    assert status == 1


def test_command_with_missing_validate(tmp_path):
    status = validate_main([
        "label.xml", "--report", str(tmp_path / "report.txt"),
        "--validate-bin", str(tmp_path / "no_such_validate"),
    ])
    assert status == 1
