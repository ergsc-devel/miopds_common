#!/usr/bin/env bash
#
# Generate a PDS4 observational label (.lblx) from a CDF file.
# CDF ファイルから PDS4 観測ラベル（.lblx）を作る。
#
# Usage / 使い方:
#   make_pds_label_for_mmo_cdf_data.sh \
#     CDF_FILE TEMPLATE_DIR TEMPLATE_NAME OUTPUT_DIR [miopds-label OPTIONS...]
#
#   TEMPLATE_NAME "" uses mmo_cdf_label_template_multi_dataset.xml.j2.
#   TEMPLATE_NAME に "" を渡すと mmo_cdf_label_template_multi_dataset.xml.j2 を使う。
#   Options after OUTPUT_DIR go to miopds-label and override the defaults below.
#   OUTPUT_DIR より後のオプションは miopds-label に渡され、下の既定値より優先される。
#   Set MISSION_TIMELINE to a mission_timeline.json to take the mission phase
#   from it; without it, the defaults in mission.json are used.
#   MISSION_TIMELINE に mission_timeline.json を指定すると、ミッションフェーズを
#   そこから決める。指定しなければ mission.json の既定値を使う。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USAGE="Usage: $0 CDF_FILE TEMPLATE_DIR TEMPLATE_NAME OUTPUT_DIR [OPTIONS...]"

CDF_FILE="${1:?$USAGE}"
TEMPLATE_DIR="${2:?$USAGE}"
TEMPLATE_NAME="${3:-mmo_cdf_label_template_multi_dataset.xml.j2}"
OUTPUT_DIR="${4:?$USAGE}"

# Config files / 設定ファイル
MISSION_CONFIG="${MISSION_CONFIG:-$SCRIPT_DIR/../config/mission.json}"
DATASET_CONFIG="${DATASET_CONFIG:-$SCRIPT_DIR/../config/dataset_pwi_efd.json}"

# Timeline (optional) / 期間表（任意）
MISSION_TIMELINE="${MISSION_TIMELINE:-}"
TIMELINE_ARGS=()
if [[ -n "$MISSION_TIMELINE" ]]; then
  TIMELINE_ARGS=(--timeline "$MISSION_TIMELINE")
fi

# Python that has miopds_common installed. It differs between servers
# (python3 or python, venv path): set PYTHON for each server (../README.md).
# miopds_common をインストールした Python。サーバーごとに異なるので
# （python3 か python か、venv の場所）、サーバーごとに PYTHON を指定する（../README.md）。
PYTHON="${PYTHON:-python3}"

# Check with the same Python that runs the jobs
# 実行に使うのと同じ Python で確認する
"$PYTHON" -c 'import miopds_common' 2>/dev/null || {
  echo "ERROR: miopds_common is not installed for $PYTHON" >&2
  echo "       Activate the venv, or set PYTHON=/path/to/python" >&2
  exit 1
}

# miopds_common/_cli.py: label_main()
"$PYTHON" -m miopds_common cdf2pdslabel \
  "$CDF_FILE" \
  "$TEMPLATE_DIR/$TEMPLATE_NAME" \
  "$OUTPUT_DIR" \
  --mission-config "$MISSION_CONFIG" \
  --dataset-config "$DATASET_CONFIG" \
  ${TIMELINE_ARGS[@]+"${TIMELINE_ARGS[@]}"} \
  "${@:5}"
