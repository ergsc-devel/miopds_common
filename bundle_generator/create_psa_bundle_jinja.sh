#!/usr/bin/env bash
#
# Create and validate a PSA/PDS4 Bundle label from the Collection labels found
# below the Bundle directory.
#
# Usage:
#   create_psa_bundle_jinja_modified.sh [BUNDLE_DIR]
#
# Example:
#   create_psa_bundle_jinja_modified.sh bc_mmo_pwi
#
# Default output:
#   bc_mmo_pwi/bundle_bc_mmo_pwi.xml
#
set -euo pipefail

# This script expects the renderer and Jinja2 template in the same directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The first argument is the Bundle directory. If omitted, use bc_mmo_pwi.
BUNDLE_DIR="${1:-bc_mmo_pwi}"
BUNDLE_DIR="${BUNDLE_DIR%/}"

# Use the final path component as the Bundle name.
BUNDLE_NAME="${BUNDLE_NAME:-${BUNDLE_DIR##*/}}"

# Values used in the Bundle label. Environment variables may override them.
BUNDLE_LID="${BUNDLE_LID:-urn:jaxa:darts:${BUNDLE_NAME}}"
BUNDLE_VID="${BUNDLE_VID:-1.0}"
PUBLICATION_YEAR="${PUBLICATION_YEAR:-2027}"
MODIFICATION_DATE="${MODIFICATION_DATE:-$(date -u +%F)}"

# Generate bundle_<Bundle directory name>.xml unless OUTPUT_FILE is specified.
# Example: BUNDLE_DIR=bc_mmo_pwi -> bundle_bc_mmo_pwi.xml
OUTPUT_FILE="${OUTPUT_FILE:-bundle_${BUNDLE_NAME}.xml}"

TEMPLATE_FILE="${TEMPLATE_FILE:-${SCRIPT_DIR}/bundle_template.xml.j2}"
RENDERER_FILE="${RENDERER_FILE:-${SCRIPT_DIR}/render_psa_bundle.py}"

# PDS Validate settings.
VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"
VALIDATE_BIN="${VALIDATE_BIN:-${HOME}/validate-4.0.8/bin/validate}"
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"
BUNDLE_LABEL_EXTENSION="${BUNDLE_LABEL_EXTENSION:-}"

# Common report location for Bundles, Collections, Documents, and LBLX files.
REPORT_DIR="${REPORT_DIR:-/home/miosc/mio-sc/work_local/tmp/pds_chk_log}"
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
VALIDATE_REPORT="${VALIDATE_REPORT:-${REPORT_DIR}/${REPORT_TIMESTAMP}_${BUNDLE_NAME}_bundle_validate_report.txt}"

# Verify required inputs and commands.
[[ -d "${BUNDLE_DIR}" ]] || {
    echo "ERROR: Bundle directory not found: ${BUNDLE_DIR}" >&2
    exit 1
}

[[ -f "${TEMPLATE_FILE}" ]] || {
    echo "ERROR: Template file not found: ${TEMPLATE_FILE}" >&2
    exit 1
}

[[ -f "${RENDERER_FILE}" ]] || {
    echo "ERROR: Renderer not found: ${RENDERER_FILE}" >&2
    exit 1
}

command -v python3 >/dev/null 2>&1 || {
    echo "ERROR: python3 was not found." >&2
    exit 1
}

python3 -c 'import jinja2' >/dev/null 2>&1 || {
    echo "ERROR: Jinja2 is required." >&2
    exit 1
}

# Read list_author values from existing XML/LBLX labels in the Bundle.
# For backward compatibility, author_list is accepted as an input element too,
# but the value is passed to the renderer using the new --list-author option.
# Bundle labels are excluded to avoid reading values from a previous output.
LIST_AUTHOR="$(python3 - "${BUNDLE_DIR}" <<'PY'
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

bundle_dir = Path(sys.argv[1])
pds_namespace = "http://pds.nasa.gov/pds4/pds/v1"
root_tag = f"{{{pds_namespace}}}Product_Bundle"
author_tags = {
    f"{{{pds_namespace}}}list_author",
    f"{{{pds_namespace}}}author_list",
    "list_author",
    "author_list",
}

authors = []
seen = set()

for pattern in ("*.xml", "*.lblx"):
    for label_path in sorted(bundle_dir.rglob(pattern)):
        try:
            root = ET.parse(label_path).getroot()
        except (ET.ParseError, OSError):
            # Non-XML or incomplete files are ignored here; PDS Validate will
            # report malformed archive labels during the validation stage.
            continue

        # Do not use an existing Bundle label as the source of list_author.
        if root.tag == root_tag:
            continue

        for element in root.iter():
            if element.tag not in author_tags or not element.text:
                continue

            value = " ".join(element.text.split())
            if value and value not in seen:
                seen.add(value)
                authors.append(value)

print(", ".join(authors))
PY
)"

if [[ -z "${LIST_AUTHOR}" ]]; then
    echo "ERROR: list_author/author_list was not found in any XML or LBLX label under: ${BUNDLE_DIR}" >&2
    exit 1
fi

# Create report directories before rendering and validation.
mkdir -p "${REPORT_DIR}"
mkdir -p "$(dirname "${VALIDATE_REPORT}")"

echo "Bundle name     : ${BUNDLE_NAME}"
echo "Bundle dir      : ${BUNDLE_DIR}"
echo "Bundle LID      : ${BUNDLE_LID}"
echo "Bundle VID      : ${BUNDLE_VID}"
echo "List author     : ${LIST_AUTHOR}"
echo "Output file     : ${OUTPUT_FILE}"
echo "Report dir      : ${REPORT_DIR}"
echo "Report file     : ${VALIDATE_REPORT}"

# Read Collection labels and render the Bundle label from the Jinja2 template.
# render_psa_bundle.py must accept --list-author and expose list_author to the
# Jinja2 template.
python3 "${RENDERER_FILE}" \
    "${BUNDLE_DIR}" \
    --template "${TEMPLATE_FILE}" \
    --bundle-lid "${BUNDLE_LID}" \
    --bundle-vid "${BUNDLE_VID}" \
    --publication-year "${PUBLICATION_YEAR}" \
    --list-author "${LIST_AUTHOR}" \
    --modification-date "${MODIFICATION_DATE}" \
    --output "${OUTPUT_FILE}"

BUNDLE_XML="${BUNDLE_DIR}/${OUTPUT_FILE}"
[[ -f "${BUNDLE_XML}" ]] || {
    echo "ERROR: Generated Bundle XML not found: ${BUNDLE_XML}" >&2
    exit 1
}

if [[ "${VALIDATE_ENABLED}" == "0" ]]; then
    echo "Validation skipped because VALIDATE_ENABLED=0"
    exit 0
fi

[[ -x "${VALIDATE_BIN}" ]] || {
    echo "ERROR: Validate executable not found or not executable: ${VALIDATE_BIN}" >&2
    exit 1
}

VALIDATE_ARGS=(
    --rule pds4.bundle
    --target "${BUNDLE_DIR}"
)

if [[ -n "${BUNDLE_LABEL_EXTENSION}" ]]; then
    VALIDATE_ARGS+=(--label-extension "${BUNDLE_LABEL_EXTENSION}")
fi

if [[ -n "${VALIDATE_CATALOG}" ]]; then
    if [[ -f "${VALIDATE_CATALOG}" ]]; then
        VALIDATE_ARGS+=(--catalog "${VALIDATE_CATALOG}")
        echo "Using XML catalog: ${VALIDATE_CATALOG}"
    else
        echo "WARNING: XML catalog was not found: ${VALIDATE_CATALOG}" >&2
        echo "WARNING: Validation will continue without --catalog." >&2
    fi
else
    echo "XML catalog is not specified."
    echo "Validation will continue without --catalog."
fi

echo "Validating Bundle: ${BUNDLE_DIR}"
echo "Validation report: ${VALIDATE_REPORT}"
printf 'Validation command:'
printf ' %q' "${VALIDATE_BIN}" "${VALIDATE_ARGS[@]}"
printf '\n'

"${VALIDATE_BIN}" "${VALIDATE_ARGS[@]}" 2>&1 | tee "${VALIDATE_REPORT}"

echo "Bundle validation passed."
echo "Validation report saved to: ${VALIDATE_REPORT}"
