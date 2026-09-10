#!/usr/bin/env python3
"""Generate a PDS4 LBLX file from an actual CDF file and a Jinja2 template."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import cdflib
import cdftool
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


# Map CDF data types to the corresponding PDS4 data type names.
# Both numeric CDF type identifiers and textual CDF type names are supported.
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


def scalar(value, default="") -> str:
    """Convert an attribute or array value into a single normalized string.

    CDF libraries may return scalar values, lists, tuples, NumPy arrays,
    or byte strings. For array-like values, use the first element.
    """
    if value is None:
        return str(default)

    # Flatten NumPy-like arrays and select the first value.
    if hasattr(value, "reshape") and hasattr(value, "size"):
        if int(value.size) == 0:
            return str(default)
        value = value.reshape(-1)[0]

    # Select the first value from ordinary Python sequences.
    elif isinstance(value, (list, tuple)):
        if not value:
            return str(default)
        value = value[0]

    # Decode byte strings returned by CDF readers.
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")

    text = str(value).strip()
    return text if text else str(default)


def attr(attrs: dict, name: str, default="") -> str:
    """Return a CDF attribute value using a case-insensitive key lookup."""
    for key, value in attrs.items():
        if key.lower() == name.lower():
            return scalar(value, default)
    return str(default)


def md5sum(path: Path) -> str:
    """Calculate the MD5 checksum of a file without loading it all at once."""
    digest = hashlib.md5()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def yyyymmdd_from_name(name: str) -> str:
    """Extract an eight-digit date surrounded by separators from a file name."""
    match = re.search(r"_(\d{8})(?:_|\.)", name)

    if not match:
        raise ValueError(f"Could not extract YYYYMMDD from CDF file name: {name}")

    return match.group(1)


def time_bounds(cdf, time_variable: str) -> tuple[str, str]:
    """Return the first and last values of a CDF time-string variable."""
    values = cdf.varget(time_variable)

    # Handle NumPy-like arrays returned by cdflib.
    if hasattr(values, "reshape") and hasattr(values, "size"):
        if int(values.size) == 0:
            raise ValueError(f"Time variable is empty: {time_variable}")

        values = values.reshape(-1)
        return scalar(values[0]), scalar(values[-1])

    # Handle Python lists and tuples.
    if isinstance(values, (list, tuple)):
        if not values:
            raise ValueError(f"Time variable is empty: {time_variable}")

        return scalar(values[0]), scalar(values[-1])

    # If a scalar is returned, use the same value for both bounds.
    value = scalar(values)
    return value, value


def field(info, *names, default=None):
    """Read a field from either a dictionary or an object returned by cdflib."""
    for name in names:
        if isinstance(info, dict) and name in info:
            return info[name]

        if hasattr(info, name):
            return getattr(info, name)

    return default


def main() -> None:
    """Read the CDF, build the template context, and generate the LBLX file."""
    parser = argparse.ArgumentParser(
        description="Generate a PDS4 LBLX file directly from a CDF file."
    )

    # Required positional arguments.
    parser.add_argument("cdf", type=Path, help="Input CDF file")
    parser.add_argument("xml_template", type=Path, help="Jinja2 PDS4 label template")
    parser.add_argument("output_dir", type=Path, help="Output directory for the LBLX file")

    # Optional settings used to interpret the CDF and populate the label.
    parser.add_argument("--time-variable", default="strtime")
    parser.add_argument("--epoch-variable", default="epoch")
    parser.add_argument("--information-model-version", default="1.22.0.0")
    parser.add_argument("--header-length", type=int, default=404)
    parser.add_argument("--publication-year", type=int)
    parser.add_argument("--description")
    parser.add_argument(
        "--instrument-host-lid",
        default="urn:jaxa:darts:context:instrument_host:spacecraft.mmo",
    )
    parser.add_argument(
        "--instrument-lid",
        default="urn:jaxa:darts:context:instrument:mmo.pwi",
    )

    args = parser.parse_args()

    # Normalize the input paths and verify that the required files exist.
    cdf_path = args.cdf.resolve()
    template_path = args.xml_template.resolve()

    if not cdf_path.is_file():
        raise FileNotFoundError(cdf_path)

    if not template_path.is_file():
        raise FileNotFoundError(template_path)

    # Open the CDF and retrieve its global metadata, variable list,
    # and physical variable information such as offsets and record counts.
    cdf = cdflib.CDF(str(cdf_path))
    globals_ = cdf.globalattsget()
    cdf_info = cdf.cdf_info()
    physical = cdftool.cdfinfo(str(cdf_path))
    variable_names = list(cdf_info.zVariables)

    # The selected string-time variable is required to define the observation
    # start and stop times in Time_Coordinates.
    if args.time_variable not in variable_names:
        raise ValueError(f"Time variable was not found: {args.time_variable}")

    start_time, stop_time = time_bounds(cdf, args.time_variable)

    # Use the epoch variable record count as the common time-axis length.
    # The max_rec value is zero-based, so add one to obtain the record count.
    time_count = None
    if args.epoch_variable in variable_names:
        time_count = int(
            physical.var_info[args.epoch_variable]["max_rec"]
        ) + 1

    # Build the PDS4 data object definitions from all CDF zVariables.
    objects = []

    for name in variable_names:
        # Read the CDF variable definition, variable attributes,
        # record count, and physical byte offset.
        inquiry = cdf.varinq(name)
        vatts = cdf.varattsget(name)
        data_type = field(
            inquiry,
            "Data_Type_Description",
            "Data_Type",
            default="",
        )
        dimensions = list(
            field(inquiry, "Dim_Sizes", default=[]) or []
        )
        rec_vary = bool(field(inquiry, "Rec_Vary", default=True))
        num_elements = int(
            field(inquiry, "Num_Elements", default=1) or 1
        )
        records = int(physical.var_info[name]["max_rec"]) + 1
        offset = int(physical.var_info[name]["offset_for_var"])

        # Represent CDF character variables as PDS4 binary tables.
        if str(data_type).upper() in {
            "CDF_CHAR",
            "CDF_UCHAR",
            "51",
            "52",
        }:
            objects.append(
                {
                    "kind": "Table_Binary",
                    "name": name,
                    "offset": offset,
                    "records": records,
                    "record_length": num_elements,
                    "description": attr(
                        vatts,
                        "CATDESC",
                        attr(vatts, "FIELDNAM", name),
                    ),
                }
            )
            continue

        # Build the axis definitions for numeric CDF variables.
        axes = []

        # A record-varying variable receives a time axis.
        if rec_vary:
            axes.append(
                {
                    "name": "time",
                    "elements": time_count or records,
                }
            )

        # Add the non-record dimensions as additional PDS4 axes.
        for index, size in enumerate(dimensions, start=1):
            size = int(size)

            # A dimension of one does not need a separate axis here.
            if size <= 1:
                continue

            # Use the corresponding DEPEND_n attribute as the axis name
            # when it is available. Otherwise, use a generic name.
            dependency = attr(vatts, f"DEPEND_{index}")
            axes.append(
                {
                    "name": dependency or f"dimension_{index}",
                    "elements": size,
                }
            )

        # Provide a fallback axis for non-varying scalar variables.
        if not axes:
            axes.append(
                {
                    "name": "element",
                    "elements": max(num_elements, 1),
                }
            )

        # Normalize the data type so it can be looked up in TYPE_MAP.
        try:
            type_key = int(data_type)
        except (TypeError, ValueError):
            type_key = str(data_type).upper()

        # Add a PDS4 Array definition using CDF variable attributes.
        objects.append(
            {
                "kind": "Array",
                "name": name,
                "offset": offset,
                "axes": axes,
                "pds_data_type": TYPE_MAP.get(
                    type_key,
                    str(data_type),
                ),
                "unit": attr(vatts, "UNITS"),
                "description": attr(
                    vatts,
                    "CATDESC",
                    attr(vatts, "FIELDNAM", name),
                ),
                "fillval": attr(vatts, "FILLVAL"),
                "validmin": attr(vatts, "VALIDMIN"),
                "validmax": attr(vatts, "VALIDMAX"),
            }
        )

    # Sort data objects by physical byte offset before rendering.
    # This avoids placing later objects before earlier objects in the label.
    objects.sort(key=lambda item: item["offset"])

    # Extract the observation date from the CDF file name.
    date = yyyymmdd_from_name(cdf_path.name)

    # Obtain the physical file metadata used by the PDS4 File class.
    stat = cdf_path.stat()
    creation = datetime.fromtimestamp(
        stat.st_mtime,
        timezone.utc,
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Read and finalize the product logical identifier.
    logical_identifier = attr(globals_, "PDS_LOGICAL_IDENTIFIER")
    logical_identifier = logical_identifier.replace("YYYYMMDD", date)

    if not logical_identifier:
        raise ValueError(
            "CDF global attribute PDS_LOGICAL_IDENTIFIER is missing"
        )

    # Build the context passed to the Jinja2 label template.
    context = {
        "logical_identifier": logical_identifier,
        "version_id": attr(
            globals_,
            "PDS_VERSION_IDENTIFIER",
            "1.0",
        ),
        "title": attr(globals_, "TITLE", cdf_path.stem),
        "yyyymmdd": date,
        "information_model_version": args.information_model_version,
        "publication_year": args.publication_year or int(creation[:4]),
        "modification_date": datetime.now(timezone.utc).date().isoformat(),
        "modification_description": "Initial version",
        "description": args.description
        or attr(
            globals_,
            "Logical_source_description",
            attr(globals_, "TITLE"),
        ),
        "start_time": start_time,
        "stop_time": stop_time,
        "instrument_host_lid": args.instrument_host_lid,
        "instrument_lid": args.instrument_lid,
        "sclk_start": attr(globals_, "PDS_SCLK_START_COUNT"),
        "sclk_stop": attr(globals_, "PDS_SCLK_STOP_COUNT"),
        "processing_software_title": attr(
            globals_,
            "GENERATION_SOFTWARE",
        ),
        "processing_software_version": attr(
            globals_,
            "SOFTWARE_VERSION",
        ),
        "source_file": attr(globals_, "SOURCE_FILE"),
        "cdf_file_name": cdf_path.name,
        "cdf_creation_time": creation,
        "cdf_size": stat.st_size,
        "cdf_md5": md5sum(cdf_path),
        "cdf_header_length": args.header_length,
        "data_objects": objects,
    }

    # Configure Jinja2 with strict undefined-variable handling.
    # Autoescaping is enabled to protect XML text values.
    environment = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(default=True),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Create the output directory and render the final LBLX file.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"{cdf_path.stem}.lblx"
    output.write_text(
        environment.get_template(template_path.name).render(**context),
        encoding="utf-8",
        newline="\n",
    )

    # Display a concise generation summary.
    print(f"Start time  : {start_time}")
    print(f"Stop time   : {stop_time}")
    print(f"Data objects: {len(objects)}")
    print(f"Generated   : {output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Print a clear error message and return a nonzero exit status.
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
