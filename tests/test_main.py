"""Tests for "python -m miopds_common" (miopds_common/__main__.py).
「python -m miopds_common」（miopds_common/__main__.py）のテスト。
"""

import contextlib
import io
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from miopds_common.__main__ import SUBCOMMANDS, main

ROOT = Path(__file__).resolve().parents[1]


def _run(argv: list[str]) -> tuple[int, str]:
    # Run main() and capture what it prints / main() を実行し、表示内容を捕まえる
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        try:
            status = main(argv)
        except SystemExit as error:  # argparse --help / argparse の --help
            status = error.code
    return status, output.getvalue()


def test_help_lists_every_subcommand():
    status, text = _run(["--help"])
    assert status == 0
    for name in ("cdf2pdslabel", "labels2collection", "pdf2pdslabel",
                 "pdf2document", "collections2bundle", "tab2timeline", "validate"):
        assert name in text


def test_no_subcommand_is_a_usage_error():
    assert _run([])[0] == 2


def test_unknown_subcommand_is_a_usage_error():
    status, text = _run(["nosuch"])
    assert status == 2
    assert "unknown subcommand: nosuch" in text


def test_subcommand_help_shows_python_m_form():
    status, text = _run(["validate", "--help"])
    assert status == 0
    assert text.startswith("usage: python -m miopds_common validate")


def test_subcommand_runs(tmp_path):
    validate = tmp_path / "fake_validate"
    validate.write_text("#!/bin/sh\nexit 0\n")
    validate.chmod(0o755)
    status, _ = _run([
        "validate", "x.xml", "--report", str(tmp_path / "report.txt"),
        "--validate-bin", str(validate),
    ])
    assert status == 0


def test_subcommands_match_registered_commands():
    # A subcommand and its miopds-* command must call the same function
    # サブコマンドと miopds-* コマンドは、同じ関数を呼ぶこと
    with (ROOT / "pyproject.toml").open("rb") as stream:
        scripts = tomllib.load(stream)["project"]["scripts"]
    for name, (function, _, command) in SUBCOMMANDS.items():
        assert scripts[command] == f"miopds_common._cli:{function.__name__}", name


def test_python_m_really_works():
    # Start a new Python process, as the shell scripts do
    # shell スクリプトと同じく、新しい Python のプロセスとして起動する
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(ROOT), env.get("PYTHONPATH")])
    )
    result = subprocess.run(
        [sys.executable, "-m", "miopds_common", "--help"],
        capture_output=True, text=True, env=env, check=False,
    )
    assert result.returncode == 0
    assert "cdf2pdslabel" in result.stdout


@pytest.mark.parametrize("name", sorted(SUBCOMMANDS))
def test_every_subcommand_has_help(name):
    status, text = _run([name, "--help"])
    assert status == 0
    assert f"python -m miopds_common {name}" in text
