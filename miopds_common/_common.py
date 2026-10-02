"""Helpers shared by the miopds_common tools.
miopds_common の各ツールで共通に使う定数と補助関数。

The leading underscore marks this as an internal module: it is used by the
tools inside this package and is not part of the public API.
先頭の "_" は「パッケージ内部用のモジュール」という意味。外部から使う前提ではない。
"""

import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

# PDS4 common namespace URI / PDS4 共通辞書の名前空間 URI
PDS_NS = "http://pds.nasa.gov/pds4/pds/v1"

# Prefix map for ElementTree find()/findall(), e.g. root.find("pds:title", PDS_NSMAP)
# ElementTree の find()/findall() で使う接頭辞の対応表
PDS_NSMAP = {"pds": PDS_NS}


def make_jinja_env(template_dir: Path | str) -> Environment:
    """Create the Jinja2 environment used for every PDS4 label template.
    すべての PDS4 ラベル用テンプレートで共通に使う Jinja2 環境を作る。

    - StrictUndefined: a missing variable is an error, not an empty string.
      渡し忘れた変数を空文字にせず、エラーにする。
    - autoescape: characters such as "&" and "<" are escaped for XML.
      "&" や "<" を XML 用に自動で置き換える（壊れた XML を防ぐ）。
    - trim_blocks / lstrip_blocks: lines holding only {% ... %} leave no blank space.
      {% ... %} だけの行が、出力に空白や空行を残さないようにする。
    """
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        autoescape=True,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(template_path: Path | str, context: Mapping[str, Any]) -> str:
    """Render a Jinja2 template file with the given values and return the text.
    テンプレートファイルに値を埋め込み、結果の文字列を返す。
    """
    template_path = Path(template_path)
    env = make_jinja_env(template_path.parent)
    return env.get_template(template_path.name).render(**context)


def check_well_formed(xml_text: str, source: str = "") -> None:
    """Raise ValueError if the text is not well-formed XML.
    XML の文法（開始タグと終了タグの対応など）として正しくなければ ValueError を出す。

    This does not check PDS4 rules; use PDS Validate for that.
    PDS4 の規則に合っているかは確認しない（それは PDS Validate の役割）。
    """
    try:
        ET.fromstring(xml_text)
    except ET.ParseError as error:
        where = f" ({source})" if source else ""
        raise ValueError(f"Generated XML is not well-formed{where}: {error}") from error
