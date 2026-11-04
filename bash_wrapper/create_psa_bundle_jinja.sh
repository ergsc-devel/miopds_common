#!/usr/bin/env bash
#
# Create a PSA/PDS4 Bundle label from the Collection labels below the Bundle
# directory, then validate the whole Bundle.
# Bundle ディレクトリ以下の Collection ラベルから Bundle ラベルを作り、
# PDS Validate で Bundle 全体を検証する。
#
# Usage / 使い方:
#   create_psa_bundle_jinja.sh [BUNDLE_DIR]
#
# Default output / 既定の出力:
#   bc_mmo_pwi/bc_mmo_pwi.lblx
#
# Other settings are read from the settings file (PIPELINE_SETTINGS), and
# environment variables win over them (see README.md).
# その他の設定は設定ファイル（PIPELINE_SETTINGS）から読み、環境変数で変更できる
# （README.md を参照）。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read one settings file of the Bundle (README.md): the values of the Bundle and
# the Document are the same in all its files. Choose the file with
# PIPELINE_SETTINGS (any name); without it, the default below is read. Environment
# variables given when running the script win over the values in the file.
# この Bundle の設定ファイルを1つ読む（README.md）。Bundle と Document の値は、どの
# ファイルでも同じ。ファイルは PIPELINE_SETTINGS で選ぶ（名前は自由）。指定がなければ
# 下の既定のファイルを読む。実行時に付けた環境変数は、ファイルの値より優先される。
PIPELINE_SETTINGS="${PIPELINE_SETTINGS:-$SCRIPT_DIR/../user_config/pipeline_settings.sh}"
[[ -r "$PIPELINE_SETTINGS" ]] || {
  echo "ERROR: settings file is not readable: $PIPELINE_SETTINGS" >&2
  echo "       Copy user_config/pipeline_settings.sh, or set PIPELINE_SETTINGS" >&2
  exit 1
}
SETTINGS_DIR="$(cd "$(dirname "$PIPELINE_SETTINGS")" && pwd)"
# Use the full path: "source" searches PATH for a name without "/"
# 絶対パスにする（source は、/ のない名前を PATH から探すため）
PIPELINE_SETTINGS="$SETTINGS_DIR/${PIPELINE_SETTINGS##*/}"
source "$PIPELINE_SETTINGS"

# -- Bundle / Bundle の設定 -------------------------------------------------------
BUNDLE_DIR="${1:-bc_mmo_pwi}"
BUNDLE_DIR="${BUNDLE_DIR%/}"
# The last path component is the Bundle name / パスの最後の部分を Bundle 名にする
BUNDLE_NAME="${BUNDLE_NAME:-${BUNDLE_DIR##*/}}"
BUNDLE_LID="${BUNDLE_LID:-urn:jaxa:darts:${BUNDLE_NAME}}"
BUNDLE_VID="${BUNDLE_VID:-1.0}"
PUBLICATION_YEAR="${PUBLICATION_YEAR:-2027}"
MODIFICATION_DATE="${MODIFICATION_DATE:-$(date -u +%F)}"
OUTPUT_FILE="${OUTPUT_FILE:-${BUNDLE_NAME}.lblx}"

# Template and config files / テンプレートと設定ファイル
TEMPLATE_FILE="${TEMPLATE_FILE:-${SCRIPT_DIR}/../label_templates/bundle_template.xml.j2}"
MISSION_CONFIG="${MISSION_CONFIG:-${SCRIPT_DIR}/../user_config/mission.json}"
INSTRUMENT_CONFIG="${INSTRUMENT_CONFIG:-${SCRIPT_DIR}/../user_config/instrument_pwi.json}"

# -- Reports and PDS Validate / レポートと PDS Validate ---------------------------
REPORT_DIR="${REPORT_DIR:-./pds_chk_log}"
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
# Validate's own report (--report-file) / Validate 自身が書くレポート（--report-file）
VALIDATE_REPORT="${VALIDATE_REPORT:-${REPORT_DIR}/${REPORT_TIMESTAMP}_${BUNDLE_NAME}_bundle_validate_report.txt}"
# What Validate printed on the screen / Validate が画面に出した内容の記録
VALIDATE_LOG="${VALIDATE_LOG:-${REPORT_DIR}/${REPORT_TIMESTAMP}_${BUNDLE_NAME}_bundle_validate_log.txt}"
VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"   # 0: skip validation / 0 なら検証しない
VALIDATE_BIN="${VALIDATE_BIN:-${HOME}/local/pds/validate/bin/validate}"
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"   # "": no catalog / 空ならカタログなし
# More options for PDS Validate, e.g. "-D --add-context-products context.json"
# PDS Validate に足すオプション（例："-D --add-context-products context.json"）
VALIDATE_OPTION="${VALIDATE_OPTION:-}"
# Label file extension for Validate ("": Validate's default, xml)
# Validate に渡すラベルの拡張子（空なら Validate の既定の xml）
BUNDLE_LABEL_EXTENSION="${BUNDLE_LABEL_EXTENSION-lblx}"

# Python that has miopds_common installed. It differs between servers
# (python3 or python, venv path): set PYTHON for each server (README.md).
# miopds_common をインストールした Python。サーバーごとに異なるので
# （python3 か python か、venv の場所）、サーバーごとに PYTHON を指定する（README.md）。
PYTHON="${PYTHON:-python3}"

# -- Checks / 事前確認 ------------------------------------------------------------
# Check with the same Python that runs the jobs
# 実行に使うのと同じ Python で確認する
"$PYTHON" -c 'import miopds_common' 2>/dev/null || {
    echo "ERROR: miopds_common is not installed for $PYTHON" >&2
    echo "       Activate the venv, or set PYTHON=/path/to/python" >&2
    exit 1
}

# -- Generate / 生成 --------------------------------------------------------------
# miopds_common/_cli.py: bundle_main()
"$PYTHON" -m miopds_common collections2bundle \
    "${BUNDLE_DIR}" \
    --template "${TEMPLATE_FILE}" \
    --bundle-lid "${BUNDLE_LID}" \
    --version-id "${BUNDLE_VID}" \
    --publication-year "${PUBLICATION_YEAR}" \
    --mission-config "${MISSION_CONFIG}" \
    --instrument-config "${INSTRUMENT_CONFIG}" \
    --modification-date "${MODIFICATION_DATE}" \
    --output "${OUTPUT_FILE}"

# -- Validate the whole Bundle / Bundle 全体を検証 ------------------------------------
if [[ "${VALIDATE_ENABLED}" == "0" ]]; then
    echo "Validation skipped because VALIDATE_ENABLED=0"
    exit 0
fi
# miopds_common/_cli.py: validate_main()
"$PYTHON" -m miopds_common validate "${BUNDLE_DIR}" \
    --rule pds4.bundle \
    --label-extension "${BUNDLE_LABEL_EXTENSION}" \
    --report "${VALIDATE_LOG}" \
    --report-file "${VALIDATE_REPORT}" \
    --validate-bin "${VALIDATE_BIN}" \
    --catalog "${VALIDATE_CATALOG}" \
    --validate-option="${VALIDATE_OPTION}"
