#!/usr/bin/env bash
#
# Create a PSA/PDS4 Collection label and inventory, then validate the label.
# Collection のラベルとインベントリを作り、PDS Validate でラベルを検証する。
#
# The label root is derived automatically from the archive root, bundle name,
# and collection name. Labels below mission-phase and annual subdirectories are
# discovered recursively by labels2collection.
#
# Usage / 使い方:
#   create_psa_collection_jinja_dynamic.sh [COLLECTION_NAME]
#
# Optional environment overrides:
#   ARCHIVE_ROOT, BUNDLE_NAME, COLLECTION_DIR, LABEL_DIR,
#   MISSION_TIMELINE_FILE, PYTHON, VALIDATE_ENABLED
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -- Archive and Collection settings -------------------------------------------
COLLECTION_NAME="${1:-data_calibrated_efd}"
BUNDLE_NAME="${BUNDLE_NAME:-bc_mmo_pwi}"

# Root containing bundle directories such as bc_mmo_pwi.
ARCHIVE_ROOT="${ARCHIVE_ROOT:-/var/www/html/data/chs/satellite/mmo/pds4}"
ARCHIVE_ROOT="${ARCHIVE_ROOT%/}"

# Derive the collection directory automatically. COLLECTION_DIR remains an
# environment override for testing or a non-standard deployment.
COLLECTION_DIR="${COLLECTION_DIR:-${ARCHIVE_ROOT}/${BUNDLE_NAME}/${COLLECTION_NAME}}"
COLLECTION_DIR="${COLLECTION_DIR%/}"

# The dynamic label-generation cron writes products below this science root:
#   <mission-phase-path>/<YYYY0101_YYYY1231>/*.lblx
LABEL_DIR="${LABEL_DIR:-${COLLECTION_DIR}/}"
LABEL_DIR="${LABEL_DIR%/}"

COLLECTION_LID="${COLLECTION_LID:-urn:jaxa:darts:${BUNDLE_NAME}:${COLLECTION_NAME}}"
OUTPUT_BASE="${OUTPUT_BASE:-$COLLECTION_NAME}"
PUBLICATION_YEAR="${PUBLICATION_YEAR:-2027}"
VERSION_ID="${VERSION_ID:-1.0}"

# Template and config files.
TEMPLATE_FILE="${TEMPLATE_FILE:-$SCRIPT_DIR/../templates/collection_template.xml.j2}"
MISSION_CONFIG="${MISSION_CONFIG:-$SCRIPT_DIR/../config/mission.json}"
DATASET_CONFIG="${DATASET_CONFIG:-$SCRIPT_DIR/../config/dataset_pwi_efd.json}"
MISSION_TIMELINE_FILE="${MISSION_TIMELINE_FILE:-$SCRIPT_DIR/../config/mission_timeline.json}"

# -- Reports and PDS Validate --------------------------------------------------
REPORT_DIR="${REPORT_DIR:-./pds_chk_log}"
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
VALIDATE_REPORT="${VALIDATE_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_validate_report.txt}"
SKIP_REPORT="${SKIP_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_skipped_missing_cdf.txt}"
VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"
VALIDATE_BIN="${VALIDATE_BIN:-$HOME/local/pds/validate/bin/validate}"
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"
PYTHON="${PYTHON:-python3}"

# -- Checks --------------------------------------------------------------------
case "$COLLECTION_NAME" in
  *[!A-Za-z0-9_-]*|'')
    echo "ERROR: invalid Collection name: $COLLECTION_NAME" >&2
    exit 1
    ;;
esac

"$PYTHON" -c 'import miopds_common' 2>/dev/null || {
  echo "ERROR: miopds_common is not installed for $PYTHON" >&2
  echo "       Activate the venv, or set PYTHON=/path/to/python" >&2
  exit 1
}

for required_file in \
  "$TEMPLATE_FILE" \
  "$MISSION_CONFIG" \
  "$DATASET_CONFIG" \
  "$MISSION_TIMELINE_FILE"
do
  [[ -r "$required_file" ]] || {
    echo "ERROR: required file is not readable: $required_file" >&2
    exit 1
  }
done

"$PYTHON" -m json.tool "$MISSION_TIMELINE_FILE" >/dev/null || {
  echo "ERROR: invalid mission timeline JSON: $MISSION_TIMELINE_FILE" >&2
  exit 1
}

[[ -d "$COLLECTION_DIR" ]] || {
  echo "ERROR: Collection directory was not found: $COLLECTION_DIR" >&2
  exit 1
}

[[ -d "$LABEL_DIR" ]] || {
  echo "ERROR: Dynamic science label root was not found: $LABEL_DIR" >&2
  exit 1
}

# Count labels recursively. The phase/year paths are not hard-coded here.
LABEL_COUNT=$(find "$LABEL_DIR" -type f -name '*.lblx' -print | wc -l)
if (( LABEL_COUNT == 0 )); then
  echo "ERROR: No LBLX files were found below: $LABEL_DIR" >&2
  exit 1
fi

mkdir -p "$REPORT_DIR"

echo "Collection name : $COLLECTION_NAME"
echo "Collection dir  : $COLLECTION_DIR"
echo "Label root      : $LABEL_DIR"
echo "Timeline JSON   : $MISSION_TIMELINE_FILE"
echo "LBLX files      : $LABEL_COUNT"

# Show the mission-phase directories that currently contain labels. This is
# diagnostic only; labels2collection receives the common science root.
echo "Label directories:"
find "$LABEL_DIR" -type f -name '*.lblx' -printf '%h\n' |
  sort -u |
  sed 's/^/  /'

# -- Generate ------------------------------------------------------------------
# labels2collection receives the common science root and recursively gathers
# labels from mission-phase and annual directories created by the label cron.
"$PYTHON" -m miopds_common labels2collection \
  "$LABEL_DIR" \
  "$COLLECTION_DIR" \
  "$TEMPLATE_FILE" \
  "$COLLECTION_LID" \
  "$OUTPUT_BASE" \
  --mission-config "$MISSION_CONFIG" \
  --dataset-config "$DATASET_CONFIG" \
  --publication-year "$PUBLICATION_YEAR" \
  --version-id "$VERSION_ID" \
  --skip-report "$SKIP_REPORT"

# -- Validate ------------------------------------------------------------------
if [[ "$VALIDATE_ENABLED" == "0" ]]; then
  echo "Validation skipped because VALIDATE_ENABLED=0"
  exit 0
fi

"$PYTHON" -m miopds_common validate \
  "$COLLECTION_DIR/${OUTPUT_BASE}.lblx" \
  --report "$VALIDATE_REPORT" \
  --validate-bin "$VALIDATE_BIN" \
  --catalog "$VALIDATE_CATALOG" \
  --label-extension "lblx"
