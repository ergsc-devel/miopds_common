#!/usr/bin/env bash
# A simple script for creating PDS4 labels from CDF files in a specified directory
#
# Usage:
#   ./make_pds_labels_simple.sh CDF_DIRECTORY LABEL_OUTPUT_DIRECTORY

set -u

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 CDF_DIRECTORY LABEL_OUTPUT_DIRECTORY" >&2
    exit 1
fi

CDF_DIR="$1"
OUTPUT_DIR="$2"

# Fixed settings depending on the usage environment
source ~/work_local/.3_13/bin/activate
LABEL_SCRIPT="${HOME}/work_local/pds_pipeline/common/examples/scripts/make_pds_label_for_mmo_cdf_data.sh"
TEMPLATE_DIR="${HOME}/work_local/pds_pipeline/common/examples/templates"
TEMPLATE_NAME="mmo_cdf_label_template_multi_dataset.xml.j2"

# Settings referenced by the label generation script
export MISSION_CONFIG="${HOME}/work_local/pds_pipeline/common/examples/config/mission.json"
export DATASET_CONFIG="${HOME}/work_local/data_pipeline/mmo/pwi/efd/pds/config/dataset_pwi_efd.json"
export MISSION_TIMELINE="${HOME}/work_local/pds_pipeline/common/examples/config/mission_timeline.json"
export PYTHON="${PYTHON:-python3}"

if [[ ! -d "$CDF_DIR" ]]; then
    echo "ERROR: CDF directory does not exist: $CDF_DIR" >&2
    exit 1
fi

if [[ ! -x "$LABEL_SCRIPT" ]]; then
    echo "ERROR: Label script is not executable: $LABEL_SCRIPT" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

found=0

while IFS= read -r -d '' cdf_file; do
    found=1
    echo "Processing: $cdf_file"

    if "$LABEL_SCRIPT" \
        "$cdf_file" \
        "$TEMPLATE_DIR" \
        "$TEMPLATE_NAME" \
        "$OUTPUT_DIR"
    then
        echo "Completed : $cdf_file"
    else
        echo "ERROR: Label generation failed: $cdf_file" >&2
    fi
done < <(find "$CDF_DIR" -type f -name '*.cdf' -print0 | sort -z)

if [[ $found -eq 0 ]]; then
    echo "No CDF files were found under: $CDF_DIR" >&2
    exit 1
fi

