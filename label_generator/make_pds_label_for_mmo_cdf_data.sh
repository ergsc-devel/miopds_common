#!/usr/bin/env bash

# Generate a PDS4 LBLX label directly from a CDF file.
#
# Usage:
#   make_pds_label_for_mmo_cdf_data.sh \
#     CDF_FILE \
#     TEMPLATE_DIR \
#     TEMPLATE_NAME \
#     OUTPUT_DIR \
#     [RENDERER_OPTIONS...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# First argument: input CDF file.
CDF_FILE="${1:?Usage: $0 CDF_FILE TEMPLATE_DIR OUTPUT_DIR TEMPLATE_NAME [RENDERER_OPTIONS...]}"

# Second argument: directory containing the Jinja2 template.
TEMPLATE_DIR="${2:?ERROR: TEMPLATE_DIR is required.}"

# Third argument: Jinja2 template file name.
TEMPLATE_NAME="${3:?ERROR: TEMPLATE_NAME is required.}"
TEMPLATE_FILE="$TEMPLATE_DIR/$TEMPLATE_NAME"

# Forth argument: output directory for the generated LBLX file.
OUTPUT_DIR="${4:?ERROR: OUTPUT_DIR is required.}"

# Python renderer used to generate the PDS4 label.
RENDERER="${RENDERER:-$SCRIPT_DIR/render_mmo_cdf_label.py}"

# Directory containing the project-specific cdftool module.
CDFTOOL_DIR="${CDFTOOL_DIR:-/home/miosc/mio-sc/work_local/pds_pipeline/common/miopds_common/cdftool}"

export PYTHONPATH="$CDFTOOL_DIR:$(dirname "$CDFTOOL_DIR")${PYTHONPATH:+:$PYTHONPATH}"

[[ -f "$CDF_FILE" ]] || {
  echo "ERROR: CDF not found: $CDF_FILE" >&2
  exit 1
}

[[ -d "$TEMPLATE_DIR" ]] || {
  echo "ERROR: Template directory not found: $TEMPLATE_DIR" >&2
  exit 1
}

[[ -f "$TEMPLATE_FILE" ]] || {
  echo "ERROR: Template not found: $TEMPLATE_FILE" >&2
  exit 1
}

[[ -f "$RENDERER" ]] || {
  echo "ERROR: Renderer not found: $RENDERER" >&2
  exit 1
}

[[ -d "$CDFTOOL_DIR" ]] || {
  echo "ERROR: cdftool directory not found: $CDFTOOL_DIR" >&2
  exit 1
}

for module in jinja2 cdflib cdftool; do
  if ! python3 -c "import ${module}" >/dev/null 2>&1; then
    echo "ERROR: Python module could not be imported: $module" >&2
    echo "Python executable: $(command -v python3)" >&2
    echo "PYTHONPATH: $PYTHONPATH" >&2
    exit 1
  fi
done

mkdir -p "$OUTPUT_DIR"

echo "CDF file          : $CDF_FILE"
echo "Template directory: $TEMPLATE_DIR"
echo "Template name     : $TEMPLATE_NAME"
echo "Template file     : $TEMPLATE_FILE"
echo "Output directory  : $OUTPUT_DIR"
echo "Renderer          : $RENDERER"

# Arguments beginning with the fifth argument are passed to the Python renderer.
python3 "$RENDERER" \
  "$CDF_FILE" \
  "$TEMPLATE_FILE" \
  "$OUTPUT_DIR" \
  "${@:5}"

CDF_BASE="$(basename "$CDF_FILE")"
CDF_STEM="${CDF_BASE%.[cC][dD][fF]}"
GENERATED_LABEL="$OUTPUT_DIR/$CDF_STEM.lblx"

[[ -f "$GENERATED_LABEL" ]] || {
  echo "ERROR: Generated PDS label was not found: $GENERATED_LABEL" >&2
  exit 1
}

echo "PDS4 label generated successfully."
echo "Generated label: $GENERATED_LABEL"
