"""Run the miopds_common tools with "python -m miopds_common <subcommand> ...".
「python -m miopds_common <サブコマンド> ...」で各ツールを実行する入口。

Subcommands are named after the subpackages. Each one calls a function in
miopds_common/_cli.py (the same function as the miopds-* command).
サブコマンド名はサブパッケージ名に揃えている。各サブコマンドは
miopds_common/_cli.py の関数（miopds-* コマンドと同じもの）を呼ぶ。

Example / 例:
    python -m miopds_common --help
    python -m miopds_common cdf2pdslabel --help
"""

import sys

from miopds_common import _cli

# subcommand -> (function in _cli.py, description, miopds-* command)
# サブコマンド -> （_cli.py の関数、説明、同じ処理の miopds-* コマンド）
SUBCOMMANDS = {
    "cdf2pdslabel": (
        _cli.label_main, "CDF -> observational label (.lblx)", "miopds-label"
    ),
    "labels2collection": (
        _cli.collection_main, "labels -> Collection label + inventory",
        "miopds-collection",
    ),
    "pdf2pdslabel": (
        _cli.document_main, "PDF -> Product_Document label", "miopds-document"
    ),
    "pdf2document": (
        _cli.document_set_main,
        "PDF -> Product_Document label + Document Collection",
        "miopds-document-set",
    ),
    "collections2bundle": (
        _cli.bundle_main, "Collection labels -> Bundle label", "miopds-bundle"
    ),
    "validate": (
        _cli.validate_main, "run NASA PDS Validate and save the report",
        "miopds-validate",
    ),
}

_PROG = "python -m miopds_common"


def _usage() -> str:
    lines = [f"usage: {_PROG} <subcommand> [options]", "", "subcommands:"]
    for name, (function, description, command) in SUBCOMMANDS.items():
        lines.append(f"  {name:<20}{description}")
        lines.append(f"  {'':<20}(_cli.{function.__name__}, same as {command})")
    lines.append("")
    lines.append(f"Run '{_PROG} <subcommand> --help' for the options.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Dispatch to the subcommand and return its exit status.
    サブコマンドに振り分け、その終了コードを返す。
    """
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(_usage())
        return 0 if argv else 2
    name, rest = argv[0], argv[1:]
    if name not in SUBCOMMANDS:
        print(f"ERROR: unknown subcommand: {name}\n", file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2
    function = SUBCOMMANDS[name][0]
    return function(rest, prog=f"{_PROG} {name}")


if __name__ == "__main__":
    raise SystemExit(main())
