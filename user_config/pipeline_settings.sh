# Settings of one data Collection for the shell scripts in bash_wrapper/ (PWI-EFD
# example). The scripts read this file with "source" when they start, so edit
# this file for the instrument instead of the scripts. Make one file per data
# Collection, e.g. by copying this file; any file name works (README.md).
# bash_wrapper/ の shell が読む、1つのデータの Collection の設定（PWI-EFD の例）。shell は
# 始めにこのファイルを source で読むので、shell ではなくこのファイルを機器に合わせて直す。
# データの Collection ごとに、このファイルをコピーして1つ作る。名前は自由（README.md）。
#
# Each value is written as VAR="${VAR:-value}", so an environment variable given
# when running a script wins over the value here.
# 各値は VAR="${VAR:-値}" の形なので、実行時に付けた環境変数のほうが優先される。
#
# SETTINGS_DIR is the directory of this file (the scripts set it).
# Do not write TEMPLATE_FILE, COLLECTION_LID or VERSION_ID here: several scripts
# use these names with different meanings.
# SETTINGS_DIR はこのファイルのあるディレクトリ（shell が設定する）。
# TEMPLATE_FILE、COLLECTION_LID、VERSION_ID はここに書かない（複数の shell が
# 別の意味で使う名前のため）。

# -- Python ---------------------------------------------------------------------
# Python that has miopds_common installed (e.g. ~/mio_pds_validate/bin/python)
# miopds_common をインストールした Python（例：~/mio_pds_validate/bin/python）
PYTHON="${PYTHON:-python3}"

# -- This data Collection / このデータの Collection ----------------------------------
# Name of the Collection. Its directory is BUNDLE_DIR/COLLECTION_NAME.
# Collection の名前。ディレクトリは BUNDLE_DIR/COLLECTION_NAME になる。
COLLECTION_NAME="${COLLECTION_NAME:-data_calibrated_efd}"
DATASET_CONFIG="${DATASET_CONFIG:-$SETTINGS_DIR/dataset_pwi_efd.json}"
# Name of the template file in label_templates/
# label_templates/ の中のテンプレートのファイル名
LABEL_TEMPLATE="${LABEL_TEMPLATE:-mmo_cdf_label_template_multi_dataset.xml.j2}"
# Timeline (optional; empty: the mission phase in mission.json)
# 期間表（任意。空なら mission.json のミッションフェーズを使う）
MISSION_TIMELINE="${MISSION_TIMELINE:-}"

# Extra options for cdf2pdslabel for each CDF file, used by
# make_pds_label_for_mmo_cdf_data.sh and the scripts that call it
# (e.g. the mission phase or internal references derived from the file name).
# $1 is the CDF file. Put the options in LABEL_ARGS.
# make_pds_label_for_mmo_cdf_data.sh と、それを呼ぶ shell が、CDF ごとに cdf2pdslabel
# に足すオプション（ミッションフェーズや、ファイル名から作る internal reference など）。
# $1 は CDF ファイル。オプションは LABEL_ARGS に入れる。
set_label_args() {
  LABEL_ARGS=()
  # Example / 例:
  # LABEL_ARGS+=(--mission-phase-name Cruise --mission-phase-id cruise)
  # LABEL_ARGS+=(--internal-reference "urn:jaxa:darts:bc_mmo_pwi:document:pwi_data_user_guide::1.0|data_to_document")
}

# -- Common to the Bundle / Bundle に共通 --------------------------------------------
# From here to the end of the Document values: write the same values in all the
# settings files of a Bundle. cron_mk_cdf_to_pds.sh stops if they differ.
# ここから Document の値の終わりまでは、同じ Bundle の設定ファイルすべてに同じ値を書く。
# 違っていると cron_mk_cdf_to_pds.sh は止まる。
BUNDLE_NAME="${BUNDLE_NAME:-bc_mmo_pwi}"
MISSION_CONFIG="${MISSION_CONFIG:-$SETTINGS_DIR/mission.json}"
INSTRUMENT_CONFIG="${INSTRUMENT_CONFIG:-$SETTINGS_DIR/instrument_pwi.json}"

# -- Document -------------------------------------------------------------------
# The PDF in BUNDLE_DIR/document/, and the names of the two labels made from it
# BUNDLE_DIR/document/ の PDF と、それから作る2つのラベルの名前
PDF_FILE="${PDF_FILE:-bc_mmo_pwi_data_user_guide.pdf}"
DOCUMENT_OUTPUT="${DOCUMENT_OUTPUT:-bc_mmo_pwi_data_user_guide.lblx}"
COLLECTION_OUTPUT="${COLLECTION_OUTPUT:-collection_bc_mmo_pwi_document.lblx}"
DOCUMENT_LID="${DOCUMENT_LID:-urn:jaxa:darts:bc_mmo_pwi:document:bc_mmo_pwi_data_user_guide}"
DOCUMENT_COLLECTION_LID="${DOCUMENT_COLLECTION_LID:-urn:jaxa:darts:bc_mmo_pwi:document}"
TITLE="${TITLE:-BepiColombo MMO Plasma Wave Investigation Data User Guide}"
DESCRIPTION="${DESCRIPTION:-Data user guide for the BepiColombo Mercury Magnetospheric Orbiter Plasma Wave Investigation archive. The guide describes all level products, archive organization, data format, time and coordinate systems, calibration, processing, and quality information.}"
DOCUMENT_MODIFICATION_DESCRIPTION="${DOCUMENT_MODIFICATION_DESCRIPTION:-Initial version of the PWI Data User Guide document label.}"
COLLECTION_MODIFICATION_DESCRIPTION="${COLLECTION_MODIFICATION_DESCRIPTION:-Initial version of the PWI document collection.}"

# -- PDS Validate ---------------------------------------------------------------
VALIDATE_BIN="${VALIDATE_BIN:-$HOME/local/pds/validate/bin/validate}"
# "": no catalog / 空ならカタログなし
VALIDATE_CATALOG="${VALIDATE_CATALOG-pds4-validate-catalog.xml}"
# More options for PDS Validate, e.g. "-D --add-context-products context.json"
# PDS Validate に足すオプション（例："-D --add-context-products context.json"）
VALIDATE_OPTION="${VALIDATE_OPTION:-}"
