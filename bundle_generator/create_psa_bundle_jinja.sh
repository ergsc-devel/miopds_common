#!/usr/bin/env bash

# Undefined variables, command failures, and failures in the middle of a pipeline are treated as errors.
set -euo pipefail

# It references the renderer and template located in the same directory as this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The first argument is the Bundle directory. If not specified, `bc_mmo_pwi` is used.
BUNDLE_DIR="${1:-bc_mmo_pwi}"
BUNDLE_DIR="${BUNDLE_DIR%/}"

# The end of the bundle directory path is used as the bundle name.
BUNDLE_NAME="${BUNDLE_NAME:-${BUNDLE_DIR##*/}}"

# This is the value set for the Bundle label. It can be overridden using an environment variable.
BUNDLE_LID="${BUNDLE_LID:-urn:jaxa:darts:$BUNDLE_NAME}"
BUNDLE_VID="${BUNDLE_VID:-1.0}"
PUBLICATION_YEAR="${PUBLICATION_YEAR:-2027}"
AUTHOR_LIST="${AUTHOR_LIST:-Kasaba, Y., Kojima, H., Moncuquet, M. et al.}"
MODIFICATION_DATE="${MODIFICATION_DATE:-$(date -u +%F)}"

OUTPUT_FILE="${OUTPUT_FILE:-bundle.xml}"
TEMPLATE_FILE="${TEMPLATE_FILE:-$SCRIPT_DIR/bundle_template.xml.j2}"
RENDERER_FILE="${RENDERER_FILE:-$SCRIPT_DIR/render_psa_bundle.py}"

# These are the PDS Validate settings.
VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"
VALIDATE_BIN="${VALIDATE_BIN:-$HOME/validate-4.0.8/bin/validate}"
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"
BUNDLE_LABEL_EXTENSION="${BUNDLE_LABEL_EXTENSION:-}"

# This is the common report storage location for Bundles, Collections, Documents, and LBLX.
REPORT_DIR="${REPORT_DIR:-/home/miosc/mio-sc/work_local/tmp/pds_chk_log}"
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
VALIDATE_REPORT="${VALIDATE_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_${BUNDLE_NAME}_bundle_validate_report.txt}"

[[ -d "$BUNDLE_DIR" ]] || { echo "ERROR: Bundle directory not found: $BUNDLE_DIR" >&2; exit 1; }
[[ -f "$TEMPLATE_FILE" ]] || { echo "ERROR: template file not found: $TEMPLATE_FILE" >&2; exit 1; }
[[ -f "$RENDERER_FILE" ]] || { echo "ERROR: renderer not found: $RENDERER_FILE" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 was not found." >&2; exit 1; }
python3 -c 'import jinja2' >/dev/null 2>&1 || { echo "ERROR: Jinja2 is required." >&2; exit 1; }

# If the destination does not exist, it will be created automatically.
mkdir -p "$REPORT_DIR"
mkdir -p "$(dirname "$VALIDATE_REPORT")"

echo "Bundle name     : $BUNDLE_NAME"
echo "Bundle dir      : $BUNDLE_DIR"
echo "Bundle LID      : $BUNDLE_LID"
echo "Bundle VID      : $BUNDLE_VID"
echo "Output file     : $OUTPUT_FILE"
echo "Report dir      : $REPORT_DIR"
echo "Report file     : $VALIDATE_REPORT"

# Reads the Collection label and generates Bundle XML from the Jinja2 template.
python3 "$RENDERER_FILE" \
  "$BUNDLE_DIR" \
  --template "$TEMPLATE_FILE" \
  --bundle-lid "$BUNDLE_LID" \
  --bundle-vid "$BUNDLE_VID" \
  --publication-year "$PUBLICATION_YEAR" \
  --author-list "$AUTHOR_LIST" \
  --modification-date "$MODIFICATION_DATE" \
  --output "$OUTPUT_FILE"

BUNDLE_XML="$BUNDLE_DIR/$OUTPUT_FILE"
[[ -f "$BUNDLE_XML" ]] || { echo "ERROR: generated Bundle XML not found: $BUNDLE_XML" >&2; exit 1; }

if [[ "$VALIDATE_ENABLED" == "0" ]]; then
  echo "Validation skipped because VALIDATE_ENABLED=0"
  exit 0
fi

[[ -x "$VALIDATE_BIN" ]] || { echo "ERROR: validate executable not found or not executable: $VALIDATE_BIN" >&2; exit 1; }

VALIDATE_ARGS=(
  --rule pds4.bundle
  --target "$BUNDLE_DIR"
)

if [[ -n "$BUNDLE_LABEL_EXTENSION" ]]; then
  VALIDATE_ARGS+=(--label-extension "$BUNDLE_LABEL_EXTENSION")
fi

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

echo "Validating Bundle: $BUNDLE_DIR"
echo "Validation report: $VALIDATE_REPORT"
printf 'Validation command:'
printf ' %q' "$VALIDATE_BIN" "${VALIDATE_ARGS[@]}"
printf '\n'

"$VALIDATE_BIN" "${VALIDATE_ARGS[@]}" 2>&1 | tee "$VALIDATE_REPORT"

echo "Bundle validation passed."
echo "Validation report saved to: $VALIDATE_REPORT"
