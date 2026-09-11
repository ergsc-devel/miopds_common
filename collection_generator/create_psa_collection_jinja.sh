#!/usr/bin/env bash

# Undefined variables, command failures, and failures in the middle of a pipeline are treated as errors.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

COLLECTION_NAME="${1:-data_calibrated_efd}"
COLLECTION_DIR="${2:-bc_mmo_pwi/$COLLECTION_NAME}"
COLLECTION_DIR="${COLLECTION_DIR%/}"

BUNDLE_NAME="${BUNDLE_NAME:-bc_mmo_pwi}"
LABEL_DIR="${LABEL_DIR:-$COLLECTION_DIR/science}"
COLLECTION_LID="${COLLECTION_LID:-urn:jaxa:darts:$BUNDLE_NAME:$COLLECTION_NAME}"
OUTPUT_BASE="${OUTPUT_BASE:-$COLLECTION_NAME}"

TEMPLATE_FILE="${TEMPLATE_FILE:-$SCRIPT_DIR/collection_template.xml.j2}"
RENDERER_FILE="${RENDERER_FILE:-$SCRIPT_DIR/render_psa_collection.py}"

VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"
VALIDATE_BIN="${VALIDATE_BIN:-$HOME/validate-4.0.8/bin/validate}"
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"

# This is the save location for check reports shared by all generators.
REPORT_DIR="${REPORT_DIR:-/home/miosc/mio-sc/work_local/tmp/pds_chk_log}"
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
VALIDATE_REPORT="${VALIDATE_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_validate_report.txt}"

case "$COLLECTION_NAME" in
  *[!A-Za-z0-9_-]*|'')
    echo "ERROR: invalid Collection name: $COLLECTION_NAME" >&2
    exit 1
    ;;
esac

[[ -d "$COLLECTION_DIR" ]] || { echo "ERROR: Collection directory not found: $COLLECTION_DIR" >&2; exit 1; }
[[ -d "$LABEL_DIR" ]] || { echo "ERROR: label directory not found: $LABEL_DIR" >&2; exit 1; }
[[ -f "$TEMPLATE_FILE" ]] || { echo "ERROR: template file not found: $TEMPLATE_FILE" >&2; exit 1; }
[[ -f "$RENDERER_FILE" ]] || { echo "ERROR: renderer not found: $RENDERER_FILE" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 was not found." >&2; exit 1; }
python3 -c 'import jinja2' >/dev/null 2>&1 || { echo "ERROR: Jinja2 is required." >&2; exit 1; }

# Create the report directory before the generation process.
mkdir -p "$REPORT_DIR"
mkdir -p "$(dirname "$VALIDATE_REPORT")"

echo "Collection name : $COLLECTION_NAME"
echo "Collection dir  : $COLLECTION_DIR"
echo "Label dir       : $LABEL_DIR"
echo "Bundle name     : $BUNDLE_NAME"
echo "Collection LID  : $COLLECTION_LID"
echo "Output base     : $OUTPUT_BASE"
echo "Report dir      : $REPORT_DIR"
echo "Report file     : $VALIDATE_REPORT"

python3 "$RENDERER_FILE" \
  "$LABEL_DIR" \
  "$COLLECTION_DIR" \
  "$TEMPLATE_FILE" \
  "$COLLECTION_LID" \
  "$OUTPUT_BASE"

COLLECTION_XML="$COLLECTION_DIR/${OUTPUT_BASE}.xml"
COLLECTION_CSV="$COLLECTION_DIR/${OUTPUT_BASE}.csv"
[[ -f "$COLLECTION_XML" ]] || { echo "ERROR: generated Collection XML not found: $COLLECTION_XML" >&2; exit 1; }
[[ -f "$COLLECTION_CSV" ]] || { echo "ERROR: generated Collection CSV not found: $COLLECTION_CSV" >&2; exit 1; }

if [[ "$VALIDATE_ENABLED" == "0" ]]; then
  echo "Validation skipped because VALIDATE_ENABLED=0"
  exit 0
fi

[[ -x "$VALIDATE_BIN" ]] || { echo "ERROR: validate executable not found or not executable: $VALIDATE_BIN" >&2; exit 1; }

VALIDATE_ARGS=(--target "$COLLECTION_XML")

if [[ -n "$VALIDATE_CATALOG" ]]; then
  if [[ -f "$VALIDATE_CATALOG" ]]; then
    VALIDATE_ARGS+=(--catalog "$VALIDATE_CATALOG")
    echo "Using XML catalog: $VALIDATE_CATALOG"
  else
    echo "WARNING: XML catalog was not found: $VALIDATE_CATALOG" >&2
    echo "WARNING: Validation will continue without --catalog." >&2
  fi
else
  echo "XML catalog is not specified."
  echo "Validation will continue without --catalog."
fi

echo "Validating Collection label: $COLLECTION_XML"
echo "Validation report: $VALIDATE_REPORT"
printf 'Validation command:'
printf ' %q' "$VALIDATE_BIN" "${VALIDATE_ARGS[@]}"
printf '\n'

"$VALIDATE_BIN" "${VALIDATE_ARGS[@]}" 2>&1 | tee "$VALIDATE_REPORT"

echo "Collection label validation passed."
echo "Validation report saved to: $VALIDATE_REPORT"
