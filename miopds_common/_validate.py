"""Run NASA PDS Validate and save its output as a report.
NASA の PDS Validate を実行し、出力をレポートとして保存する。

This replaces the validation part that each shell script used to repeat.
各 shell スクリプトで繰り返していた検証処理を、ここにまとめる。
"""

import logging
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TextIO

logger = logging.getLogger(__name__)


def build_validate_command(
    validate_bin: Path | str,
    target: Path | str,
    *,
    catalog: Path | str | None = None,
    rule: str | None = None,
    label_extension: str | None = None,
    report_file: Path | str | None = None,
) -> list[str]:
    """Return the Validate command line (same argument order as the old shells).
    Validate のコマンドラインを返す（引数の順番は以前の shell と同じ）。

    A catalog that does not exist is left out with a warning; an empty value
    means no catalog. report_file is Validate's own report (--report-file).
    存在しないカタログは警告を出して外す。空の値はカタログなしとみなす。
    report_file は Validate 自身が書くレポート（--report-file）。
    """
    command = [_find_validate(validate_bin)]
    if rule:
        command += ["--rule", rule]
    command += ["--target", str(target)]
    if label_extension:
        command += ["--label-extension", label_extension]
    if report_file:
        command += ["--report-file", str(report_file)]
    if catalog:
        if Path(catalog).is_file():
            command += ["--catalog", str(catalog)]
        else:
            logger.warning(
                "XML catalog was not found: %s; "
                "validation will continue without --catalog.",
                catalog,
            )
    return command


def run_validate(
    command: list[str], report: Path | str, *, stream: TextIO | None = None
) -> int:
    """Run Validate, show its output and save it to report. Returns the exit status.
    Validate を実行し、出力を画面に表示しながら report に保存する。終了コードを返す。

    stdout and stderr of Validate are merged, like "2>&1 | tee" in shell.
    shell の "2>&1 | tee" と同じく、標準出力と標準エラー出力をまとめて扱う。
    """
    # Look up sys.stdout at call time, so redirection works
    # 出力先の差し替えが効くよう、sys.stdout は呼び出した時点で参照する
    stream = sys.stdout if stream is None else stream
    report = Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8", newline="\n") as saved, subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    ) as process:
        for line in process.stdout:
            stream.write(line)
            saved.write(line)
    return process.returncode


def format_command(command: list[str]) -> str:
    """Return the command as one line that can be pasted into a shell.
    shell にそのまま貼り付けられる1行の文字列にする。
    """
    return shlex.join(command)


def _find_validate(validate_bin: Path | str) -> str:
    # A bare name such as "validate" is searched in PATH
    # "validate" のような名前だけの指定は、PATH から探す
    text = str(validate_bin)
    if os.sep not in text:
        found = shutil.which(text)
        if found is None:
            raise FileNotFoundError(f"Validate was not found in PATH: {text}")
        return found
    path = Path(text).expanduser()
    if not (path.is_file() and os.access(path, os.X_OK)):
        raise FileNotFoundError(
            f"Validate executable not found or not executable: {path}"
        )
    return str(path)
