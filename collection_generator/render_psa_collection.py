#!/usr/bin/env python3
"""Generate a PDS4 Collection inventory CSV and Product_Collection XML.

Usage:
    render_psa_collection.py LABEL_DIR OUTPUT_DIR TEMPLATE COLLECTION_LID OUTPUT_BASE

Only .lblx labels are considered. A label is included only when every CDF
referenced by its <file_name> elements exists beside the label.
"""

from __future__ import annotations

import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

PDS_NS = {"p": "http://pds.nasa.gov/pds4/pds/v1"}


def usage() -> None:
    print(
        f"Usage: {Path(sys.argv[0]).name} "
        "LABEL_DIR OUTPUT_DIR TEMPLATE COLLECTION_LID OUTPUT_BASE",
        file=sys.stderr,
    )


def referenced_cdf_files(label: Path, root: ET.Element) -> list[Path]:
    files: list[Path] = []
    for elem in root.findall(".//p:File/p:file_name", PDS_NS):
        if elem.text:
            name = elem.text.strip()
            if name.lower().endswith(".cdf"):
                files.append(label.parent / name)
    return files


def main() -> int:
    if len(sys.argv) != 6:
        usage()
        return 2

    input_dir = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    template_file = Path(sys.argv[3]).resolve()
    collection_lid = sys.argv[4].strip()
    output_base = sys.argv[5].strip()

    if not input_dir.is_dir():
        raise FileNotFoundError(f"Label directory not found: {input_dir}")
    if not template_file.is_file():
        raise FileNotFoundError(f"Template not found: {template_file}")
    if not collection_lid:
        raise ValueError("Collection LID is empty")
    if not output_base:
        raise ValueError("Output base is empty")

    rows: list[tuple[str, str, str]] = []
    skipped: list[tuple[Path, list[Path]]] = []

    labels = sorted(list(input_dir.rglob("*.lblx")) + list(input_dir.rglob("*.LBLX")))

    for label in labels:
        try:
            root = ET.parse(label).getroot()
        except ET.ParseError as exc:
            print(f"WARNING: malformed XML skipped: {label}: {exc}", file=sys.stderr)
            continue

        cdf_files = referenced_cdf_files(label, root)
        missing = [path for path in cdf_files if not path.is_file()]
        if missing:
            skipped.append((label, missing))
            continue

        lid = root.findtext(
            "./p:Identification_Area/p:logical_identifier",
            namespaces=PDS_NS,
        )
        vid = root.findtext(
            "./p:Identification_Area/p:version_id",
            namespaces=PDS_NS,
        )

        if not lid or not vid:
            print(f"WARNING: LID or VID missing; skipped: {label}", file=sys.stderr)
            continue

        # Collection members whose LID begins with collection_lid + ':' are primary.
        status = "P" if lid.startswith(collection_lid + ":") else "S"
        rows.append((status, lid.strip(), vid.strip()))

    if not rows:
        raise RuntimeError("No eligible .lblx labels with available CDF files were found")

    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / f"{output_base}.csv"
    collection_path = output_dir / f"{output_base}.xml"
    skip_path = output_dir / f"{output_base}_skipped_missing_cdf.txt"

    # PDS DSV inventory uses CRLF record delimiters.
    inventory = "".join(
        f"{status},{lid}::{vid}\r\n"
        for status, lid, vid in sorted(rows, key=lambda row: (row[1], row[2]))
    ).encode("utf-8")
    inventory_path.write_bytes(inventory)

    env = Environment(
        loader=FileSystemLoader(str(template_file.parent)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(default=True),
        keep_trailing_newline=True,
    )
    xml_text = env.get_template(template_file.name).render(
        lid=collection_lid,
        csv=inventory_path.name,
        size=len(inventory),
        md5=hashlib.md5(inventory).hexdigest(),
        records=len(rows),
    )

    # Verify well-formed XML before writing the final collection label.
    ET.fromstring(xml_text)
    collection_path.write_text(xml_text, encoding="utf-8", newline="\n")

    with skip_path.open("w", encoding="utf-8", newline="\n") as stream:
        for label, missing_files in skipped:
            stream.write(f"SKIP: {label}\n")
            for missing_file in missing_files:
                stream.write(f"  Missing CDF: {missing_file}\n")

    print(f"LBLX labels found   : {len(labels)}")
    print(f"Inventory members  : {len(rows)}")
    print(f"Labels skipped     : {len(skipped)}")
    print(f"Inventory CSV      : {inventory_path}")
    print(f"Collection XML     : {collection_path}")
    print(f"Skip report        : {skip_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
