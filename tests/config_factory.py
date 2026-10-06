"""Config files for tests, based on examples/config.
examples/config をもとにした、テスト用の設定ファイル。

The example dataset contains REPLACE_ placeholders, which are rejected when
loaded, so tests use a copy with the placeholders filled in.
見本の dataset には REPLACE_ のプレースホルダーがあり、読み込むとエラーになる。
そのため、テストではプレースホルダーを埋めたコピーを使う。
"""

import json
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "config"

FILLED_COLLECTION = {
    "collection_type": "Data",
    # "&" checks XML escaping / "&" で XML の置き換えを確かめる
    "title": "Test collection & more",
    "citation_description": "Citation text.",
    "collection_description": "Collection text.",
}


def dataset_dict() -> dict:
    """The example dataset with the collection texts filled in.
    Collection の文を埋めた、見本の dataset の中身。

    Relative paths are kept as in the example.
    相対パスは見本のまま。
    """
    data = json.loads((EXAMPLES / "dataset_pwi_efd.json").read_text(encoding="utf-8"))
    data["collection"] = dict(FILLED_COLLECTION)
    return data


def filled_dataset(directory: Path) -> Path:
    """Write a usable dataset config into directory and return its path.
    そのまま使える dataset の設定ファイルを directory に書き、そのパスを返す。

    The instrument and authors files point to examples/config.
    機器と著者のファイルは examples/config のものを指す。
    """
    data = dataset_dict()
    data["instrument_file"] = str(EXAMPLES / "instrument_pwi.json")
    data["authors_file"] = str(EXAMPLES / "authors_pwi_efd.json")
    path = Path(directory) / "dataset.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path
