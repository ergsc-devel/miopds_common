#!/usr/bin/env bash
#
# Update one Bundle: walk through the target files and rebuild only what is out
# of date (parent script).
# 1つの Bundle を更新する。対象ファイルを巡回し、古くなったものだけを作り直す（親 shell）。
#
#   For each settings file (one data Collection) / 設定ファイル（データの Collection）ごとに
#   1. a label for each CDF        make_pds_label_for_mmo_cdf_data.sh
#   2. the data collection         create_psa_collection_jinja.sh
#   Once, after all the Collections / すべての Collection の後に1回
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
#   cron_mk_cdf_to_pds.sh [all] [BUNDLE_DIR] [SETTINGS_FILE...]
#     all           : rebuild everything / すべて作り直す
#     SETTINGS_FILE : one settings file per data Collection of the Bundle (any
#                     names, any number). Without it: PIPELINE_SETTINGS, or
#                     ../user_config/pipeline_settings.sh.
#                     Bundle のデータの Collection ごとに1つの設定ファイル（名前も
#                     個数も自由）。指定がなければ PIPELINE_SETTINGS、それもなければ
#                     ../user_config/pipeline_settings.sh。
#
# Expected layout / 想定するディレクトリ構成:
#   BUNDLE_DIR/<collection>/**/*.cdf   data in any subdirectory (e.g.
#                                      <phase>/<data_type>/<YYYYMMDD_YYYYMMDD>/,
#                                      one directory per month);
#                                      labels are written beside the CDF
#                                      データ（サブディレクトリはどの構成でもよい。
#                                      例：<フェーズ>/<データの種類>/<月>/）。
#                                      ラベルは CDF の隣に作る
#   BUNDLE_DIR/document/*.pdf          documents (optional / なくてもよい)
#
# Creating the L2 CDF files and copying them here is done by each instrument's
# own pipeline before this script.
# L2 CDF の作成と、ここへのコピーは、この shell の前に各機器のパイプラインで行う。
#
# Each settings file holds the values of one data Collection and the values
# common to the Bundle, which must be the same in all the files (README.md).
# 設定ファイルには、1つのデータの Collection の値と、Bundle に共通の値を書く。
# Bundle に共通の値は、すべてのファイルで同じにする（README.md）。
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
(( $# == 0 )) || shift

# Settings files: one per data Collection (README.md)
# 設定ファイル：データの Collection ごとに1つ（README.md）
if (( $# > 0 )); then
  SETTINGS_FILES=("$@")
else
  SETTINGS_FILES=("${PIPELINE_SETTINGS:-$SCRIPT_DIR/../user_config/pipeline_settings.sh}")
fi
FIRST_SETTINGS="${SETTINGS_FILES[0]}"

# load_settings FILE : read one settings file and add the defaults of this script.
# Call it only in a subshell "( ... )". The values are written as
# VAR="${VAR:-value}", so a value left in the shell by one file would win over
# the next file. A subshell keeps the values of each file apart.
# 設定ファイルを1つ読み、この shell の既定値を補う。サブシェル「( ... )」の中でだけ
# 呼ぶ。値は VAR="${VAR:-値}" の形なので、前のファイルの値が shell に残っていると、
# 次のファイルより優先されてしまう。サブシェルを使えば、ファイルごとに値が分かれる。
load_settings() {
  PIPELINE_SETTINGS="$1"
  [[ -r "$PIPELINE_SETTINGS" ]] || {
    echo "ERROR: settings file is not readable: $PIPELINE_SETTINGS" >&2
    echo "       Copy user_config/pipeline_settings.sh, or set PIPELINE_SETTINGS" >&2
    exit 1
  }
  SETTINGS_DIR="$(cd "$(dirname "$PIPELINE_SETTINGS")" && pwd)"
  # Use the full path, and export it so that the scripts called for this
  # Collection read the same file
  # この Collection について呼ぶ shell も同じファイルを読むよう、絶対パスにして export する
  export PIPELINE_SETTINGS="$SETTINGS_DIR/${PIPELINE_SETTINGS##*/}"
  source "$PIPELINE_SETTINGS"

  PYTHON="${PYTHON:-python3}"
  BUNDLE_NAME="${BUNDLE_NAME:-${BUNDLE_DIR##*/}}"
  TEMPLATES_DIR="${TEMPLATES_DIR:-$SCRIPT_DIR/../label_templates}"
  MISSION_CONFIG="${MISSION_CONFIG:-$SCRIPT_DIR/../user_config/mission.json}"
  INSTRUMENT_CONFIG="${INSTRUMENT_CONFIG:-$SCRIPT_DIR/../user_config/instrument_pwi.json}"
  DATASET_CONFIG="${DATASET_CONFIG:-$SCRIPT_DIR/../user_config/dataset_pwi_efd.json}"

  # Output names must match the child scripts' settings / 子 shell の設定と同じ名前にする
  PDF_FILE="${PDF_FILE:-bc_mmo_pwi_data_user_guide.pdf}"
  export DOCUMENT_OUTPUT="${DOCUMENT_OUTPUT:-bc_mmo_pwi_data_user_guide.lblx}"
  export COLLECTION_OUTPUT="${COLLECTION_OUTPUT:-collection_bc_mmo_pwi_document.lblx}"
  export OUTPUT_FILE="${OUTPUT_FILE:-${BUNDLE_NAME}.lblx}"

  # Inputs shared by every product. Only the files that this settings file uses,
  # so that editing the file of another Collection does not rebuild this one.
  # すべての製品に共通の入力。この設定ファイルが使うものだけにする（ほかの Collection の
  # 設定ファイルを直しても、この Collection を作り直さないため）。
  COMMON_INPUTS=("$TEMPLATES_DIR" "$MISSION_CONFIG" "$PIPELINE_SETTINGS" "$SCRIPT_DIR")
}

# setting_value FILE NAME : print one value of a settings file.
# 設定ファイルの値を1つ表示する。
setting_value() {
  (
    load_settings "$1"
    printf '%s\n' "${!2:-}"
  )
}


# -- Check the settings files / 設定ファイルの確認 ------------------------------------
# A Bundle has one Bundle label and one Document, so these values must be the same
# in all the files. Which file they are read from then makes no difference.
# 1つの Bundle に Bundle のラベルと Document は1つなので、次の値はすべてのファイルで
# 同じにする。そうすれば、どのファイルから読んでも結果は変わらない。
BUNDLE_VALUES=(
  BUNDLE_NAME MISSION_CONFIG INSTRUMENT_CONFIG PDF_FILE DOCUMENT_OUTPUT
  COLLECTION_OUTPUT DOCUMENT_LID DOCUMENT_COLLECTION_LID TITLE DESCRIPTION
  DOCUMENT_MODIFICATION_DESCRIPTION COLLECTION_MODIFICATION_DESCRIPTION
)
COLLECTION_LABELS=()
SEEN_COLLECTIONS=" "
for settings in "${SETTINGS_FILES[@]}"; do
  collection="$(setting_value "$settings" COLLECTION_NAME)"
  [[ -n "$collection" ]] || {
    echo "ERROR: COLLECTION_NAME is not set in $settings" >&2
    exit 1
  }
  [[ "$SEEN_COLLECTIONS" != *" $collection "* ]] || {
    echo "ERROR: more than one settings file for the Collection $collection" >&2
    exit 1
  }
  SEEN_COLLECTIONS+="$collection "
  COLLECTION_LABELS+=("$BUNDLE_DIR/$collection/$collection.lblx")
  for name in "${BUNDLE_VALUES[@]}"; do
    [[ "$(setting_value "$settings" "$name")" == "$(setting_value "$FIRST_SETTINGS" "$name")" ]] || {
      echo "ERROR: $name differs between $FIRST_SETTINGS and $settings" >&2
      exit 1
    }
  done
done
RUN_BUNDLE_NAME="$(setting_value "$FIRST_SETTINGS" BUNDLE_NAME)"

# Share one report directory and one time stamp among all steps of this run.
# "export" is needed: a child script cannot see a variable that is not exported.
# 今回の実行の全手順で、レポートの保存先と日時をそろえる。
# 子 shell は export されていない変数を見られないため、export が必要。
export REPORT_DIR="${REPORT_DIR:-./pds_chk_log}"
export REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"
# Python that has miopds_common installed. It differs between servers
# (python3 or python, venv path): set PYTHON for each server (README.md).
# Exported so that the child scripts use the same Python: the one of the first file.
# miopds_common をインストールした Python。サーバーごとに異なるので
# （python3 か python か、venv の場所）、サーバーごとに PYTHON を指定する（README.md）。
# 子 shell も同じ Python（最初のファイルのもの）を使うよう export する。
PYTHON="$(setting_value "$FIRST_SETTINGS" PYTHON)"
export PYTHON


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
LOCK_DIR="${LOCK_DIR:-${TMPDIR:-/tmp}/miopds_cron_mk_cdf_to_pds_${RUN_BUNDLE_NAME}.lock}"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Already running for $RUN_BUNDLE_NAME (lock: $LOCK_DIR)" >&2
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


# -- Steps 1-2: one data collection / 手順1-2：データの Collection 1つ分 ------------
# Usage: make_data_collection COLLECTION_NAME DATASET_CONFIG
make_data_collection() {
  local name="$1"
  local dataset_config="$2"
  local collection_dir="$BUNDLE_DIR/$name"
  local collection_label="$collection_dir/$name.lblx"
  local cdf label made=0 current=0 stale=0

  # The CDF files may be in any subdirectory of the Collection
  # CDF は Collection の下のどのサブディレクトリにあってもよい
  echo "===== [1] Labels: $collection_dir"
  [[ -d "$collection_dir" ]] || {
    echo "ERROR: directory not found: $collection_dir" >&2
    return 1
  }
  find "$collection_dir" -type f \( -name '*.cdf' -o -name '*.CDF' \) | sort > "$WORK_DIR/cdf_files.txt"
  [[ -s "$WORK_DIR/cdf_files.txt" ]] || {
    echo "ERROR: no CDF file below $collection_dir" >&2
    return 1
  }

  while IFS= read -r cdf; do
    label="${cdf%.*}.lblx"
    # The timeline is an input only when it is given (needs_update skips "")
    # 期間表は指定したときだけ入力になる（needs_update は "" を飛ばす）
    if needs_update "$label" "$cdf" "$dataset_config" "${MISSION_TIMELINE:-}" \
         "${COMMON_INPUTS[@]}"; then
      # stdin from /dev/null: the loop reads the CDF list from stdin
      # 標準入力は /dev/null（繰り返しが標準入力から CDF の一覧を読んでいるため）
      DATASET_CONFIG="$dataset_config" \
        "$SCRIPT_DIR/make_pds_label_for_mmo_cdf_data.sh" \
        "$cdf" "$TEMPLATES_DIR" "" "$(dirname "$cdf")" < /dev/null
      made=$((made + 1))
    else
      current=$((current + 1))
    fi
  done < "$WORK_DIR/cdf_files.txt"

  # A label whose CDF is gone is only reported; the collection leaves it out.
  # -mindepth 2 skips the Collection label itself, which has no CDF.
  # CDF がなくなったラベルは報告するだけ（Collection はそれを除外する）。
  # -mindepth 2 で、CDF を持たない Collection のラベル自身を除く。
  find "$collection_dir" -mindepth 2 -type f -name '*.lblx' | sort > "$WORK_DIR/label_files.txt"
  while IFS= read -r label; do
    if [[ ! -e "${label%.lblx}.cdf" && ! -e "${label%.lblx}.CDF" ]]; then
      echo "WARNING: label without CDF (not removed): $label" >&2
      stale=$((stale + 1))
    fi
  done < "$WORK_DIR/label_files.txt"
  echo "Labels: $made made, $current up to date, $stale without CDF"

  echo "===== [2] Collection: $name"
  if needs_update "$collection_label" "$collection_dir" "$dataset_config" "${COMMON_INPUTS[@]}"; then
    # The child reads the Collection directory from COLLECTION_DIR
    # 子 shell は Collection のディレクトリを COLLECTION_DIR から読む
    BUNDLE_NAME="$BUNDLE_NAME" DATASET_CONFIG="$dataset_config" \
      COLLECTION_DIR="$collection_dir" \
      "$SCRIPT_DIR/create_psa_collection_jinja.sh" "$name"
  else
    echo "Collection is up to date: $collection_label"
  fi
}

# -- Steps 3-4: document and bundle / 手順3-4：Document と Bundle ----------------------
make_document_and_bundle() {
  local document_dir="$BUNDLE_DIR/document"
  if [[ -d "$document_dir" ]]; then
    echo "===== [3] Document: $document_dir"
    # Both outputs are made together / 2つの出力は一緒に作られる
    if needs_update "$document_dir/$DOCUMENT_OUTPUT" \
         "$document_dir/$PDF_FILE" "$INSTRUMENT_CONFIG" "${COMMON_INPUTS[@]}" ||
       needs_update "$document_dir/$COLLECTION_OUTPUT" \
         "$document_dir/$PDF_FILE" "$INSTRUMENT_CONFIG" "${COMMON_INPUTS[@]}"; then
      PDF_FILE="$PDF_FILE" "$SCRIPT_DIR/create_psa_document_jinja.sh" "$document_dir"
    else
      echo "Document is up to date: $document_dir/$DOCUMENT_OUTPUT"
    fi
    COLLECTION_LABELS+=("$document_dir/$COLLECTION_OUTPUT")
  else
    echo "===== [3] Document: skipped ($document_dir not found)"
  fi

  echo "===== [4] Bundle: $BUNDLE_DIR"
  if needs_update "$BUNDLE_DIR/$OUTPUT_FILE" "${COLLECTION_LABELS[@]}" \
       "$INSTRUMENT_CONFIG" "${COMMON_INPUTS[@]}"; then
    BUNDLE_NAME="$BUNDLE_NAME" "$SCRIPT_DIR/create_psa_bundle_jinja.sh" "$BUNDLE_DIR"
  else
    echo "Bundle is up to date: $BUNDLE_DIR/$OUTPUT_FILE"
  fi
}

# One data Collection for each settings file, in a subshell (see load_settings)
# 設定ファイルごとに、データの Collection を作る（サブシェルの理由は load_settings を参照）
for settings in "${SETTINGS_FILES[@]}"; do
  (
    load_settings "$settings"
    make_data_collection "$COLLECTION_NAME" "$DATASET_CONFIG"
  )
done

# The Document and the Bundle once, after all the Collections. The values are the
# same in all the files (checked above).
# Document と Bundle は、すべての Collection の後に1回だけ作る。値はすべてのファイルで
# 同じ（上で確かめた）。
(
  load_settings "$FIRST_SETTINGS"
  make_document_and_bundle
)

echo "===== All steps finished. Reports: $REPORT_DIR (${REPORT_TIMESTAMP}_*)"
date
