#!/usr/bin/env bash

# References to undefined variables, command failures, and failures in the middle of a pipeline are treated as errors.
#
# -e:
#   Terminate the script if the command returns a non-zero exit code.
#
# -u:
#   The script terminates if an undefined variable is referenced.
#
# -o pipefail:
#   If any command within the pipeline fails, the entire pipeline is treated as a failure.
#   
set -euo pipefail


# ============================================================
# Setting Up Scripts and Working Directories
# ============================================================

# Obtain the absolute path of the directory where this script itself is located.
# Used as the default search location for Jinja2 templates and Python renderers.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The first argument is used as the Documents directory.
# If the first argument is omitted, the `document` directory within the BepiColombo MMO PWI Bundle is used.
DOCUMENT_DIR="${1:-/var/www/html/data/chs/satellite/mmo/pds4/bc_mmo_pwi/document}"

# Remove the trailing slash from DOCUMENT_DIR if present.
# This prevents double slashes from appearing in the path during subsequent processing.
DOCUMENT_DIR="${DOCUMENT_DIR%/}"


# ============================================================
# Configuration of Jinja2 templates and Python renderer
# ============================================================

# This is a Jinja2 template for generating Product_Document XML.
# You can switch to a different template using the DOCUMENT_TEMPLATE environment variable.
DOCUMENT_TEMPLATE="${DOCUMENT_TEMPLATE:-$SCRIPT_DIR/document_template.xml.j2}"

# This is a Jinja2 template for generating Document Collection XML.
# You can switch to a different template using the COLLECTION_TEMPLATE environment variable.
COLLECTION_TEMPLATE="${COLLECTION_TEMPLATE:-$SCRIPT_DIR/document_collection_template.xml.j2}"

# This is a Python renderer that generates Product_Document, Document Collection XML, and Inventory CSV.
# You can switch to a different renderer using the RENDERER_FILE environment variable.
RENDERER_FILE="${RENDERER_FILE:-$SCRIPT_DIR/render_psa_document_set.py}"


# ============================================================
# PDS Validate Tool Configuration
# ============================================================

# Configure whether to execute validation using the PDS Validate Tool.
#
# 1:
#   Verification will be performed.
#
# 0:
#   Only XML and CSV generation will be performed; validation will be skipped.
VALIDATE_ENABLED="${VALIDATE_ENABLED:-1}"

# This is the executable file for the PDS Validate Tool.
# You can specify a different installation location using the VALIDATE_BIN environment variable.
VALIDATE_BIN="${VALIDATE_BIN:-$HOME/validate-4.0.8/bin/validate}"

# XML Catalogのパスです。
#
# 未定義の場合:
#   pds4-validate-catalog.xmlを使用します。
#
# 空文字列の場合:
#   XML Catalogを使用しません。
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"


# ============================================================
# Validationレポートの設定
# ============================================================

# Document製品とDocument CollectionのValidationレポートを
# 保存する共通ディレクトリです。
#
# ディレクトリが存在しない場合は、後続処理で自動作成します。
REPORT_DIR="${REPORT_DIR:-/home/miosc/mio-sc/work_local/tmp/pds_chk_log}"

# レポートファイル名へ付加する実行日時です。
# 同名レポートの上書きを避けるために使用します。
#
# 例:
#   20260909_135232
REPORT_TIMESTAMP="${REPORT_TIMESTAMP:-$(date '+%Y%m%d_%H%M%S')}"

# Product_DocumentラベルのValidationレポートです。
# DOCUMENT_REPORT環境変数で保存先を個別に変更できます。
DOCUMENT_REPORT="${DOCUMENT_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_bc_mmo_pwi_document_validate_report.txt}"

# Document CollectionラベルのValidationレポートです。
# COLLECTION_REPORT環境変数で保存先を個別に変更できます。
COLLECTION_REPORT="${COLLECTION_REPORT:-$REPORT_DIR/${REPORT_TIMESTAMP}_bc_mmo_pwi_document_collection_validate_report.txt}"


# ============================================================
# Product_DocumentおよびCollectionの識別情報
# ============================================================

# PWI Data User GuideのProduct_Document LIDです。
DOCUMENT_LID="${DOCUMENT_LID:-urn:jaxa:darts:bc_mmo_pwi:document:bc_mmo_pwi_data_user_guide}"

# PWI Document CollectionのLIDです。
COLLECTION_LID="${COLLECTION_LID:-urn:jaxa:darts:bc_mmo_pwi:document}"

# Product_DocumentとDocument Collectionで使用するVersion IDです。
VERSION_ID="${VERSION_ID:-1.0}"

# Data User Guideの文書タイトルです。
TITLE="${TITLE:-BepiColombo MMO Plasma Wave Investigation Data User Guide}"

# Citation_Informationへ設定する出版年です。
PUBLICATION_YEAR="${PUBLICATION_YEAR:-2027}"

# Documentクラスへ設定する出版日です。
# 現在は年だけを設定しています。
PUBLICATION_DATE="${PUBLICATION_DATE:-2027}"

# Modification_Historyへ設定する変更日です。
# 指定がない場合は、UTCでの実行日を使用します。
MODIFICATION_DATE="${MODIFICATION_DATE:-$(date -u +%F)}"

# Product_DocumentのCitation_Informationへ設定する説明です。
DESCRIPTION="${DESCRIPTION:-Data user guide for the BepiColombo Mercury Magnetospheric Orbiter Plasma Wave Investigation archive. The guide describes all level products, archive organization, data format, time and coordinate systems, calibration, processing, and quality information.}"


# ============================================================
# 入出力ファイル名
# ============================================================

# Product_Documentラベルが参照するPDF/Aファイル名です。
# このPDFはDOCUMENT_DIR内に存在する必要があります。
PDF_FILE="${PDF_FILE:-bc_mmo_pwi_data_user_guide.pdf}"

# 生成するProduct_Document XMLのファイル名です。
DOCUMENT_OUTPUT="${DOCUMENT_OUTPUT:-bc_mmo_pwi_data_user_guide.xml}"

# 生成するDocument Collection XMLのファイル名です。
COLLECTION_OUTPUT="${COLLECTION_OUTPUT:-collection_bc_mmo_pwi_document.xml}"

# 生成するDocument Collection Inventory CSVのファイル名です。
INVENTORY_OUTPUT="${INVENTORY_OUTPUT:-collection_bc_mmo_pwi_document.csv}"


# ============================================================
# 入力ディレクトリと必要ファイルの事前確認
# ============================================================

# Documentディレクトリが存在することを確認します。
[[ -d "$DOCUMENT_DIR" ]] || {
  echo "ERROR: Document directory not found: $DOCUMENT_DIR" >&2
  exit 1
}

# Product_Document用Jinja2テンプレートが存在することを確認します。
[[ -f "$DOCUMENT_TEMPLATE" ]] || {
  echo "ERROR: document template not found: $DOCUMENT_TEMPLATE" >&2
  exit 1
}

# Document Collection用Jinja2テンプレートが存在することを確認します。
[[ -f "$COLLECTION_TEMPLATE" ]] || {
  echo "ERROR: collection template not found: $COLLECTION_TEMPLATE" >&2
  exit 1
}

# Pythonレンダラーが存在することを確認します。
[[ -f "$RENDERER_FILE" ]] || {
  echo "ERROR: renderer not found: $RENDERER_FILE" >&2
  exit 1
}

# Product_Documentラベルから参照するPDFファイルが
# Documentディレクトリ内に存在することを確認します。
[[ -f "$DOCUMENT_DIR/$PDF_FILE" ]] || {
  echo "ERROR: PDF not found: $DOCUMENT_DIR/$PDF_FILE" >&2
  exit 1
}

# python3コマンドが利用できることを確認します。
command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 was not found." >&2
  exit 1
}

# PythonからJinja2モジュールを読み込めることを確認します。
python3 -c 'import jinja2' >/dev/null 2>&1 || {
  echo "ERROR: Jinja2 is required." >&2
  exit 1
}

# レポート保存ディレクトリを作成します。
#
# DOCUMENT_REPORTまたはCOLLECTION_REPORTで別ディレクトリが
# 指定された場合にも対応できるよう、それぞれの親ディレクトリも作成します。
mkdir -p \
  "$REPORT_DIR" \
  "$(dirname "$DOCUMENT_REPORT")" \
  "$(dirname "$COLLECTION_REPORT")"


# ============================================================
# Product_Document、Inventory CSV、Collection XMLの生成
# ============================================================

# Pythonレンダラーを実行します。
#
# レンダラーは次の3ファイルを生成します。
#
# 1. Product_Document XML
# 2. Document Collection Inventory CSV
# 3. Product_Collection XML
#
# Inventory CSVのファイルサイズ、MD5、レコード数は、
# Pythonレンダラー側で計算してCollection XMLへ設定します。
python3 "$RENDERER_FILE" "$DOCUMENT_DIR" \
  --document-template "$DOCUMENT_TEMPLATE" \
  --collection-template "$COLLECTION_TEMPLATE" \
  --document-lid "$DOCUMENT_LID" \
  --collection-lid "$COLLECTION_LID" \
  --version-id "$VERSION_ID" \
  --title "$TITLE" \
  --publication-year "$PUBLICATION_YEAR" \
  --publication-date "$PUBLICATION_DATE" \
  --description "$DESCRIPTION" \
  --modification-date "$MODIFICATION_DATE" \
  --document-modification-description \
    "Initial version of the PWI Data User Guide document label." \
  --collection-modification-description \
    "Initial version of the PWI document collection." \
  --pdf-file "$PDF_FILE" \
  --document-output "$DOCUMENT_OUTPUT" \
  --collection-output "$COLLECTION_OUTPUT" \
  --inventory-output "$INVENTORY_OUTPUT"


# ============================================================
# 生成ファイルの確認
# ============================================================

# 生成したProduct_Document XMLのフルパスを設定します。
DOCUMENT_XML="$DOCUMENT_DIR/$DOCUMENT_OUTPUT"

# 生成したDocument Collection XMLのフルパスを設定します。
COLLECTION_XML="$DOCUMENT_DIR/$COLLECTION_OUTPUT"

# Product_Document XMLが正常に生成されたことを確認します。
[[ -f "$DOCUMENT_XML" ]] || {
  echo "ERROR: document XML was not generated: $DOCUMENT_XML" >&2
  exit 1
}

# Document Collection XMLが正常に生成されたことを確認します。
[[ -f "$COLLECTION_XML" ]] || {
  echo "ERROR: collection XML was not generated: $COLLECTION_XML" >&2
  exit 1
}

# Document Collection Inventory CSVが正常に生成されたことを確認します。
[[ -f "$DOCUMENT_DIR/$INVENTORY_OUTPUT" ]] || {
  echo "ERROR: inventory CSV was not generated: $DOCUMENT_DIR/$INVENTORY_OUTPUT" >&2
  exit 1
}


# ============================================================
# Validationの実行可否確認
# ============================================================

# VALIDATE_ENABLED=0の場合は、生成処理だけで正常終了します。
if [[ "$VALIDATE_ENABLED" == "0" ]]; then
  echo "Validation skipped because VALIDATE_ENABLED=0."
  exit 0
fi

# Validate Toolが存在し、実行可能であることを確認します。
[[ -x "$VALIDATE_BIN" ]] || {
  echo "ERROR: Validate not executable: $VALIDATE_BIN" >&2
  exit 1
}


# ============================================================
# Validate Toolの共通引数
# ============================================================

# Product_Document検証とDocument Collection検証の両方で
# 使用する共通引数を配列として管理します。
VALIDATE_COMMON=()

# XML Catalogが指定され、ファイルも存在する場合は、
# Validate Toolへ--catalogオプションを追加します。
if [[ -n "$VALIDATE_CATALOG" && -f "$VALIDATE_CATALOG" ]]; then
  VALIDATE_COMMON+=(
    --catalog "$VALIDATE_CATALOG"
  )

  echo "Using XML catalog: $VALIDATE_CATALOG"

# XML Catalogのパスは指定されているものの、
# ファイルが存在しない場合は警告だけを表示します。
#
# この場合、CatalogなしでValidationを続行します。
elif [[ -n "$VALIDATE_CATALOG" ]]; then
  echo "WARNING: Catalog not found: $VALIDATE_CATALOG" >&2
  echo "WARNING: Validation will continue without --catalog." >&2

# VALIDATE_CATALOG=""が指定された場合です。
else
  echo "XML catalog is not specified."
  echo "Validation will continue without --catalog."
fi


# ============================================================
# Product_Documentラベルの検証
# ============================================================

echo "Validating Document product: $DOCUMENT_XML"
echo "Document validation report: $DOCUMENT_REPORT"

# Product_Documentラベルを単体検証します。
#
# 標準エラーを標準出力へ統合し、teeで画面表示と
# レポート保存を同時に行います。
#
# set -o pipefailが有効なため、Validate Toolが失敗した場合は
# パイプ全体が失敗となり、スクリプトも終了します。
"$VALIDATE_BIN" \
  --target "$DOCUMENT_XML" \
  "${VALIDATE_COMMON[@]}" \
  2>&1 | tee "$DOCUMENT_REPORT"


# ============================================================
# Document Collectionラベルの検証
# ============================================================

echo "Validating Document collection: $COLLECTION_XML"
echo "Collection validation report: $COLLECTION_REPORT"

# Document Collectionラベルを単体検証します。
#
# この検証では、Collection XMLの構造に加えて、
# Inventory CSVの存在、サイズ、MD5、レコード数なども確認されます。
"$VALIDATE_BIN" \
  --target "$COLLECTION_XML" \
  "${VALIDATE_COMMON[@]}" \
  2>&1 | tee "$COLLECTION_REPORT"


# ============================================================
# 正常終了メッセージ
# ============================================================

# 両方のValidate処理が正常終了した場合だけ、ここへ到達します。
echo "Document and Document Collection validation passed."
echo "Document report  : $DOCUMENT_REPORT"
echo "Collection report: $COLLECTION_REPORT"
