#!/usr/bin/env bash
#
# Create a PSA/PDS4 Collection label and inventory, then validate the label.
# Collection のラベルとインベントリを作り、PDS Validate でラベルを検証する。
#
# Usage / 使い方:
#   create_psa_collection_jinja.sh [COLLECTION_NAME] [COLLECTION_DIR]
#
# Other settings are environment variables (see ../README.md).
# その他の設定は環境変数で変更する（../README.md を参照）。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -- Collection / Collection の設定 ---------------------------------------------
COLLECTION_NAME="${1:-data_calibrated_efd}"
COLLECTION_DIR="${2:-bc_mmo_pwi/$COLLECTION_NAME}"
COLLECTION_DIR="${COLLECTION_DIR%/}"
BUNDLE_NAME="${BUNDLE_NAME:-bc_mmo_pwi}"
LABEL_DIR="${LABEL_DIR:-$COLLECTION_DIR/science}"
COLLECTION_LID="${COLLECTION_LID:-urn:jaxa:darts:$BUNDLE_NAME:$COLLECTION_NAME}"
OUTPUT_BASE="${OUTPUT_BASE:-$COLLECTION_NAME}"
PUBLICATION_YEAR="${PUBLICATION_YEAR:-2027}"
VERSION_ID="${VERSION_ID:-1.0}"

# Template and config files / テンプレートと設定ファイル
TEMPLATE_FILE="${TEMPLATE_FILE:-$SCRIPT_DIR/../templates/collection_template.xml.j2}"
MISSION_CONFIG="${MISSION_CONFIG:-$SCRIPT_DIR/../config/mission.json}"
DATASET_CONFIG="${DATASET_CONFIG:-$SCRIPT_DIR/../config/dataset_pwi_efd.json}"

# -- Reports and PDS Validate / レポートと PDS Validate ---------------------------
REPORT_DIR="${REPORT_DIR:-./pds_chk_log}"
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
VALIDATE_REPORT="${VALIDATE_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_validate_report.txt}"
# Labels skipped for missing CDF; kept outside the archive
# CDF がなく除外したラベルの一覧。アーカイブの外に保存する
SKIP_REPORT="${SKIP_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_skipped_missing_cdf.txt}"
VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"   # 0: skip validation / 0 なら検証しない
VALIDATE_BIN="${VALIDATE_BIN:-$HOME/local/pds/validate/bin/validate}"
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"   # "": no catalog / 空ならカタログなし

# Python that has miopds_common installed. It differs between servers
# (python3 or python, venv path): set PYTHON for each server (../README.md).
# miopds_common をインストールした Python。サーバーごとに異なるので
# （python3 か python か、venv の場所）、サーバーごとに PYTHON を指定する（../README.md）。
PYTHON="${PYTHON:-python3}"

# -- Checks / 事前確認 ------------------------------------------------------------
case "$COLLECTION_NAME" in
  *[!A-Za-z0-9_-]*|'')
    echo "ERROR: invalid Collection name: $COLLECTION_NAME" >&2
    exit 1
    ;;
esac
# Check with the same Python that runs the jobs
# 実行に使うのと同じ Python で確認する
"$PYTHON" -c 'import miopds_common' 2>/dev/null || {
  echo "ERROR: miopds_common is not installed for $PYTHON" >&2
  echo "       Activate the venv, or set PYTHON=/path/to/python" >&2
  exit 1
}

# -- Generate / 生成 --------------------------------------------------------------
# miopds_common/_cli.py: collection_main()
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

# -- Validate / 検証 --------------------------------------------------------------
if [[ "$VALIDATE_ENABLED" == "0" ]]; then
  echo "Validation skipped because VALIDATE_ENABLED=0"
  exit 0
fi
# miopds_common/_cli.py: validate_main()
"$PYTHON" -m miopds_common validate "$COLLECTION_DIR/${OUTPUT_BASE}.lblx" \
  --report "$VALIDATE_REPORT" \
  --validate-bin "$VALIDATE_BIN" \
  --catalog "$VALIDATE_CATALOG"
