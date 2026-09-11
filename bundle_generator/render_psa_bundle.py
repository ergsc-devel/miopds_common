#!/usr/bin/env python3

"""Search for the Collection label and generate a PDS4 Bundle label from Jinja2."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from jinja2 import Environment, FileSystemLoader, StrictUndefined

PDS_NS = "http://pds.nasa.gov/pds4/pds/v1"
NS = {"pds": PDS_NS}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--bundle-lid", required=True)
    parser.add_argument("--bundle-vid", default="1.0")
    parser.add_argument("--publication-year", default="2027")
    parser.add_argument("--author-list", default="")  # 旧CLIとの互換用。テンプレートには渡すが使用は任意。
    parser.add_argument("--modification-date", required=True)
    parser.add_argument("--output", default="bundle.xml")
    return parser.parse_args()


def text_of(root: ET.Element, path: str) -> str | None:
    element = root.find(path, NS)
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def load_collections(bundle_dir: Path) -> list[dict[str, str]]:
    collections: list[dict[str, str]] = []
    seen_lids: set[str] = set()

    for label_path in sorted(bundle_dir.rglob("*.xml")):
        try:
            root = ET.parse(label_path).getroot()
        except ET.ParseError:
            continue

        if root.tag != f"{{{PDS_NS}}}Product_Collection":
            continue

        lid = text_of(root, "./pds:Identification_Area/pds:logical_identifier")
        collection_type = text_of(root, "./pds:Collection/pds:collection_type")

        if not lid or not collection_type or lid in seen_lids:
            continue

        seen_lids.add(lid)
        collections.append(
            {
                "lid": lid,
                "member_status": "Primary",
                "collection_type": collection_type.lower(),
                "source_label": str(label_path),
            }
        )

    return collections


def main() -> None:
    args = parse_arguments()
    bundle_dir = args.bundle_dir.resolve()
    template_path = args.template.resolve()

    if not bundle_dir.is_dir():
        raise SystemExit(f"ERROR: Bundle directory not found: {bundle_dir}")
    if not template_path.is_file():
        raise SystemExit(f"ERROR: Template not found: {template_path}")

    collections = load_collections(bundle_dir)
    if not collections:
        raise SystemExit(
            "ERROR: No Product_Collection XML labels were found under "
            f"{bundle_dir}"
        )

    environment = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    rendered = environment.get_template(template_path.name).render(
        bundle_lid=args.bundle_lid,
        bundle_vid=args.bundle_vid,
        publication_year=args.publication_year,
        author_list=args.author_list,
        modification_date=args.modification_date,
        collections=collections,
    )

    output_path = bundle_dir / args.output
    output_path.write_text(rendered, encoding="utf-8", newline="\n")

    print(f"Generated Bundle label: {output_path}")
    print(f"Collection members: {len(collections)}")
    for collection in collections:
        print(f"  {collection['lid']} ({collection['collection_type']})")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
