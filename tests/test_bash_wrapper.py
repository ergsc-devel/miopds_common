"""Tests for the shell scripts in bash_wrapper/ with a settings file.
設定ファイルを使った bash_wrapper/ の shell のテスト。

The scripts are run with bash on synthetic data, without being edited.
PDS Validate is not run (VALIDATE_ENABLED=0).
合成データで、shell を書き換えずに bash で動かす。PDS Validate は動かさない
（VALIDATE_ENABLED=0）。
"""

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from cdf_factory import TEST_CDF_NAME, make_test_cdf
from config_factory import filled_dataset

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "bash_wrapper"
CONFIG = ROOT / "user_config"
TEMPLATES = ROOT / "label_templates"
LABEL_TEMPLATE = "mmo_cdf_label_template_multi_dataset.xml.j2"
LABEL_NAME = TEST_CDF_NAME.replace(".cdf", ".lblx")

NS = {"pds": "http://pds.nasa.gov/pds4/pds/v1", "psa": "http://psa.esa.int/psa/v1"}

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")

# Settings of a test instrument; the files are in the settings directory
# テスト用の機器の設定。ファイルは設定ファイルと同じディレクトリに置く
BASE_SETTINGS = """\
MISSION_CONFIG="${MISSION_CONFIG:-$SETTINGS_DIR/mission.json}"
INSTRUMENT_CONFIG="${INSTRUMENT_CONFIG:-$SETTINGS_DIR/instrument_pwi.json}"
DATASET_CONFIG="${DATASET_CONFIG:-$SETTINGS_DIR/dataset.json}"
"""


def _settings(tmp_path: Path, text: str = "") -> Path:
    """Write a settings file of a test instrument and return its path.
    テスト用の機器の設定ファイルを書き、そのパスを返す。
    """
    directory = tmp_path / "instrument_config"
    directory.mkdir()
    shutil.copy(CONFIG / "mission.json", directory)
    shutil.copy(CONFIG / "instrument_pwi.json", directory)
    filled_dataset(directory)
    path = directory / "pipeline_settings.sh"
    path.write_text(BASE_SETTINGS + text, encoding="utf-8")
    return path


def _cdf(directory: Path) -> Path:
    directory.mkdir(parents=True)
    return make_test_cdf(directory)


def _run(
    tmp_path: Path, script: str, *args: str, **env: str
) -> subprocess.CompletedProcess:
    """Run a script of bash_wrapper/ in tmp_path with the given environment.
    bash_wrapper/ の shell を、指定した環境変数で tmp_path において実行する。
    """
    base = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "TMPDIR": os.environ.get("TMPDIR", str(tmp_path)),
        "PYTHON": sys.executable,
        "PYTHONPATH": str(ROOT),
        "VALIDATE_ENABLED": "0",
    }
    return subprocess.run(
        ["bash", str(WRAPPER / script), *args],
        cwd=tmp_path, env={**base, **env}, capture_output=True, text=True,
    )


def _findtext(label: Path, path: str) -> str:
    return ET.parse(label).getroot().findtext(path, namespaces=NS)


def test_missing_settings_file_is_an_error(tmp_path):
    result = _run(
        tmp_path, "make_pds_label_for_mmo_cdf_data.sh",
        str(_cdf(tmp_path / "cdf")), str(TEMPLATES), "", str(tmp_path),
        PIPELINE_SETTINGS=str(tmp_path / "no_such.sh"),
    )
    assert result.returncode == 1
    assert "settings file is not readable" in result.stderr


def test_environment_wins_over_the_sample_settings(tmp_path):
    # The sample dataset has REPLACE_ values, so the label is made only when
    # DATASET_CONFIG from the environment is used
    # 見本の dataset には REPLACE_ が残っているので、環境変数の DATASET_CONFIG が
    # 使われたときだけラベルができる
    result = _run(
        tmp_path, "make_pds_label_for_mmo_cdf_data.sh",
        str(_cdf(tmp_path / "cdf")), str(TEMPLATES), "", str(tmp_path),
        DATASET_CONFIG=str(filled_dataset(tmp_path)),
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / LABEL_NAME).exists()


def test_label_template_is_taken_from_settings(tmp_path):
    # Only the template named in the settings file is in TEMPLATES_DIR
    # TEMPLATES_DIR には、設定ファイルで指定した名前のテンプレートしかない
    templates = tmp_path / "templates"
    templates.mkdir()
    shutil.copy(TEMPLATES / LABEL_TEMPLATE, templates / "my_label.xml.j2")
    collection = tmp_path / "data_one"
    _cdf(collection / "sub")
    result = _run(
        tmp_path, "make_all_pds_label_for_collection.sh", str(collection),
        PIPELINE_SETTINGS=str(_settings(tmp_path, 'LABEL_TEMPLATE="my_label.xml.j2"')),
        TEMPLATES_DIR=str(templates),
    )
    assert result.returncode == 0, result.stderr
    assert (collection / "sub" / LABEL_NAME).exists()


def test_cron_makes_every_collection_in_settings(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    settings = _settings(
        tmp_path,
        'DATA_COLLECTIONS=("data_one|$DATASET_CONFIG" "data_two|$DATASET_CONFIG")\n',
    )
    result = _run(
        tmp_path, "cron_mk_cdf_to_pds.sh", str(bundle),
        PIPELINE_SETTINGS=str(settings), LOCK_DIR=str(tmp_path / "lock"),
    )
    assert result.returncode == 0, result.stderr
    assert (bundle / "data_one" / "data_one.lblx").exists()
    assert (bundle / "data_two" / "data_two.lblx").exists()


def test_cron_adds_label_args_from_settings(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    _cdf(bundle / "data_one" / "sub")
    settings = _settings(
        tmp_path,
        'DATA_COLLECTIONS=("data_one|$DATASET_CONFIG")\n'
        "set_label_args() {\n"
        "  LABEL_ARGS=(--mission-phase-name Cruise --mission-phase-id cruise)\n"
        "}\n",
    )
    result = _run(
        tmp_path, "cron_mk_cdf_to_pds.sh", str(bundle),
        PIPELINE_SETTINGS=str(settings), LOCK_DIR=str(tmp_path / "lock"),
    )
    assert result.returncode == 0, result.stderr
    label = bundle / "data_one" / "sub" / LABEL_NAME
    assert _findtext(label, ".//psa:Mission_Phase/psa:id") == "cruise"


def test_cron_rejects_a_collection_without_dataset_config(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    _cdf(bundle / "data_one" / "sub")
    result = _run(
        tmp_path, "cron_mk_cdf_to_pds.sh", str(bundle),
        PIPELINE_SETTINGS=str(_settings(tmp_path, 'DATA_COLLECTIONS=("data_one")\n')),
        LOCK_DIR=str(tmp_path / "lock"),
    )
    assert result.returncode == 1
    assert "not NAME|DATASET_CONFIG" in result.stderr


def test_document_collection_lid_is_taken_from_settings(tmp_path):
    document = tmp_path / "document"
    document.mkdir()
    (document / "guide.pdf").write_bytes(b"%PDF-1.4\n% dummy for tests\n")
    settings = _settings(
        tmp_path,
        'PDF_FILE="guide.pdf"\n'
        'DOCUMENT_OUTPUT="guide.lblx"\n'
        'COLLECTION_OUTPUT="collection_document.lblx"\n'
        'DOCUMENT_LID="urn:jaxa:darts:bc_mmo_test:document:guide"\n'
        'DOCUMENT_COLLECTION_LID="urn:jaxa:darts:bc_mmo_test:document"\n',
    )
    result = _run(
        tmp_path, "create_psa_document_jinja.sh", str(document),
        PIPELINE_SETTINGS=str(settings),
    )
    assert result.returncode == 0, result.stderr
    lid = _findtext(
        document / "collection_document.lblx",
        "pds:Identification_Area/pds:logical_identifier",
    )
    assert lid == "urn:jaxa:darts:bc_mmo_test:document"


def test_simple_example_writes_labels_in_another_directory(tmp_path):
    output = tmp_path / "labels"
    result = _run(
        tmp_path, "mio_examples/pwi_efd/make_pds_labels_simple.sh",
        str(_cdf(tmp_path / "cdf").parent), str(output),
        PIPELINE_SETTINGS=str(_settings(tmp_path)),
    )
    assert result.returncode == 0, result.stderr
    assert (output / LABEL_NAME).exists()
