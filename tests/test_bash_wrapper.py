"""Tests for the shell scripts in bash_wrapper/ with a settings file.
設定ファイルを使った bash_wrapper/ の shell のテスト。

The scripts are run with bash on synthetic data, without being edited.
PDS Validate is not run (VALIDATE_ENABLED=0).
合成データで、shell を書き換えずに bash で動かす。PDS Validate は動かさない
（VALIDATE_ENABLED=0）。
"""

import json
import os
import shutil
import subprocess
import sys
import time
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

PHASE_ID = ".//psa:Mission_Phase/psa:id"
LABEL_ARGS = (
    "set_label_args() {\n"
    "  LABEL_ARGS=(--mission-phase-name Test --mission-phase-id from_settings)\n"
    "}\n"
)


def _settings(
    tmp_path: Path, text: str = "", name: str = "pipeline_settings.sh"
) -> Path:
    """Write a settings file of a test instrument and return its path.
    テスト用の機器の設定ファイルを書き、そのパスを返す。
    """
    directory = tmp_path / "instrument_config"
    directory.mkdir(exist_ok=True)
    shutil.copy(CONFIG / "mission.json", directory)
    shutil.copy(CONFIG / "instrument_pwi.json", directory)
    filled_dataset(directory)
    path = directory / name
    path.write_text(BASE_SETTINGS + text, encoding="utf-8")
    return path


def _collection_settings(tmp_path: Path, collection: str, text: str = "") -> Path:
    """Write the settings file of one data Collection.
    1つのデータの Collection の設定ファイルを書く。
    """
    # The same form as the sample: a value left in the shell would win over it
    # 見本と同じ形：shell に値が残っていると、そちらが優先される
    value = f'COLLECTION_NAME="${{COLLECTION_NAME:-{collection}}}"\n'
    return _settings(tmp_path, value + text, f"{collection}.sh")


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


def _cron(tmp_path: Path, bundle: Path, *settings: Path) -> subprocess.CompletedProcess:
    """Run the cron script for one Bundle with the given settings files.
    指定した設定ファイルで、1つの Bundle について cron の shell を実行する。
    """
    return _run(
        tmp_path, "cron_mk_cdf_to_pds.sh", str(bundle), *map(str, settings),
        LOCK_DIR=str(tmp_path / "lock"),
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


def test_label_script_adds_label_args_from_settings(tmp_path):
    result = _run(
        tmp_path, "make_pds_label_for_mmo_cdf_data.sh",
        str(_cdf(tmp_path / "cdf")), str(TEMPLATES), "", str(tmp_path),
        PIPELINE_SETTINGS=str(_settings(tmp_path, LABEL_ARGS)),
    )
    assert result.returncode == 0, result.stderr
    assert _findtext(tmp_path / LABEL_NAME, PHASE_ID) == "from_settings"


def test_label_args_receive_the_cdf_file(tmp_path):
    settings = _settings(
        tmp_path,
        "set_label_args() {\n"
        '  LABEL_ARGS=(--mission-phase-name Test --mission-phase-id "id_${1##*/}")\n'
        "}\n",
    )
    result = _run(
        tmp_path, "make_pds_label_for_mmo_cdf_data.sh",
        str(_cdf(tmp_path / "cdf")), str(TEMPLATES), "", str(tmp_path),
        PIPELINE_SETTINGS=str(settings),
    )
    assert result.returncode == 0, result.stderr
    assert _findtext(tmp_path / LABEL_NAME, PHASE_ID) == f"id_{TEST_CDF_NAME}"


def test_options_on_the_command_line_win_over_label_args(tmp_path):
    result = _run(
        tmp_path, "make_pds_label_for_mmo_cdf_data.sh",
        str(_cdf(tmp_path / "cdf")), str(TEMPLATES), "", str(tmp_path),
        "--mission-phase-name", "Command", "--mission-phase-id", "from_command",
        PIPELINE_SETTINGS=str(_settings(tmp_path, LABEL_ARGS)),
    )
    assert result.returncode == 0, result.stderr
    assert _findtext(tmp_path / LABEL_NAME, PHASE_ID) == "from_command"


def test_internal_references_of_both_sources_are_in_the_label(tmp_path):
    settings = _settings(
        tmp_path,
        "set_label_args() {\n"
        "  LABEL_ARGS=(--internal-reference "
        '"urn:jaxa:darts:test:one::1.0|data_to_document")\n'
        "}\n",
    )
    result = _run(
        tmp_path, "make_pds_label_for_mmo_cdf_data.sh",
        str(_cdf(tmp_path / "cdf")), str(TEMPLATES), "", str(tmp_path),
        "--internal-reference", "urn:jaxa:darts:test:two::1.0|data_to_document",
        PIPELINE_SETTINGS=str(settings),
    )
    assert result.returncode == 0, result.stderr
    label = (tmp_path / LABEL_NAME).read_text(encoding="utf-8")
    assert "urn:jaxa:darts:test:one::1.0" in label
    assert "urn:jaxa:darts:test:two::1.0" in label


def test_make_all_adds_label_args_from_settings(tmp_path):
    collection = tmp_path / "data_one"
    _cdf(collection / "sub")
    result = _run(
        tmp_path, "make_all_pds_label_for_collection.sh", str(collection),
        PIPELINE_SETTINGS=str(_settings(tmp_path, LABEL_ARGS)),
    )
    assert result.returncode == 0, result.stderr
    label = collection / "sub" / LABEL_NAME
    assert _findtext(label, PHASE_ID) == "from_settings"


def test_simple_example_adds_label_args_from_settings(tmp_path):
    output = tmp_path / "labels"
    result = _run(
        tmp_path, "mio_examples/pwi_efd/make_pds_labels_simple.sh",
        str(_cdf(tmp_path / "cdf").parent), str(output),
        PIPELINE_SETTINGS=str(_settings(tmp_path, LABEL_ARGS)),
    )
    assert result.returncode == 0, result.stderr
    assert _findtext(output / LABEL_NAME, PHASE_ID) == "from_settings"


def test_cron_makes_a_collection_for_each_settings_file(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    result = _cron(
        tmp_path, bundle,
        _collection_settings(tmp_path, "data_one"),
        _collection_settings(tmp_path, "data_two"),
    )
    assert result.returncode == 0, result.stderr
    assert (bundle / "data_one" / "data_one.lblx").exists()
    assert (bundle / "data_two" / "data_two.lblx").exists()


def test_cron_makes_the_bundle_once_with_all_collections(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    result = _cron(
        tmp_path, bundle,
        _collection_settings(tmp_path, "data_one"),
        _collection_settings(tmp_path, "data_two"),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("===== [4] Bundle") == 1
    bundle_label = (bundle / "bc_mmo_test.lblx").read_text(encoding="utf-8")
    assert "data_one" in bundle_label
    assert "data_two" in bundle_label


def test_cron_uses_the_dataset_config_of_each_settings_file(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    one = _settings(tmp_path, 'COLLECTION_NAME="data_one"\n', "data_one.sh")
    two = _settings(tmp_path, 'COLLECTION_NAME="data_two"\n', "data_two.sh")
    # Only the file name differs, in the form DATASET_CONFIG="${DATASET_CONFIG:-...}"
    # DATASET_CONFIG="${DATASET_CONFIG:-...}" の形のまま、ファイル名だけを変える
    two.write_text(
        two.read_text(encoding="utf-8").replace("dataset.json", "dataset_two.json"),
        encoding="utf-8",
    )
    data = json.loads((one.parent / "dataset.json").read_text(encoding="utf-8"))
    data["collection"]["title"] = "Title of data_two"
    (one.parent / "dataset_two.json").write_text(json.dumps(data), encoding="utf-8")
    result = _cron(tmp_path, bundle, one, two)
    assert result.returncode == 0, result.stderr
    title = "pds:Identification_Area/pds:title"
    label_one = bundle / "data_one" / "data_one.lblx"
    label_two = bundle / "data_two" / "data_two.lblx"
    assert _findtext(label_one, title) != "Title of data_two"
    assert _findtext(label_two, title) == "Title of data_two"


def test_cron_uses_the_label_template_of_each_settings_file(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    source = (TEMPLATES / LABEL_TEMPLATE).read_text(encoding="utf-8")
    for name in ("one", "two"):
        (templates / f"{name}.xml.j2").write_text(
            f"{source}\n<!-- template {name} -->\n", encoding="utf-8"
        )
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    result = _run(
        tmp_path, "cron_mk_cdf_to_pds.sh", str(bundle),
        str(_collection_settings(
            tmp_path, "data_one", 'LABEL_TEMPLATE="${LABEL_TEMPLATE:-one.xml.j2}"\n'
        )),
        str(_collection_settings(
            tmp_path, "data_two", 'LABEL_TEMPLATE="${LABEL_TEMPLATE:-two.xml.j2}"\n'
        )),
        LOCK_DIR=str(tmp_path / "lock"), TEMPLATES_DIR=str(templates),
    )
    assert result.returncode == 0, result.stderr
    for collection, marker in (("data_one", "one"), ("data_two", "two")):
        label = (bundle / collection / "sub" / LABEL_NAME).read_text(encoding="utf-8")
        assert f"<!-- template {marker} -->" in label


def test_cron_uses_set_label_args_only_for_the_file_that_defines_it(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    result = _cron(
        tmp_path, bundle,
        _collection_settings(
            tmp_path, "data_one",
            "set_label_args() {\n"
            "  LABEL_ARGS=(--mission-phase-name Test --mission-phase-id only_one)\n"
            "}\n",
        ),
        _collection_settings(tmp_path, "data_two"),
    )
    assert result.returncode == 0, result.stderr
    phase = ".//psa:Mission_Phase/psa:id"
    assert _findtext(bundle / "data_one" / "sub" / LABEL_NAME, phase) == "only_one"
    assert _findtext(bundle / "data_two" / "sub" / LABEL_NAME, phase) != "only_one"


def test_cron_adds_label_args_from_settings(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    _cdf(bundle / "data_one" / "sub")
    settings = _settings(
        tmp_path,
        'COLLECTION_NAME="data_one"\n'
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


def test_cron_rejects_a_settings_file_without_collection_name(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    _cdf(bundle / "data_one" / "sub")
    result = _cron(tmp_path, bundle, _settings(tmp_path))
    assert result.returncode == 1
    assert "COLLECTION_NAME is not set" in result.stderr


def test_cron_rejects_two_settings_files_for_one_collection(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    _cdf(bundle / "data_one" / "sub")
    result = _cron(
        tmp_path, bundle,
        _settings(tmp_path, 'COLLECTION_NAME="data_one"\n', "copy_one.sh"),
        _settings(tmp_path, 'COLLECTION_NAME="data_one"\n', "copy_two.sh"),
    )
    assert result.returncode == 1
    assert "more than one settings file" in result.stderr


def test_cron_rejects_different_bundle_values_before_making_anything(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    result = _cron(
        tmp_path, bundle,
        _collection_settings(tmp_path, "data_one", 'TITLE="Guide one"\n'),
        _collection_settings(tmp_path, "data_two", 'TITLE="Guide two"\n'),
    )
    assert result.returncode == 1
    assert "TITLE differs" in result.stderr
    assert not (bundle / "data_one" / "sub" / LABEL_NAME).exists()


def test_settings_files_can_share_values_from_another_file(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    shared = 'source "$SETTINGS_DIR/shared.sh"\n'
    settings = [
        _collection_settings(tmp_path, name, shared)
        for name in ("data_one", "data_two")
    ]
    (settings[0].parent / "shared.sh").write_text(
        'TITLE="${TITLE:-Common guide}"\n', encoding="utf-8"
    )
    result = _cron(tmp_path, bundle, *settings)
    assert result.returncode == 0, result.stderr


def test_editing_a_settings_file_keeps_the_other_collection(tmp_path):
    bundle = tmp_path / "bc_mmo_test"
    for name in ("data_one", "data_two"):
        _cdf(bundle / name / "sub")
    settings = [
        _collection_settings(tmp_path, name) for name in ("data_one", "data_two")
    ]
    assert _cron(tmp_path, bundle, *settings).returncode == 0
    # A time in the future: newer than every product of the first run
    # 未来の時刻：1回目の実行で作ったどの製品よりも新しい
    later = time.time() + 60
    os.utime(settings[0], (later, later))
    result = _cron(tmp_path, bundle, *settings)
    assert result.returncode == 0, result.stderr
    made = [line for line in result.stdout.splitlines() if line.startswith("Labels:")]
    assert made[0].startswith("Labels: 1 made")
    assert made[1].startswith("Labels: 0 made, 1 up to date")


def test_collection_name_is_taken_from_settings(tmp_path):
    collection = tmp_path / "data_one"
    _cdf(collection / "sub")
    settings = str(_settings(tmp_path, 'COLLECTION_NAME="data_one"\n'))
    made = _run(
        tmp_path, "make_all_pds_label_for_collection.sh", str(collection),
        PIPELINE_SETTINGS=settings,
    )
    assert made.returncode == 0, made.stderr
    result = _run(
        tmp_path, "create_psa_collection_jinja.sh",
        PIPELINE_SETTINGS=settings, COLLECTION_DIR=str(collection),
    )
    assert result.returncode == 0, result.stderr
    assert (collection / "data_one.lblx").exists()


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
