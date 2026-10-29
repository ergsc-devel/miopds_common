#!/usr/bin/env bash
#
# Generate the PDS4 observational labels (.lblx) for all CDF files in one
# Collection. Every label is made again; the Collection label and inventory
# are not touched (use create_psa_collection_jinja.sh for them).
# 1つの Collection にあるすべての CDF ファイルの PDS4 観測ラベル（.lblx）を作る。
# ラベルはすべて作り直す。Collection のラベルとインベントリは変えない
# （それには create_psa_collection_jinja.sh を使う）。
#
# Usage / 使い方:
#   make_all_pds_label_for_collection.sh COLLECTION_DIR [miopds-label OPTIONS...]
#
#   The CDF files may be in any subdirectory of COLLECTION_DIR
#   (e.g. <phase>/<data_type>/<YYYYMMDD_YYYYMMDD>/, one directory per month).
#   Each label is written beside its CDF file.
#   CDF は COLLECTION_DIR の下のどのサブディレクトリにあってもよい
#   （例：<フェーズ>/<データの種類>/<月>/）。ラベルは CDF の隣に作る。
#   Options after COLLECTION_DIR go to make_pds_label_for_mmo_cdf_data.sh,
#   and then to miopds-label, for every CDF file.
#   COLLECTION_DIR より後のオプションは、すべての CDF について
#   make_pds_label_for_mmo_cdf_data.sh を経て miopds-label に渡される。
#   MISSION_CONFIG, DATASET_CONFIG and MISSION_TIMELINE are passed on as they are.
#   MISSION_CONFIG、DATASET_CONFIG、MISSION_TIMELINE はそのまま子 shell に渡る。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USAGE="Usage: $0 COLLECTION_DIR [OPTIONS...]"

COLLECTION_DIR="${1:?$USAGE}"
COLLECTION_DIR="${COLLECTION_DIR%/}"
shift

TEMPLATES_DIR="${TEMPLATES_DIR:-$SCRIPT_DIR/../templates}"

# Python that has miopds_common installed. It differs between servers
# (python3 or python, venv path): set PYTHON for each server (../README.md).
# Exported so that the child script uses the same Python.
# miopds_common をインストールした Python。サーバーごとに異なるので
# （python3 か python か、venv の場所）、サーバーごとに PYTHON を指定する（../README.md）。
# 子 shell も同じ Python を使うよう export する。
export PYTHON="${PYTHON:-python3}"

# -- Checks / 事前確認 ------------------------------------------------------------
[[ -d "$COLLECTION_DIR" ]] || {
  echo "ERROR: Collection directory not found: $COLLECTION_DIR" >&2
  exit 1
}
# Check with the same Python that runs the jobs
# 実行に使うのと同じ Python で確認する
"$PYTHON" -c 'import miopds_common' 2>/dev/null || {
  echo "ERROR: miopds_common is not installed for $PYTHON" >&2
  echo "       Activate the venv, or set PYTHON=/path/to/python" >&2
  exit 1
}

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/miopds_make_all_pds_label.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

find "$COLLECTION_DIR" -type f \( -name '*.cdf' -o -name '*.CDF' \) | sort > "$WORK_DIR/cdf_files.txt"
[[ -s "$WORK_DIR/cdf_files.txt" ]] || {
  echo "ERROR: no CDF file below $COLLECTION_DIR" >&2
  exit 1
}

# -- Generate / 生成 --------------------------------------------------------------
made=0
while IFS= read -r cdf; do
  # stdin from /dev/null: the loop reads the CDF list from stdin
  # 標準入力は /dev/null（繰り返しが標準入力から CDF の一覧を読んでいるため）
  "$SCRIPT_DIR/make_pds_label_for_mmo_cdf_data.sh" \
    "$cdf" "$TEMPLATES_DIR" "" "$(dirname "$cdf")" \
    "$@" < /dev/null
  made=$((made + 1))
done < "$WORK_DIR/cdf_files.txt"

# A label whose CDF is gone is only reported. -mindepth 2 skips the
# Collection label itself, which has no CDF.
# CDF がなくなったラベルは報告するだけ。-mindepth 2 で、CDF を持たない
# Collection のラベル自身を除く。
stale=0
find "$COLLECTION_DIR" -mindepth 2 -type f -name '*.lblx' | sort > "$WORK_DIR/label_files.txt"
while IFS= read -r label; do
  if [[ ! -e "${label%.lblx}.cdf" && ! -e "${label%.lblx}.CDF" ]]; then
    echo "WARNING: label without CDF (not removed): $label" >&2
    stale=$((stale + 1))
  fi
done < "$WORK_DIR/label_files.txt"

echo "Labels: $made made, $stale without CDF ($COLLECTION_DIR)"
