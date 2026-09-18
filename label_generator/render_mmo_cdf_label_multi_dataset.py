#!/usr/bin/env python3
"""Generate a PDS4 observational label for a BepiColombo Mio CDF product."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import cdflib
import cdftool
import numpy as np
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


# Map CDF data types to PDS4 data type names.
TYPE_MAP = {
    1: "SignedByte",
    2: "SignedMSB2",
    4: "SignedMSB4",
    8: "SignedMSB8",
    11: "UnsignedByte",
    12: "UnsignedMSB2",
    14: "UnsignedMSB4",
    21: "IEEE754MSBSingle",
    22: "IEEE754MSBDouble",
    31: "SignedMSB8",
    32: "SignedMSB8",
    33: "SignedMSB8",
    41: "ASCII_String",
    51: "ASCII_String",
    "CDF_INT1": "SignedByte",
    "CDF_INT2": "SignedMSB2",
    "CDF_INT4": "SignedMSB4",
    "CDF_INT8": "SignedMSB8",
    "CDF_UINT1": "UnsignedByte",
    "CDF_UINT2": "UnsignedMSB2",
    "CDF_UINT4": "UnsignedMSB4",
    "CDF_REAL4": "IEEE754MSBSingle",
    "CDF_FLOAT": "IEEE754MSBSingle",
    "CDF_REAL8": "IEEE754MSBDouble",
    "CDF_DOUBLE": "IEEE754MSBDouble",
    "CDF_TIME_TT2000": "SignedMSB8",
    "CDF_EPOCH": "IEEE754MSBDouble",
    "CDF_CHAR": "ASCII_String",
    "CDF_UCHAR": "ASCII_String",
}


# Profile defaults may be overridden by command-line options.
PROFILES = {
    "pwi-efd": {
        "instrument_name": "PWI",
        "instrument_lid": "urn:jaxa:darts:context:instrument:mmo.pwi",
        "processing_level": "Calibrated",
        "domains": ["Heliosphere", "Magnetosphere"],
        "discipline_name": "Fields",
        "facet1": "Electric",
        "facet2": "Waves",
        "mission_phase_name": "Cruise",
        "mission_phase_id": "cruise",
    },
    "mppe-ena": {
        "instrument_name": "MPPE",
        "instrument_lid": "urn:jaxa:darts:context:instrument:mmo.mppe",
        "processing_level": "Calibrated",
        "domains": ["Magnetosphere"],
        "discipline_name": "Particles",
        "facet1": "Neutrals",
        "facet2": "",
        "mission_phase_name": "Cruise",
        "mission_phase_id": "cruise",
    },
    "mgf": {
        "instrument_name": "MGF",
        "instrument_lid": "urn:jaxa:darts:context:instrument:mmo.mgf",
        "processing_level": "Calibrated",
        "domains": ["Heliosphere", "Magnetosphere"],
        "discipline_name": "Fields",
        "facet1": "Magnetic",
        "facet2": "",
        "mission_phase_name": "Cruise",
        "mission_phase_id": "cruise",
    },
}


# Citation authors are represented as the structured PDS4 List_Author class.
DEFAULT_AUTHORS = [
    {"display_full_name": "Shinbori, A.", "given_name": "A.", "family_name": "Shinbori"},
    {"display_full_name": "Kasaba, Y.", "given_name": "Y.", "family_name": "Kasaba"},
    {"display_full_name": "Kojima, H.", "given_name": "H.", "family_name": "Kojima"},
    {"display_full_name": "Moncuquet, M.", "given_name": "M.", "family_name": "Moncuquet"},
    {"display_full_name": "Bougeret, J.-L.", "given_name": "J.-L.", "family_name": "Bougeret"},
    {"display_full_name": "Blomberg, L. G.", "given_name": "L. G.", "family_name": "Blomberg"},
    {"display_full_name": "Yagitani, S.", "given_name": "S.", "family_name": "Yagitani"},
]


def scalar(value, default="") -> str:
    """Convert a CDF value into one normalized string."""
    if value is None:
        return str(default)
    if hasattr(value, "reshape") and hasattr(value, "size"):
        if int(value.size) == 0:
            return str(default)
        value = value.reshape(-1)[0]
    elif isinstance(value, (list, tuple)):
        if not value:
            return str(default)
        value = value[0]
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    text = str(value).strip()
    return text if text else str(default)


def attr(attributes: dict, name: str, default="") -> str:
    """Read a CDF attribute using a case-insensitive key lookup."""
    for key, value in attributes.items():
        if key.lower() == name.lower():
            return scalar(value, default)
    return str(default)


def field(info, *names, default=None):
    """Read a field from a mapping or an object returned by cdflib."""
    for name in names:
        if isinstance(info, dict) and name in info:
            return info[name]
        if hasattr(info, name):
            return getattr(info, name)
    return default


def md5sum(path: Path) -> str:
    """Calculate the MD5 checksum without loading the entire file."""
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def yyyymmdd_from_name(name: str) -> str:
    """Extract the observation date from the CDF filename."""
    match = re.search(r"_(\d{8})(?:_|\.)", name)
    if not match:
        raise ValueError(f"Could not extract YYYYMMDD from CDF filename: {name}")
    return match.group(1)


def time_bounds(cdf, variable_name: str) -> tuple[str, str]:
    """Return the first and last values of the configured time variable."""
    values = np.asarray(cdf.varget(variable_name))
    if values.size == 0:
        raise ValueError(f"Time variable is empty: {variable_name}")
    values = values.reshape(-1)
    return scalar(values[0]), scalar(values[-1])


def variable_record_count(cdf, name: str, record_varying: bool) -> int:
    """Return the logical record count actually readable from the CDF."""
    if not record_varying:
        return 1
    values = np.asarray(cdf.varget(name))
    return 1 if values.ndim == 0 else int(values.shape[0])


def validate_time_record_counts(cdf, names, epoch_name: str, time_name: str) -> int:
    """Require the epoch and text-time variables to have equal record counts."""
    if epoch_name not in names:
        raise ValueError(f"Epoch variable was not found: {epoch_name}")
    if time_name not in names:
        raise ValueError(f"Time variable was not found: {time_name}")
    epoch_count = variable_record_count(cdf, epoch_name, True)
    time_count = variable_record_count(cdf, time_name, True)
    if epoch_count != time_count:
        raise ValueError(
            f"CDF time record count mismatch: {epoch_name}={epoch_count}, "
            f"{time_name}={time_count}"
        )
    return epoch_count



def load_authors(path: Path) -> list[dict[str, str]]:
    """Load and validate an instrument-specific List_Author JSON file."""
    authors_path = path.expanduser().resolve()
    if not authors_path.is_file():
        raise FileNotFoundError(f"Authors file was not found: {authors_path}")
    with authors_path.open("r", encoding="utf-8") as stream:
        authors = json.load(stream)
    if not isinstance(authors, list) or not authors:
        raise ValueError("The authors file must contain a non-empty JSON list.")
    required = ("display_full_name", "given_name", "family_name")
    normalized = []
    for index, author in enumerate(authors, start=1):
        if not isinstance(author, dict):
            raise ValueError(f"Author {index} must be a JSON object.")
        item = {}
        for key in required:
            value = str(author.get(key, "")).strip()
            if not value:
                raise ValueError(f"Author {index} is missing a non-empty {key}.")
            item[key] = value
        normalized.append(item)
    return normalized

def parse_internal_references(values):
    """Parse repeated LID_OR_LIDVID|REFERENCE_TYPE command-line values."""
    references = []
    for value in values:
        identifier, separator, reference_type = value.partition("|")
        identifier = identifier.strip()
        reference_type = reference_type.strip()
        if not separator or not identifier or not reference_type:
            raise ValueError(
                f"Invalid --internal-reference value: {value!r}. "
                "Expected 'LID_OR_LIDVID|REFERENCE_TYPE'."
            )
        reference = {"reference_type": reference_type}
        key = "lidvid_reference" if "::" in identifier else "lid_reference"
        reference[key] = identifier
        references.append(reference)
    return references


def build_parser() -> argparse.ArgumentParser:
    """Create the renderer command-line parser."""
    parser = argparse.ArgumentParser(
        description="Generate a PDS4 observational label from a CDF file."
    )
    parser.add_argument("cdf", type=Path)
    parser.add_argument("xml_template", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--time-variable", default="strtime")
    parser.add_argument("--epoch-variable", default="epoch")
    parser.add_argument("--information-model-version", default="1.22.0.0")
    parser.add_argument("--header-length", type=int, default=404)
    parser.add_argument("--publication-year", type=int)
    parser.add_argument("--description")
    parser.add_argument(
        "--authors-file", type=Path, required=True,
        help="JSON file containing the structured citation author list",
    )
    parser.add_argument("--profile", choices=sorted(PROFILES), default="pwi-efd")
    parser.add_argument("--purpose", default="Science")
    parser.add_argument("--instrument-name")
    parser.add_argument("--processing-level")
    parser.add_argument("--domain", action="append", dest="domains")
    parser.add_argument("--discipline-name")
    parser.add_argument("--facet1")
    parser.add_argument("--facet2")
    parser.add_argument("--mission-phase-name")
    parser.add_argument("--mission-phase-id")
    parser.add_argument("--target-name", default="Mercury")
    parser.add_argument("--target-type", default="Planet")
    parser.add_argument("--target-lid", default="urn:nasa:pds:context:target:planet.mercury")
    parser.add_argument("--investigation-name", default="BepiColombo")
    parser.add_argument("--investigation-type", default="Mission")
    parser.add_argument("--investigation-lid", default="urn:esa:psa:context:investigation:mission.bc")
    parser.add_argument("--instrument-host-name", default="Mercury Magnetospheric Orbiter")
    parser.add_argument("--instrument-host-lid", default="urn:jaxa:darts:context:instrument_host:spacecraft.mmo")
    parser.add_argument("--instrument-lid")
    parser.add_argument("--cdf-parsing-standard-id", default="CDF 3.4 ISTP/IACG")
    parser.add_argument("--internal-reference", action="append", default=[])
    return parser


def main() -> None:
    """Read the CDF, build template data, and write the LBLX file."""
    args = build_parser().parse_args()
    authors = load_authors(args.authors_file)
    profile = dict(PROFILES[args.profile])
    for key in (
        "instrument_name", "instrument_lid", "processing_level", "domains",
        "discipline_name", "facet1", "facet2", "mission_phase_name",
        "mission_phase_id",
    ):
        value = getattr(args, key, None)
        if value is not None:
            profile[key] = value

    cdf_path = args.cdf.resolve()
    template_path = args.xml_template.resolve()
    if not cdf_path.is_file():
        raise FileNotFoundError(cdf_path)
    if not template_path.is_file():
        raise FileNotFoundError(template_path)

    cdf = cdflib.CDF(str(cdf_path))
    globals_ = cdf.globalattsget()
    cdf_info = cdf.cdf_info()
    physical = cdftool.cdfinfo(str(cdf_path))
    names = list(cdf_info.zVariables)
    start_time, stop_time = time_bounds(cdf, args.time_variable)
    time_count = validate_time_record_counts(
        cdf, names, args.epoch_variable, args.time_variable
    )

    # Build one PDS4 object description for each CDF zVariable.
    objects = []
    for name in names:
        inquiry = cdf.varinq(name)
        attributes = cdf.varattsget(name)
        data_type = field(inquiry, "Data_Type_Description", "Data_Type", default="")
        dimensions = list(field(inquiry, "Dim_Sizes", default=[]) or [])
        record_varying = bool(field(inquiry, "Rec_Vary", default=True))
        num_elements = int(field(inquiry, "Num_Elements", default=1) or 1)
        records = variable_record_count(cdf, name, record_varying)
        offset = int(physical.var_info[name]["offset_for_var"])

        if str(data_type).upper() in {"CDF_CHAR", "CDF_UCHAR", "51", "52"}:
            objects.append({
                "kind": "Table_Binary",
                "name": name,
                "offset": offset,
                "records": records,
                "record_length": num_elements,
                "pds_data_type": "ASCII_Date_Time_YMD",
                "description": attr(attributes, "CATDESC", attr(attributes, "FIELDNAM", name)),
            })
            continue

        axes = []
        if record_varying:
            if records != time_count:
                raise ValueError(
                    f"Record-varying variable has an inconsistent count: "
                    f"{name}={records}, expected={time_count}"
                )
            axes.append({"name": "time", "elements": time_count})
        for index, size in enumerate(dimensions, start=1):
            size = int(size)
            if size > 1:
                dependency = attr(attributes, f"DEPEND_{index}")
                axes.append({
                    "name": dependency or f"dimension_{index}",
                    "elements": size,
                })
        if not axes:
            axes.append({"name": "element", "elements": max(num_elements, 1)})

        try:
            type_key = int(data_type)
        except (TypeError, ValueError):
            type_key = str(data_type).upper()
        objects.append({
            "kind": "Array",
            "name": name,
            "offset": offset,
            "axes": axes,
            "pds_data_type": TYPE_MAP.get(type_key, str(data_type)),
            "unit": attr(attributes, "UNITS"),
            "description": attr(attributes, "CATDESC", attr(attributes, "FIELDNAM", name)),
            "fillval": attr(attributes, "FILLVAL"),
            "validmin": attr(attributes, "VALIDMIN"),
            "validmax": attr(attributes, "VALIDMAX"),
        })
    objects.sort(key=lambda item: item["offset"])

    date = yyyymmdd_from_name(cdf_path.name)
    stat = cdf_path.stat()
    creation = datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    logical_identifier = attr(globals_, "PDS_LOGICAL_IDENTIFIER").replace(
        "YYYYMMDD", date
    )
    if not logical_identifier:
        raise ValueError("CDF global attribute PDS_LOGICAL_IDENTIFIER is missing")

    context = {
        "logical_identifier": logical_identifier,
        "version_id": attr(globals_, "PDS_VERSION_IDENTIFIER", "1.0"),
        "title": attr(globals_, "TITLE", cdf_path.stem),
        "information_model_version": args.information_model_version,
        "publication_year": args.publication_year or int(creation[:4]),
        "description": args.description or attr(
            globals_, "Logical_source_description", attr(globals_, "TITLE")
        ),
        "authors": authors,
        "modification_date": datetime.now(timezone.utc).date().isoformat(),
        "modification_description": "Initial version",
        "start_time": start_time,
        "stop_time": stop_time,
        "purpose": args.purpose,
        "processing_level": profile["processing_level"],
        "domains": profile["domains"],
        "discipline_name": profile["discipline_name"],
        "facet1": profile["facet1"],
        "facet2": profile["facet2"],
        "investigation_name": args.investigation_name,
        "investigation_type": args.investigation_type,
        "investigation_lid": args.investigation_lid,
        "instrument_host_name": args.instrument_host_name,
        "instrument_host_lid": args.instrument_host_lid,
        "instrument_name": profile["instrument_name"],
        "instrument_lid": profile["instrument_lid"],
        "target_name": args.target_name,
        "target_type": args.target_type,
        "target_lid": args.target_lid,
        "mission_phase_name": profile["mission_phase_name"],
        "mission_phase_id": profile["mission_phase_id"],
        "sclk_start": attr(globals_, "PDS_SCLK_START_COUNT"),
        "sclk_stop": attr(globals_, "PDS_SCLK_STOP_COUNT"),
        "processing_software_title": attr(globals_, "GENERATION_SOFTWARE"),
        "processing_software_version": attr(globals_, "SOFTWARE_VERSION"),
        "source_file": attr(globals_, "SOURCE_FILE"),
        "internal_references": parse_internal_references(args.internal_reference),
        "cdf_file_name": cdf_path.name,
        "cdf_creation_time": creation,
        "cdf_size": stat.st_size,
        "cdf_md5": md5sum(cdf_path),
        "cdf_header_length": args.header_length,
        "cdf_parsing_standard_id": args.cdf_parsing_standard_id,
        "data_objects": objects,
    }

    # Preserve template indentation by disabling whitespace-stripping options.
    environment = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(default=True),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"{cdf_path.stem}.lblx"
    # Render first so repeated blank lines can be normalized safely.
    rendered = environment.get_template(
        template_path.name
    ).render(**context)

    # Keep at most one empty line between XML sections.
    rendered = re.sub(
        r"\n[ \t]*\n(?:[ \t]*\n)+",
        "\n\n",
        rendered,
    )

    output.write_text(
        rendered,
        encoding="utf-8",
        newline="\n",
    )
    print(f"Generated: {output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
