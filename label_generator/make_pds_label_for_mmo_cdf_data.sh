#!/usr/bin/env bash

# Generate a PDS4 label (.lblx) directly from an actual CDF file.
# The Python renderer reads the global attributes, variable attributes,
# dimensions, record counts, and physical offsets stored in the CDF file.
# This script does not use a JSON definition file.
#
# Usage:
#   ./make_pds_label_for_mmo_cdf_data.sh \
#     CDF_FILE \
#     [TEMPLATE_DIR] \
#     [OUTPUT_DIR] \
#     [RENDERER_OPTIONS...]
#
# Example:
#   ./make_pds_label_for_mmo_cdf_data.sh \
#     /path/to/product.cdf \
#     /home/miosc/mio-sc/work_local/data_pipeline/mmo/pwi/efd/pds/template \
#     /path/to/output \
#     --time-variable strtime \
#     --epoch-variable epoch

# Enable strict shell behavior.
# -e: Exit when a command fails.
# -u: Exit when an undefined variable is referenced.
# -o pipefail: Treat a failure in any part of a pipeline as a pipeline failure.
set -euo pipefail

# Obtain the absolute path of the directory containing this shell script.
# This directory is used as the default location of the Python renderer.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The first argument is the CDF file to process.
# If it is omitted, print the usage message and exit.
CDF_FILE="${1:?Usage: $0 CDF_FILE [TEMPLATE_DIR] [OUTPUT_DIR] [RENDERER_OPTIONS...]}"

# The second argument is the directory containing the Jinja2 label template.
# If it is omitted, use the default PWI EFD template directory.
TEMPLATE_DIR="${2:-/home/miosc/mio-sc/work_local/data_pipeline/mmo/pwi/efd/pds/template}"

# The third argument is the output directory for the generated LBLX file.
# If it is omitted, use the directory containing the input CDF file.
# The realpath -m option normalizes the path even when some path components
# do not yet exist.
OUTPUT_DIR="${3:-$(dirname "$(realpath -m "$CDF_FILE")")}" 

# Name of the Jinja2 template file.
# Set the TEMPLATE_NAME environment variable to use another template.
TEMPLATE_NAME="${TEMPLATE_NAME:-pwi_efd_l2_l_spec_label_template.xml.j2}"

# Build the full path to the Jinja2 template file.
TEMPLATE_FILE="$TEMPLATE_DIR/$TEMPLATE_NAME"

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

# Verify that the input CDF file exists.
[[ -f "$CDF_FILE" ]] || {
  echo "ERROR: CDF not found: $CDF_FILE" >&2
  exit 1
}

# Verify that the Jinja2 template exists.
[[ -f "$TEMPLATE_FILE" ]] || {
  echo "ERROR: template not found: $TEMPLATE_FILE" >&2
  exit 1
}

# Verify that the Python renderer exists.
[[ -f "$RENDERER" ]] || {
  echo "ERROR: renderer not found: $RENDERER" >&2
  exit 1
}

# Verify that the cdftool directory exists.
[[ -d "$CDFTOOL_DIR" ]] || {
  echo "ERROR: cdftool directory not found: $CDFTOOL_DIR" >&2
  exit 1
}

# Check each required Python module separately so that the missing module
# can be identified clearly.
for module in jinja2 cdflib cdftool; do
  if ! python3 -c "import ${module}" >/dev/null 2>&1; then
    echo "ERROR: Python module could not be imported: $module" >&2
    echo "Python executable: $(command -v python3)" >&2
    echo "PYTHONPATH: $PYTHONPATH" >&2
    exit 1
  fi
done

# Create the output directory if it does not exist.
mkdir -p "$OUTPUT_DIR"

# Display the configuration used for this execution.
echo "CDF file          : $CDF_FILE"
echo "Template file     : $TEMPLATE_FILE"
echo "Output directory  : $OUTPUT_DIR"
echo "Renderer          : $RENDERER"
echo "cdftool directory : $CDFTOOL_DIR"

# Run the Python renderer.
#
# The first three arguments passed to the renderer are:
#   1. Input CDF file
#   2. Jinja2 template file
#   3. LBLX output directory
#
# Any shell arguments beginning with the fourth argument are passed directly
# to the Python renderer. Examples include --time-variable,
# --epoch-variable, and --publication-year.
python3 "$RENDERER" \
  "$CDF_FILE" \
  "$TEMPLATE_FILE" \
  "$OUTPUT_DIR" \
  "${@:4}"

# Derive the expected LBLX file name from the input CDF file name.
# The pattern supports both lowercase .cdf and uppercase .CDF extensions.
CDF_BASE="$(basename "$CDF_FILE")"
CDF_STEM="${CDF_BASE%.[cC][dD][fF]}"
GENERATED_LABEL="$OUTPUT_DIR/$CDF_STEM.lblx"

# Verify that the expected LBLX file was generated successfully.
[[ -f "$GENERATED_LABEL" ]] || {
  echo "ERROR: Generated PDS label was not found: $GENERATED_LABEL" >&2
  exit 1
}

# Display a success message and the generated label path.
echo "PDS4 label generated successfully."
echo "Generated label: $GENERATED_LABEL"
