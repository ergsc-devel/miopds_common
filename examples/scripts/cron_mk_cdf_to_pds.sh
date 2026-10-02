#!/usr/bin/env bash
#
# Update the archive of one instrument: walk through the target files and
# rebuild only what is out of date (parent script).
# 1つの機器のアーカイブを更新する。対象ファイルを巡回し、古くなったものだけを
# 作り直す（親 shell）。
#
#   1. a label for each CDF        make_pds_label_for_mmo_cdf_data.sh
#   2. each data collection        create_psa_collection_jinja.sh
#   3. document + doc collection   create_psa_document_jinja.sh
#   4. bundle                      create_psa_bundle_jinja.sh
#
# A product is rebuilt when it does not exist or when one of its inputs is
# newer than it (like "make"). Inputs: the source file (CDF, labels, PDF),
# the templates, the config files, these scripts and the miopds_common code.
# 出力がない、または入力のどれかが出力より新しいときに作り直す（make と同じ考え方）。
# 入力：元のファイル（CDF、ラベル、PDF）、テンプレート、設定ファイル、shell、
# miopds_common の Python コード。
#
# Usage / 使い方:
#   cron_mk_cdf_to_pds.sh [all] [BUNDLE_DIR]
#     all : rebuild everything / すべて作り直す
#
# Expected layout / 想定するディレクトリ構成:
#   BUNDLE_DIR/<collection>/science/**/*.cdf   data; labels are written beside the CDF
#   BUNDLE_DIR/document/*.pdf                  documents (optional / なくてもよい)
#
# Creating the L2 CDF files and copying them here is done by each instrument's
# own pipeline before this script.
# L2 CDF の作成と、ここへのコピーは、この shell の前に各機器のパイプラインで行う。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FORCE=0
if [[ "${1:-}" == "all" || "${1:-}" == "--all" ]]; then
  FORCE=1
  shift
fi
BUNDLE_DIR="${1:-bc_mmo_pwi}"
BUNDLE_DIR="${BUNDLE_DIR%/}"
BUNDLE_NAME="${BUNDLE_NAME:-${BUNDLE_DIR##*/}}"

# Share one report directory and one time stamp among all steps of this run.
# "export" is needed: a child script cannot see a variable that is not exported.
# 今回の実行の全手順で、レポートの保存先と日時をそろえる。
# 子 shell は export されていない変数を見られないため、export が必要。
export REPORT_DIR="${REPORT_DIR:-./pds_chk_log}"
export REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
# Python that has miopds_common installed. It differs between servers
# (python3 or python, venv path): set PYTHON for each server (../README.md).
# Exported so that the child scripts use the same Python.
# miopds_common をインストールした Python。サーバーごとに異なるので
# （python3 か python か、venv の場所）、サーバーごとに PYTHON を指定する（../README.md）。
# 子 shell も同じ Python を使うよう export する。
export PYTHON="${PYTHON:-python3}"

TEMPLATES_DIR="${TEMPLATES_DIR:-$SCRIPT_DIR/../templates}"
CONFIG_DIR="${CONFIG_DIR:-$SCRIPT_DIR/../config}"

# Output names must match the child scripts' settings / 子 shell の設定と同じ名前にする
PDF_FILE="${PDF_FILE:-bc_mmo_pwi_data_user_guide.pdf}"
export DOCUMENT_OUTPUT="${DOCUMENT_OUTPUT:-bc_mmo_pwi_data_user_guide.lblx}"
export COLLECTION_OUTPUT="${COLLECTION_OUTPUT:-collection_bc_mmo_pwi_document.lblx}"
export OUTPUT_FILE="${OUTPUT_FILE:-${BUNDLE_NAME}.lblx}"


# -- Per-CDF label options (edit for each instrument) ----------------------------
# -- CDF ごとのラベルのオプション（機器ごとに編集する） ------------------------------
# Fill LABEL_ARGS with extra options for miopds_common cdf2pdslabel, e.g. the
# mission phase or internal references derived from the file name.
# cdf2pdslabel に渡す追加のオプションを LABEL_ARGS に入れる
# （ミッションフェーズや、ファイル名から作る internal reference など）。
set_label_args() {
  local cdf="$1"
  LABEL_ARGS=()
  # Example / 例:
  # LABEL_ARGS+=(--mission-phase-name Cruise --mission-phase-id cruise)
  # LABEL_ARGS+=(--internal-reference "urn:jaxa:darts:bc_mmo_pwi:document:pwi_data_user_guide::1.0|data_to_document")
  : "$cdf"  # Unused until the examples above are enabled / 上の例を使うまでは未使用
}


# -- Helpers / 補助関数 ------------------------------------------------------------

# needs_update OUTPUT INPUT... : true when OUTPUT must be (re)built.
# A directory INPUT counts when anything in it (a file or a folder) is newer,
# so files added or removed there also count. The miopds_common code (*.py)
# is always an input.
# OUTPUT を作り直す必要があれば真。INPUT がディレクトリなら、その中のファイルや
# フォルダのどれかが新しければ真（追加・削除もこれで検出する）。
# miopds_common のコード（*.py）は常に入力に含める。
# find -newer compares below one second; bash 3.2's -nt compares whole seconds.
# find -newer は1秒未満まで比べる（bash 3.2 の -nt は秒単位でしか比べない）。
needs_update() {
  local output="$1" input
  shift
  (( FORCE )) && return 0
  [[ -e "$output" ]] || return 0
  for input in "$@"; do
    [[ -e "$input" ]] || continue
    [[ -z "$(find "$input" -name __pycache__ -prune -o -newer "$output" -print | head -n 1)" ]] || return 0
  done
  [[ -z "$(find "$PACKAGE_DIR" -name '*.py' -newer "$output" -print | head -n 1)" ]] || return 0
  return 1
}

# Lock: only one run per bundle at a time (mkdir is atomic; flock is not on macOS).
# Set LOCK_DIR to a fixed place when cron and manual runs may differ in TMPDIR.
# ロック：同じ Bundle に対しては同時に1つだけ実行する（mkdir は不可分。flock は macOS にない）。
# cron と手動の実行で TMPDIR が異なりうる場合は、LOCK_DIR で固定の場所を指定する。
LOCK_DIR="${LOCK_DIR:-${TMPDIR:-/tmp}/miopds_cron_mk_cdf_to_pds_${BUNDLE_NAME}.lock}"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Already running for $BUNDLE_NAME (lock: $LOCK_DIR)" >&2
  echo "If no other run is active, remove the lock: rmdir $LOCK_DIR" >&2
  exit 9
fi
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/miopds_cron_mk_cdf_to_pds.XXXXXX")"
trap 'rmdir "$LOCK_DIR"; rm -rf "$WORK_DIR"' EXIT

date
[[ -d "$BUNDLE_DIR" ]] || {
  echo "ERROR: Bundle directory not found: $BUNDLE_DIR" >&2
  exit 1
}
"$PYTHON" -c 'import miopds_common' 2>/dev/null || {
  echo "ERROR: miopds_common is not installed for $PYTHON" >&2
  echo "       Activate the venv, or set PYTHON=/path/to/python" >&2
  exit 1
}
(( FORCE )) && echo "Rebuilding everything (all)."

# Where miopds_common is installed: a code change rebuilds the products.
# miopds_common のインストール先。コードが変われば作り直す。
PACKAGE_DIR="$("$PYTHON" -c 'import miopds_common, os; print(os.path.dirname(os.path.abspath(miopds_common.__file__)))')"

# Inputs shared by every product / すべての製品に共通の入力
COMMON_INPUTS=("$TEMPLATES_DIR" "$CONFIG_DIR" "$SCRIPT_DIR")


# -- Steps 1-2: one data collection / 手順1-2：データの Collection 1つ分 ------------
# Usage: make_data_collection COLLECTION_NAME DATASET_CONFIG
make_data_collection() {
  local name="$1"
  local dataset_config="$2"
  local collection_dir="$BUNDLE_DIR/$name"
  local science_dir="$collection_dir/science"
  local collection_label="$collection_dir/$name.lblx"
  local cdf label made=0 current=0 stale=0

  echo "===== [1] Labels: $science_dir"
  [[ -d "$science_dir" ]] || {
    echo "ERROR: directory not found: $science_dir" >&2
    return 1
  }
  find "$science_dir" -type f \( -name '*.cdf' -o -name '*.CDF' \) | sort > "$WORK_DIR/cdf_files.txt"
  [[ -s "$WORK_DIR/cdf_files.txt" ]] || {
    echo "ERROR: no CDF file below $science_dir" >&2
    return 1
  }

  while IFS= read -r cdf; do
    label="${cdf%.*}.lblx"
    if needs_update "$label" "$cdf" "$dataset_config" "${COMMON_INPUTS[@]}"; then
      set_label_args "$cdf"
      # stdin from /dev/null: the loop reads the CDF list from stdin
      # 標準入力は /dev/null（繰り返しが標準入力から CDF の一覧を読んでいるため）
      DATASET_CONFIG="$dataset_config" \
        "$SCRIPT_DIR/make_pds_label_for_mmo_cdf_data.sh" \
        "$cdf" "$TEMPLATES_DIR" "" "$(dirname "$cdf")" \
        ${LABEL_ARGS[@]+"${LABEL_ARGS[@]}"} < /dev/null
      made=$((made + 1))
    else
      current=$((current + 1))
    fi
  done < "$WORK_DIR/cdf_files.txt"

  # A label whose CDF is gone is only reported; the collection leaves it out.
  # CDF がなくなったラベルは報告するだけ（Collection はそれを除外する）。
  find "$science_dir" -type f -name '*.lblx' | sort > "$WORK_DIR/label_files.txt"
  while IFS= read -r label; do
    if [[ ! -e "${label%.lblx}.cdf" && ! -e "${label%.lblx}.CDF" ]]; then
      echo "WARNING: label without CDF (not removed): $label" >&2
      stale=$((stale + 1))
    fi
  done < "$WORK_DIR/label_files.txt"
  echo "Labels: $made made, $current up to date, $stale without CDF"

  echo "===== [2] Collection: $name"
  if needs_update "$collection_label" "$science_dir" "$dataset_config" "${COMMON_INPUTS[@]}"; then
    BUNDLE_NAME="$BUNDLE_NAME" DATASET_CONFIG="$dataset_config" \
      "$SCRIPT_DIR/create_psa_collection_jinja.sh" "$name" "$collection_dir"
  else
    echo "Collection is up to date: $collection_label"
  fi
  COLLECTION_LABELS+=("$collection_label")
}

COLLECTION_LABELS=()

# One line per data collection: name and its dataset config.
# データの Collection ごとに1行書く（名前と、その dataset の設定ファイル）。
make_data_collection data_calibrated_efd \
  "${DATASET_CONFIG:-$CONFIG_DIR/dataset_pwi_efd.json}"


# -- Step 3: documents / 手順3：Document ----------------------------------------------
DOCUMENT_DIR="$BUNDLE_DIR/document"
if [[ -d "$DOCUMENT_DIR" ]]; then
  echo "===== [3] Document: $DOCUMENT_DIR"
  # Both outputs are made together / 2つの出力は一緒に作られる
  if needs_update "$DOCUMENT_DIR/$DOCUMENT_OUTPUT" \
       "$DOCUMENT_DIR/$PDF_FILE" "${COMMON_INPUTS[@]}" ||
     needs_update "$DOCUMENT_DIR/$COLLECTION_OUTPUT" \
       "$DOCUMENT_DIR/$PDF_FILE" "${COMMON_INPUTS[@]}"; then
    PDF_FILE="$PDF_FILE" "$SCRIPT_DIR/create_psa_document_jinja.sh" "$DOCUMENT_DIR"
  else
    echo "Document is up to date: $DOCUMENT_DIR/$DOCUMENT_OUTPUT"
  fi
  COLLECTION_LABELS+=("$DOCUMENT_DIR/$COLLECTION_OUTPUT")
else
  echo "===== [3] Document: skipped ($DOCUMENT_DIR not found)"
fi


# -- Step 4: bundle / 手順4：Bundle -------------------------------------------------
echo "===== [4] Bundle: $BUNDLE_DIR"
if needs_update "$BUNDLE_DIR/$OUTPUT_FILE" "${COLLECTION_LABELS[@]}" "${COMMON_INPUTS[@]}"; then
  BUNDLE_NAME="$BUNDLE_NAME" "$SCRIPT_DIR/create_psa_bundle_jinja.sh" "$BUNDLE_DIR"
else
  echo "Bundle is up to date: $BUNDLE_DIR/$OUTPUT_FILE"
fi

echo "===== All steps finished. Reports: $REPORT_DIR (${REPORT_TIMESTAMP}_*)"
date
