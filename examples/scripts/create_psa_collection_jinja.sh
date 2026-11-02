#!/usr/bin/env bash
#
# Create a PSA/PDS4 Collection label and inventory, then validate the label.
# Collection のラベルとインベントリを作り、PDS Validate でラベルを検証する。
#
# The Collection directory is given by COLLECTION_DIR. Without it, the
# directory is ARCHIVE_ROOT/BUNDLE_NAME/COLLECTION_NAME (ARCHIVE_ROOT defaults
# to the current directory). Labels in any subdirectory (e.g.
# <phase>/<data_type>/<YYYYMMDD_YYYYMMDD>/, one directory per month) are
# gathered recursively by labels2collection.
# Collection のディレクトリは COLLECTION_DIR で渡す。指定しなければ
# ARCHIVE_ROOT/BUNDLE_NAME/COLLECTION_NAME になる（ARCHIVE_ROOT の既定値は
# 実行した場所）。どのサブディレクトリのラベルも（例：<フェーズ>/<データの種類>/
# <YYYYMMDD_YYYYMMDD>/、月ごとのディレクトリ）、labels2collection が再帰的に集める。
#
# Usage / 使い方:
#   create_psa_collection_jinja.sh [COLLECTION_NAME]
#
# Optional environment overrides:
#   ARCHIVE_ROOT, BUNDLE_NAME, COLLECTION_DIR, LABEL_DIR,
#   MISSION_TIMELINE, PYTHON, VALIDATE_ENABLED, VALIDATE_OPTION
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -- Archive and Collection settings -------------------------------------------
COLLECTION_NAME="${1:-data_calibrated_efd}"
BUNDLE_NAME="${BUNDLE_NAME:-bc_mmo_pwi}"

# Root containing bundle directories such as bc_mmo_pwi (default: the current
# directory). On a server, set it in the cron line.
# bc_mmo_pwi などの Bundle のディレクトリを置いた場所（既定値は実行した場所）。
# サーバーでは cron の行で指定する。
ARCHIVE_ROOT="${ARCHIVE_ROOT:-.}"
ARCHIVE_ROOT="${ARCHIVE_ROOT%/}"

# Derive the collection directory automatically. COLLECTION_DIR remains an
# environment override for testing or a non-standard deployment.
COLLECTION_DIR="${COLLECTION_DIR:-${ARCHIVE_ROOT}/${BUNDLE_NAME}}"
COLLECTION_DIR="${COLLECTION_DIR%/}"

# Labels are searched recursively below this directory, e.g.
#   <phase>/<data_type>/<YYYYMMDD_YYYYMMDD>/*.lblx  (one directory per month)
# このディレクトリの下のラベルを再帰的に探す（上は月ごとのディレクトリの例）。
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
# Timeline (optional): checked only when it is given. labels2collection does
# not read it.
# 期間表（任意）：指定したときだけ確かめる。labels2collection は読まない。
MISSION_TIMELINE="${MISSION_TIMELINE:-}"

# -- Reports and PDS Validate --------------------------------------------------
REPORT_DIR="${REPORT_DIR:-./pds_chk_log}"
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
VALIDATE_REPORT="${VALIDATE_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_validate_report.txt}"
SKIP_REPORT="${SKIP_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_skipped_missing_cdf.txt}"
VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"
VALIDATE_BIN="${VALIDATE_BIN:-$HOME/local/pds/validate/bin/validate}"
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"
# More options for PDS Validate, e.g. "-D --add-context-products context.json"
# PDS Validate に足すオプション（例："-D --add-context-products context.json"）
VALIDATE_OPTION="${VALIDATE_OPTION:-}"
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
  "$DATASET_CONFIG"
do
  [[ -r "$required_file" ]] || {
    echo "ERROR: required file is not readable: $required_file" >&2
    exit 1
  }
done

if [[ -n "$MISSION_TIMELINE" ]]; then
  [[ -r "$MISSION_TIMELINE" ]] || {
    echo "ERROR: MISSION_TIMELINE is not readable: $MISSION_TIMELINE" >&2
    exit 1
  }
  "$PYTHON" -m json.tool "$MISSION_TIMELINE" >/dev/null || {
    echo "ERROR: invalid mission timeline JSON: $MISSION_TIMELINE" >&2
    exit 1
  }
fi

[[ -d "$COLLECTION_DIR" ]] || {
  echo "ERROR: Collection directory was not found: $COLLECTION_DIR" >&2
  exit 1
}

[[ -d "$LABEL_DIR" ]] || {
  echo "ERROR: Dynamic science label root was not found: $LABEL_DIR" >&2
  exit 1
}

# Count labels recursively. The phase/month paths are not hard-coded here.
LABEL_COUNT=$(find "$LABEL_DIR" -type f -name '*.lblx' -print | wc -l)
if (( LABEL_COUNT == 0 )); then
  echo "ERROR: No LBLX files were found below: $LABEL_DIR" >&2
  exit 1
fi

mkdir -p "$REPORT_DIR"

echo "Collection name : $COLLECTION_NAME"
echo "Collection dir  : $COLLECTION_DIR"
echo "Label root      : $LABEL_DIR"
echo "Timeline JSON   : ${MISSION_TIMELINE:-(not set)}"
echo "LBLX files      : $LABEL_COUNT"

# Show the directories that currently contain labels. This is diagnostic
# only; labels2collection receives LABEL_DIR.
# -exec dirname works with both GNU and BSD (macOS) find; -printf is GNU only.
# -exec dirname は GNU と BSD（macOS）の find の両方で使える。-printf は GNU だけ。
echo "Label directories:"
find "$LABEL_DIR" -type f -name '*.lblx' -exec dirname {} \; |
  sort -u |
  sed 's/^/  /'

# -- Generate ------------------------------------------------------------------
# labels2collection receives LABEL_DIR and recursively gathers the labels in
# all its subdirectories.
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
  --label-extension "lblx" \
  --validate-option="$VALIDATE_OPTION"
