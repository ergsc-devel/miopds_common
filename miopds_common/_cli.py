"""Command-line entry points (miopds-label, ...).
コマンド（miopds-label など）の入口。

argparse is used only in this module; the tools themselves are plain classes.
argparse はこのモジュールでだけ使う。各ツールは普通の class として書く。
"""

import argparse
import logging
import sys
from pathlib import Path

from miopds_common._config import MissionPhase, Target


def _label_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Generate a PDS4 observational label (.lblx) from a CDF file.",
    )
    parser.add_argument("cdf", type=Path, help="input CDF file")
    parser.add_argument("xml_template", type=Path, help="Jinja2 label template")
    parser.add_argument("output_dir", type=Path, help="output directory")
    parser.add_argument(
        "--mission-config", type=Path, required=True, help="mission.json"
    )
    parser.add_argument(
        "--dataset-config", type=Path, required=True, help="dataset_*.json"
    )
    parser.add_argument(
        "--timeline", type=Path, help="mission_timeline.json (optional)"
    )

    # Overrides with the highest priority / 最優先で使う上書き用の値
    parser.add_argument("--mission-phase-name")
    parser.add_argument("--mission-phase-id")
    parser.add_argument("--target-name")
    parser.add_argument("--target-type")
    parser.add_argument("--target-lid")

    parser.add_argument("--publication-year", type=int)
    parser.add_argument("--description", help="override the CDF description")
    parser.add_argument("--modification-description", default="Initial version")
    parser.add_argument("--header-length", type=int, default=404)
    parser.add_argument(
        "--internal-reference",
        action="append",
        default=[],
        help="LID_OR_LIDVID|REFERENCE_TYPE (repeatable)",
    )
    return parser


def _all_or_none(args: argparse.Namespace, names: list[str]) -> list[str] | None:
    # Options that belong together must be given together
    # 組で使うオプションは、すべて指定するか、すべて省略する
    values = [getattr(args, name) for name in names]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        options = ", ".join("--" + name.replace("_", "-") for name in names)
        raise ValueError(f"These options must be given together: {options}")
    return values


def label_main(
    argv: list[str] | None = None, prog: str = "miopds-label"
) -> int:
    """Entry point of miopds-label. Returns the exit status.
    miopds-label の入口。終了コードを返す（0: 成功、1: 失敗）。
    """
    args = _label_parser(prog).parse_args(argv)
    try:
        # Imported here so that "--help" works quickly / --help を速く表示するため、ここで import
        from miopds_common.cdf2pdslabel import (
            CDFLabelGenerator,
            parse_internal_reference,
        )

        phase = _all_or_none(args, ["mission_phase_name", "mission_phase_id"])
        target = _all_or_none(args, ["target_name", "target_type", "target_lid"])
        generator = CDFLabelGenerator(
            args.xml_template,
            args.mission_config,
            args.dataset_config,
            timeline=args.timeline,
            mission_phase=None if phase is None else MissionPhase(*phase),
            target=None if target is None else Target(*target),
            publication_year=args.publication_year,
            description=args.description,
            modification_description=args.modification_description,
            header_length=args.header_length,
            internal_references=[
                parse_internal_reference(value) for value in args.internal_reference
            ],
        )
        output = generator.write(args.cdf, args.output_dir)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Generated: {output}")
    return 0


def _collection_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Generate a PDS4 Collection label and inventory CSV.",
    )
    parser.add_argument("label_dir", type=Path, help="directory searched for .lblx")
    parser.add_argument("output_dir", type=Path, help="output directory")
    parser.add_argument("template", type=Path, help="Jinja2 collection template")
    parser.add_argument("collection_lid", help="LID of the collection")
    parser.add_argument("output_base", help="base name of the output files")
    parser.add_argument(
        "--mission-config", type=Path, required=True, help="mission.json"
    )
    parser.add_argument(
        "--dataset-config", type=Path, required=True, help="dataset_*.json"
    )
    parser.add_argument("--publication-year", type=int, required=True)
    parser.add_argument("--version-id", default="1.0")
    parser.add_argument(
        "--skip-report",
        type=Path,
        help="file listing labels skipped for missing CDF (keep outside the archive)",
    )
    return parser


def collection_main(
    argv: list[str] | None = None, prog: str = "miopds-collection"
) -> int:
    """Entry point of miopds-collection. Returns the exit status.
    miopds-collection の入口。終了コードを返す（0: 成功、1: 失敗）。
    """
    args = _collection_parser(prog).parse_args(argv)
    _show_warnings()
    try:
        from miopds_common.labels2collection import CollectionBuilder

        builder = CollectionBuilder(
            args.template,
            args.mission_config,
            args.dataset_config,
            collection_lid=args.collection_lid,
            publication_year=args.publication_year,
            version_id=args.version_id,
        )
        result = builder.write(
            args.label_dir, args.output_dir, args.output_base,
            skip_report=args.skip_report,
        )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"LBLX labels found   : {result.labels_found}")
    print(f"Inventory members  : {result.members}")
    print(f"Labels skipped     : {len(result.skipped)}")
    print(f"Inventory CSV      : {result.inventory_path}")
    print(f"Collection label   : {result.label_path}")
    if result.skip_report_path is not None:
        print(f"Skip report        : {result.skip_report_path}")
    return 0


def _bundle_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Generate a PDS4 Bundle label from the Collection labels.",
    )
    parser.add_argument("bundle_dir", type=Path, help="bundle directory")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--bundle-lid", required=True)
    parser.add_argument(
        "--mission-config", type=Path, required=True, help="mission.json"
    )
    parser.add_argument(
        "--instrument-config", type=Path, required=True, help="instrument_*.json"
    )
    parser.add_argument("--publication-year", type=int, required=True)
    parser.add_argument("--version-id", default="1.0")
    parser.add_argument("--modification-date", help="YYYY-MM-DD (default: today, UTC)")
    parser.add_argument(
        "--modification-description", default="Initial release of the bundle."
    )
    parser.add_argument(
        "--output", help="output file name (default: <bundle dir name>.lblx)"
    )
    return parser


def bundle_main(
    argv: list[str] | None = None, prog: str = "miopds-bundle"
) -> int:
    """Entry point of miopds-bundle. Returns the exit status.
    miopds-bundle の入口。終了コードを返す（0: 成功、1: 失敗）。
    """
    args = _bundle_parser(prog).parse_args(argv)
    try:
        from miopds_common.collections2bundle import BundleBuilder

        builder = BundleBuilder(
            args.template,
            args.mission_config,
            args.instrument_config,
            bundle_lid=args.bundle_lid,
            publication_year=args.publication_year,
            version_id=args.version_id,
            modification_date=args.modification_date,
            modification_description=args.modification_description,
        )
        result = builder.write(args.bundle_dir, args.output)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Generated Bundle label: {result.label_path}")
    print(f"Collection members: {len(result.members)}")
    for member in result.members:
        print(f"  {member.lid} ({member.collection_type})")
    return 0


def _add_document_options(parser: argparse.ArgumentParser) -> None:
    # Options of the Product_Document label / Product_Document ラベル用のオプション
    parser.add_argument(
        "--mission-config", type=Path, required=True, help="mission.json"
    )
    parser.add_argument("--document-lid", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--publication-year", type=int, required=True)
    parser.add_argument("--publication-date", required=True)
    parser.add_argument("--version-id", default="1.0")
    parser.add_argument("--modification-date", help="YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--edition-name", default="1.0")
    parser.add_argument("--language", default="English")


def _document_generator(args: argparse.Namespace, template: Path, description: str):
    from miopds_common.pdf2pdslabel import DocumentLabelGenerator

    return DocumentLabelGenerator(
        template,
        args.mission_config,
        document_lid=args.document_lid,
        title=args.title,
        description=args.description,
        publication_year=args.publication_year,
        publication_date=args.publication_date,
        version_id=args.version_id,
        modification_date=args.modification_date,
        modification_description=description,
        edition_name=args.edition_name,
        language=args.language,
    )


def document_main(
    argv: list[str] | None = None, prog: str = "miopds-document"
) -> int:
    """Entry point of miopds-document (one Product_Document label).
    miopds-document（Product_Document ラベル1つ）の入口。終了コードを返す。
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Generate a PDS4 Product_Document label for a PDF file.",
    )
    parser.add_argument("pdf", type=Path, help="document file (PDF)")
    parser.add_argument("--template", type=Path, required=True)
    _add_document_options(parser)
    parser.add_argument("--modification-description", default="Initial version")
    parser.add_argument("--output", help="label file name (default: <PDF name>.lblx)")
    args = parser.parse_args(argv)
    try:
        generator = _document_generator(
            args, args.template, args.modification_description
        )
        output = generator.write(args.pdf, args.output)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Generated document label: {output}")
    return 0


def document_set_main(
    argv: list[str] | None = None, prog: str = "miopds-document-set"
) -> int:
    """Entry point of miopds-document-set (document label + document collection).
    miopds-document-set（Document のラベル＋Document Collection）の入口。
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Generate a Product_Document label and its Document Collection.",
    )
    parser.add_argument("document_dir", type=Path, help="document directory")
    parser.add_argument("--document-template", type=Path, required=True)
    parser.add_argument("--collection-template", type=Path, required=True)
    parser.add_argument(
        "--instrument-config", type=Path, required=True, help="instrument_*.json"
    )
    parser.add_argument("--collection-lid", required=True)
    _add_document_options(parser)
    parser.add_argument(
        "--document-modification-description", default="Initial version"
    )
    parser.add_argument(
        "--collection-modification-description", default="Initial version"
    )
    parser.add_argument("--pdf-file", required=True, help="PDF name in document_dir")
    parser.add_argument("--document-output", help="default: <PDF name>.lblx")
    parser.add_argument("--collection-output", required=True, help="<base>.lblx")
    parser.add_argument("--inventory-output", help="<base>.csv (default)")
    args = parser.parse_args(argv)
    _show_warnings()
    try:
        from miopds_common.labels2collection import CollectionBuilder

        # The collection label and inventory share one base name
        # Collection のラベルとインベントリは同じ名前の元を使う
        collection_output = Path(args.collection_output)
        if collection_output.suffix != ".lblx" or collection_output.name != str(
            collection_output
        ):
            raise ValueError("--collection-output must be a file name ending in .lblx")
        base = collection_output.stem
        if args.inventory_output not in (None, f"{base}.csv"):
            raise ValueError(f"--inventory-output must be {base}.csv")

        document_dir = args.document_dir.resolve()
        label = _document_generator(
            args, args.document_template, args.document_modification_description
        ).write(document_dir / args.pdf_file, args.document_output)
        result = CollectionBuilder.for_documents(
            args.collection_template,
            args.mission_config,
            args.instrument_config,
            collection_lid=args.collection_lid,
            publication_year=args.publication_year,
            version_id=args.version_id,
            modification_date=args.modification_date,
            modification_description=args.collection_modification_description,
        ).write(document_dir, document_dir, base)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Generated document label: {label}")
    print(f"Generated collection inventory: {result.inventory_path}")
    print(f"Generated collection label: {result.label_path}")
    return 0


def timeline_main(
    argv: list[str] | None = None, prog: str = "miopds-timeline"
) -> int:
    """Entry point of miopds-timeline (mission phase table -> mission_timeline.json).
    miopds-timeline（ミッションフェーズの表 → mission_timeline.json）の入口。
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Convert the mission phase table (*.tab) into "
        "mission_timeline.json. The dates are not public: keep both files "
        "only on the server.",
    )
    parser.add_argument("table", type=Path, help="mission phase table (*.tab)")
    parser.add_argument("output", type=Path, help="mission_timeline.json to write")
    parser.add_argument(
        "--end",
        help="stop of the last phase. Without it, the last phase must be msp "
        "and its stop is 2100-01-01T00:00:00Z",
    )
    args = parser.parse_args(argv)
    try:
        from miopds_common.tab2timeline import TimelineConverter

        result = TimelineConverter(end=args.end).write(args.table, args.output)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if result.changed:
        print(f"Generated timeline: {result.path}")
    else:
        print(f"Timeline is up to date (not rewritten): {result.path}")
    return 0


def validate_main(
    argv: list[str] | None = None, prog: str = "miopds-validate"
) -> int:
    """Entry point of miopds-validate. Returns the exit status of Validate.
    miopds-validate の入口。Validate の終了コードを返す。
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Run NASA PDS Validate and save the output as a report.",
    )
    parser.add_argument("target", type=Path, help="label file or bundle directory")
    parser.add_argument(
        "--report", type=Path, required=True, help="file to save the screen output"
    )
    parser.add_argument(
        "--report-file", type=Path, help="Validate's own report (--report-file)"
    )
    parser.add_argument(
        "--validate-bin",
        default="validate",
        help="PDS Validate executable (default: 'validate' in PATH)",
    )
    parser.add_argument("--catalog", help="XML catalog file (empty: none)")
    parser.add_argument("--rule", help='e.g. "pds4.bundle"')
    parser.add_argument("--label-extension", help='e.g. "lblx"')
    args = parser.parse_args(argv)
    _show_warnings()
    if args.report_file is not None and (
        args.report_file.resolve() == args.report.resolve()
    ):
        # Two writers on one file would corrupt it / 1つのファイルに2か所から書くと壊れる
        print(
            "ERROR: --report and --report-file must be different files",
            file=sys.stderr,
        )
        return 1
    from miopds_common._validate import (
        build_validate_command,
        format_command,
        run_validate,
    )

    try:
        command = build_validate_command(
            args.validate_bin,
            args.target,
            catalog=args.catalog,
            rule=args.rule,
            label_extension=args.label_extension,
            report_file=args.report_file,
        )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if "--catalog" in command:
        print(f"Using XML catalog: {args.catalog}")
    elif not args.catalog:
        print("XML catalog is not specified; validation continues without --catalog.")
    print(f"Validating: {args.target}")
    print(f"Validation report: {args.report}")
    print(f"Validation command: {format_command(command)}", flush=True)

    try:
        status = run_validate(command, args.report)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Validation report saved to: {args.report}")
    if args.report_file is not None:
        print(f"Validate's own report (--report-file): {args.report_file}")
    if status != 0:
        print(f"ERROR: Validate exited with status {status}", file=sys.stderr)
        # A negative value means a signal; report it as a plain failure
        # 負の値はシグナルによる終了。単に失敗（1）として返す
        return status if status > 0 else 1
    print("Validate exited with status 0.")
    return 0


def _show_warnings() -> None:
    # Print library warnings as "WARNING: ..." on stderr
    # ライブラリの警告を "WARNING: ..." の形で標準エラー出力に表示する
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
