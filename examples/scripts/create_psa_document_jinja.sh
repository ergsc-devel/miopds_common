#!/usr/bin/env bash
#
# Create a Product_Document label and its Document Collection (label and
# inventory), then validate both labels.
# Product_Document のラベルと Document Collection（ラベルとインベントリ）を作り、
# PDS Validate で2つのラベルを検証する。
#
# Usage / 使い方:
#   create_psa_document_jinja.sh [DOCUMENT_DIR]
#
# Other settings are environment variables (see ../README.md).
# その他の設定は環境変数で変更する（../README.md を参照）。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -- Document / Document の設定 ---------------------------------------------------
# The PDF must be in DOCUMENT_DIR / PDF は DOCUMENT_DIR の中に置く
DOCUMENT_DIR="${1:-bc_mmo_pwi/document}"
DOCUMENT_DIR="${DOCUMENT_DIR%/}"
PDF_FILE="${PDF_FILE:-bc_mmo_pwi_data_user_guide.pdf}"
DOCUMENT_LID="${DOCUMENT_LID:-urn:jaxa:darts:bc_mmo_pwi:document:bc_mmo_pwi_data_user_guide}"
COLLECTION_LID="${COLLECTION_LID:-urn:jaxa:darts:bc_mmo_pwi:document}"
VERSION_ID="${VERSION_ID:-1.0}"
TITLE="${TITLE:-BepiColombo MMO Plasma Wave Investigation Data User Guide}"
DESCRIPTION="${DESCRIPTION:-Data user guide for the BepiColombo Mercury Magnetospheric Orbiter Plasma Wave Investigation archive. The guide describes all level products, archive organization, data format, time and coordinate systems, calibration, processing, and quality information.}"
PUBLICATION_YEAR="${PUBLICATION_YEAR:-2027}"
PUBLICATION_DATE="${PUBLICATION_DATE:-2027}"
MODIFICATION_DATE="${MODIFICATION_DATE:-$(date -u +%F)}"
DOCUMENT_MODIFICATION_DESCRIPTION="${DOCUMENT_MODIFICATION_DESCRIPTION:-Initial version of the PWI Data User Guide document label.}"
COLLECTION_MODIFICATION_DESCRIPTION="${COLLECTION_MODIFICATION_DESCRIPTION:-Initial version of the PWI document collection.}"

# Output file names / 出力ファイル名
DOCUMENT_OUTPUT="${DOCUMENT_OUTPUT:-bc_mmo_pwi_data_user_guide.lblx}"
COLLECTION_OUTPUT="${COLLECTION_OUTPUT:-collection_bc_mmo_pwi_document.lblx}"
# Must be the COLLECTION_OUTPUT name with .csv instead of .lblx
# COLLECTION_OUTPUT と同じ名前で、拡張子だけ .lblx を .csv にしたもの
INVENTORY_OUTPUT="${INVENTORY_OUTPUT:-${COLLECTION_OUTPUT%.lblx}.csv}"

# Templates and config files / テンプレートと設定ファイル
DOCUMENT_TEMPLATE="${DOCUMENT_TEMPLATE:-$SCRIPT_DIR/../templates/document_template.xml.j2}"
COLLECTION_TEMPLATE="${COLLECTION_TEMPLATE:-$SCRIPT_DIR/../templates/document_collection_template.xml.j2}"
MISSION_CONFIG="${MISSION_CONFIG:-$SCRIPT_DIR/../config/mission.json}"
INSTRUMENT_CONFIG="${INSTRUMENT_CONFIG:-$SCRIPT_DIR/../config/instrument_pwi.json}"

# -- Reports and PDS Validate / レポートと PDS Validate ---------------------------
REPORT_DIR="${REPORT_DIR:-./pds_chk_log}"
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
DOCUMENT_REPORT="${DOCUMENT_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_bc_mmo_pwi_document_validate_report.txt}"
COLLECTION_REPORT="${COLLECTION_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_bc_mmo_pwi_document_collection_validate_report.txt}"
VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"   # 0: skip validation / 0 なら検証しない
VALIDATE_BIN="${VALIDATE_BIN:-$HOME/local/pds/validate-4.2.0/bin/validate}"
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"   # "": no catalog / 空ならカタログなし

# Python that has miopds_common installed. It differs between servers
# (python3 or python, venv path): set PYTHON for each server (../README.md).
# miopds_common をインストールした Python。サーバーごとに異なるので
# （python3 か python か、venv の場所）、サーバーごとに PYTHON を指定する（../README.md）。
PYTHON="${PYTHON:-python3}"

# -- Checks / 事前確認 ------------------------------------------------------------
# Check with the same Python that runs the jobs
# 実行に使うのと同じ Python で確認する
"$PYTHON" -c 'import miopds_common' 2>/dev/null || {
  echo "ERROR: miopds_common is not installed for $PYTHON" >&2
  echo "       Activate the venv, or set PYTHON=/path/to/python" >&2
  exit 1
}

# -- Generate the document label and the document collection --------------------
# -- Document のラベルと Document Collection を作る -------------------------------
# miopds_common/_cli.py: document_set_main()
"$PYTHON" -m miopds_common pdf2document "$DOCUMENT_DIR" \
  --document-template "$DOCUMENT_TEMPLATE" \
  --collection-template "$COLLECTION_TEMPLATE" \
  --mission-config "$MISSION_CONFIG" \
  --instrument-config "$INSTRUMENT_CONFIG" \
  --document-lid "$DOCUMENT_LID" \
  --collection-lid "$COLLECTION_LID" \
  --version-id "$VERSION_ID" \
  --title "$TITLE" \
  --description "$DESCRIPTION" \
  --publication-year "$PUBLICATION_YEAR" \
  --publication-date "$PUBLICATION_DATE" \
  --modification-date "$MODIFICATION_DATE" \
  --document-modification-description "$DOCUMENT_MODIFICATION_DESCRIPTION" \
  --collection-modification-description "$COLLECTION_MODIFICATION_DESCRIPTION" \
  --pdf-file "$PDF_FILE" \
  --document-output "$DOCUMENT_OUTPUT" \
  --collection-output "$COLLECTION_OUTPUT" \
  --inventory-output "$INVENTORY_OUTPUT"

# -- Validate both labels / 2つのラベルを検証 ----------------------------------------
if [[ "$VALIDATE_ENABLED" == "0" ]]; then
  echo "Validation skipped because VALIDATE_ENABLED=0"
  exit 0
fi
# miopds_common/_cli.py: validate_main()
"$PYTHON" -m miopds_common validate "$DOCUMENT_DIR/$DOCUMENT_OUTPUT" \
  --report "$DOCUMENT_REPORT" \
  --validate-bin "$VALIDATE_BIN" \
  --catalog "$VALIDATE_CATALOG"
"$PYTHON" -m miopds_common validate "$DOCUMENT_DIR/$COLLECTION_OUTPUT" \
  --report "$COLLECTION_REPORT" \
  --validate-bin "$VALIDATE_BIN" \
  --catalog "$VALIDATE_CATALOG"
