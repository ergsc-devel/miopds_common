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

# Build the full path to the Jinja2 template file.
TEMPLATE_FILE="$TEMPLATE_DIR/$TEMPLATE_NAME"

# Forth argument: output directory for the generated LBLX file.
OUTPUT_DIR="${4:?ERROR: OUTPUT_DIR is required.}"

# Python renderer that reads the CDF file and generates the PDS4 label.
# Set the RENDERER environment variable to use another Python script.
RENDERER="${RENDERER:-$SCRIPT_DIR/render_mmo_cdf_label.py}"

# Directory containing the project-specific cdftool Python module.
# Set the CDFTOOL_DIR environment variable to use another location.
CDFTOOL_DIR="${CDFTOOL_DIR:-/home/miosc/mio-sc/work_local/pds_pipeline/common/miopds_common/cdftool}"

# Add both the cdftool directory and its parent directory to PYTHONPATH.
# This supports either a cdftool.py module inside CDFTOOL_DIR or a cdftool
# package imported from its parent directory. Preserve an existing PYTHONPATH.
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
RENDER_OUTPUT="$(python3 "$RENDERER" \
  "$CDF_FILE" \
  "$TEMPLATE_FILE" \
  "$OUTPUT_DIR" \
  "${@:5}")"

printf '%s\n' "$RENDER_OUTPUT"

# The renderer prints the final label path in the form "Generated   : PATH".
GENERATED_LABEL="$(printf '%s\n' "$RENDER_OUTPUT" | sed -n 's/^Generated[[:space:]]*:[[:space:]]*//p' | tail -n 1)"

[[ -n "$GENERATED_LABEL" && -f "$GENERATED_LABEL" ]] || {
  echo "ERROR: Generated PDS label path could not be confirmed." >&2
  exit 1
}

echo "PDS4 label generated successfully."
echo "Generated label: $GENERATED_LABEL"
