#!/usr/bin/env bash
# A simple script for creating PDS4 labels from CDF files in a specified directory.
# The labels are written in another directory, not beside the CDF files.
# 指定したディレクトリの CDF ファイルから PDS4 ラベルを作る簡単な例。ラベルは
# CDF の隣ではなく、別のディレクトリに作る。
#
# Usage:
#   ./make_pds_labels_simple.sh CDF_DIRECTORY LABEL_OUTPUT_DIRECTORY
#
# Python, the config files, the timeline and the template are read from the
# settings file, as in the scripts in bash_wrapper/ (README.md).
# Python、設定ファイル、期間表、テンプレートは、bash_wrapper/ の shell と同じく
# 設定ファイルから読む（README.md）。

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 CDF_DIRECTORY LABEL_OUTPUT_DIRECTORY" >&2
    exit 1
fi

CDF_DIR="$1"
OUTPUT_DIR="$2"

# This script is in bash_wrapper/mio_examples/pwi_efd/
# この shell は bash_wrapper/mio_examples/pwi_efd/ にある
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Settings of the instrument: the same file as the scripts in bash_wrapper/.
# Environment variables given when running the script win over them.
# 機器の設定を読む（bash_wrapper/ の shell と同じファイル）。実行時に付けた
# 環境変数のほうが優先される。
PIPELINE_SETTINGS="${PIPELINE_SETTINGS:-$WRAPPER_DIR/../user_config/pipeline_settings.sh}"
[[ -r "$PIPELINE_SETTINGS" ]] || {
  echo "ERROR: settings file is not readable: $PIPELINE_SETTINGS" >&2
  echo "       Copy user_config/pipeline_settings.sh, or set PIPELINE_SETTINGS" >&2
  exit 1
}
SETTINGS_DIR="$(cd "$(dirname "$PIPELINE_SETTINGS")" && pwd)"
# Exported as a full path, so that the child script reads the same file
# 子 shell も同じファイルを読むよう、絶対パスにして export する
export PIPELINE_SETTINGS="$SETTINGS_DIR/${PIPELINE_SETTINGS##*/}"
source "$PIPELINE_SETTINGS"

LABEL_SCRIPT="$WRAPPER_DIR/make_pds_label_for_mmo_cdf_data.sh"
TEMPLATES_DIR="${TEMPLATES_DIR:-$WRAPPER_DIR/../label_templates}"

if [[ ! -d "$CDF_DIR" ]]; then
    echo "ERROR: CDF directory does not exist: $CDF_DIR" >&2
    exit 1
fi

if [[ ! -x "$LABEL_SCRIPT" ]]; then
    echo "ERROR: Label script is not executable: $LABEL_SCRIPT" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

found=0

while IFS= read -r -d '' cdf_file; do
    found=1
    echo "Processing: $cdf_file"

    # Template name "": LABEL_TEMPLATE of the settings file
    # テンプレートの名前 ""：設定ファイルの LABEL_TEMPLATE を使う
    if "$LABEL_SCRIPT" \
        "$cdf_file" \
        "$TEMPLATES_DIR" \
        "" \
        "$OUTPUT_DIR"
    then
        echo "Completed : $cdf_file"
    else
        echo "ERROR: Label generation failed: $cdf_file" >&2
    fi
done < <(find "$CDF_DIR" -type f -name '*.cdf' -print0 | sort -z)

if [[ $found -eq 0 ]]; then
    echo "No CDF files were found under: $CDF_DIR" >&2
    exit 1
fi

