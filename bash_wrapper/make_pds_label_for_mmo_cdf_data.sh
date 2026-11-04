#!/usr/bin/env bash
#
# Generate a PDS4 observational label (.lblx) from a CDF file.
# CDF ファイルから PDS4 観測ラベル（.lblx）を作る。
#
# Usage / 使い方:
#   make_pds_label_for_mmo_cdf_data.sh \
#     CDF_FILE TEMPLATE_DIR TEMPLATE_NAME OUTPUT_DIR [miopds-label OPTIONS...]
#
#   TEMPLATE_NAME "" uses LABEL_TEMPLATE of the settings file
#   (default: mmo_cdf_label_template_multi_dataset.xml.j2).
#   TEMPLATE_NAME に "" を渡すと、設定ファイルの LABEL_TEMPLATE を使う
#   （既定は mmo_cdf_label_template_multi_dataset.xml.j2）。
#   Options after OUTPUT_DIR go to miopds-label and override the defaults below.
#   OUTPUT_DIR より後のオプションは miopds-label に渡され、下の既定値より優先される。
#   The set_label_args function of the settings file adds options for each CDF
#   file (see README.md).
#   設定ファイルの set_label_args 関数が、CDF ごとのオプションを足す（README.md）。
#   Set MISSION_TIMELINE to a mission_timeline.json to take the mission phase
#   from it; without it, the defaults in mission.json are used.
#   MISSION_TIMELINE に mission_timeline.json を指定すると、ミッションフェーズを
#   そこから決める。指定しなければ mission.json の既定値を使う。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read the settings file of one data Collection (README.md). Choose the file with
# PIPELINE_SETTINGS (any name); without it, the default below is read. Environment
# variables given when running the script win over the values in the file.
# 1つのデータの Collection の設定ファイルを読む（README.md）。ファイルは
# PIPELINE_SETTINGS で選ぶ（名前は自由）。指定がなければ下の既定のファイルを読む。
# 実行時に付けた環境変数は、ファイルの値より優先される。
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

USAGE="Usage: $0 CDF_FILE TEMPLATE_DIR TEMPLATE_NAME OUTPUT_DIR [OPTIONS...]"

CDF_FILE="${1:?$USAGE}"
TEMPLATE_DIR="${2:?$USAGE}"
TEMPLATE_NAME="${3:-${LABEL_TEMPLATE:-mmo_cdf_label_template_multi_dataset.xml.j2}}"
OUTPUT_DIR="${4:?$USAGE}"

# Config files / 設定ファイル
MISSION_CONFIG="${MISSION_CONFIG:-$SCRIPT_DIR/../user_config/mission.json}"
DATASET_CONFIG="${DATASET_CONFIG:-$SCRIPT_DIR/../user_config/dataset_pwi_efd.json}"

# Timeline (optional) / 期間表（任意）
MISSION_TIMELINE="${MISSION_TIMELINE:-}"
TIMELINE_ARGS=()
if [[ -n "$MISSION_TIMELINE" ]]; then
  TIMELINE_ARGS=(--timeline "$MISSION_TIMELINE")
fi

# Python that has miopds_common installed. It differs between servers
# (python3 or python, venv path): set PYTHON for each server (README.md).
# miopds_common をインストールした Python。サーバーごとに異なるので
# （python3 か python か、venv の場所）、サーバーごとに PYTHON を指定する（README.md）。
PYTHON="${PYTHON:-python3}"

# Check with the same Python that runs the jobs
# 実行に使うのと同じ Python で確認する
"$PYTHON" -c 'import miopds_common' 2>/dev/null || {
  echo "ERROR: miopds_common is not installed for $PYTHON" >&2
  echo "       Activate the venv, or set PYTHON=/path/to/python" >&2
  exit 1
}

# Options of the settings file for this CDF file. The options after OUTPUT_DIR
# come later on the command, so they win over these.
# 設定ファイルの、この CDF に足すオプション。OUTPUT_DIR より後のオプションは
# コマンドの後ろに並ぶので、こちらより優先される。
LABEL_ARGS=()
if declare -F set_label_args >/dev/null; then
  set_label_args "$CDF_FILE"
fi

# miopds_common/_cli.py: label_main()
"$PYTHON" -m miopds_common cdf2pdslabel \
  "$CDF_FILE" \
  "$TEMPLATE_DIR/$TEMPLATE_NAME" \
  "$OUTPUT_DIR" \
  --mission-config "$MISSION_CONFIG" \
  --dataset-config "$DATASET_CONFIG" \
  ${TIMELINE_ARGS[@]+"${TIMELINE_ARGS[@]}"} \
  ${LABEL_ARGS[@]+"${LABEL_ARGS[@]}"} \
  "${@:5}"
