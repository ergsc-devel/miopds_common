"""Build a PDS4 Collection (label + inventory CSV) from product labels.
製品のラベル群から、PDS4 の Collection（ラベル＋インベントリ CSV）を作る。
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from miopds_common._common import PDS_NS, PDS_NSMAP, check_well_formed, make_jinja_env
from miopds_common._config import (
    DatasetConfig,
    InstrumentConfig,
    MissionConfig,
    as_config,
)
from miopds_common.filetool import md5_of_bytes

logger = logging.getLogger(__name__)

_LID_PATH = "./pds:Identification_Area/pds:logical_identifier"
_VID_PATH = "./pds:Identification_Area/pds:version_id"


@dataclass(frozen=True)
class _MemberRule:
    """How member labels are found / メンバーになるラベルの探し方。"""

    patterns: tuple[str, ...]
    # Required root element, or None for any / 必要な根要素（None なら問わない）
    product_tag: str | None
    # Root elements that are never members / メンバーにしない根要素
    excluded_tags: frozenset[str]
    # Where the files of a product are named / 製品のファイル名が書かれた場所
    file_path: str
    # Only files with this suffix must exist, or None for all
    # この拡張子のファイルだけ存在を確認する（None ならすべて）
    file_suffix: str | None
    missing_word: str
    empty_message: str


# Collection and Bundle labels are .lblx too, so they are excluded.
# Collection と Bundle のラベルも .lblx なので、メンバーから除く。
_NOT_MEMBERS = frozenset(
    {f"{{{PDS_NS}}}Product_Collection", f"{{{PDS_NS}}}Product_Bundle"}
)

# Observational data: .lblx labels whose CDF files exist (original behaviour)
# 観測データ：CDF ファイルが存在する .lblx ラベル（元の動きのまま）
_DATA_RULE = _MemberRule(
    patterns=("*.lblx", "*.LBLX"),
    product_tag=None,
    excluded_tags=_NOT_MEMBERS,
    file_path=".//pds:File/pds:file_name",
    file_suffix=".cdf",
    missing_word="CDF",
    empty_message="No eligible .lblx labels with available CDF files were found",
)

# Documents: Product_Document labels whose document files exist.
# 文書：文書ファイルが存在する Product_Document ラベル。
_DOCUMENT_RULE = _MemberRule(
    patterns=("*.lblx", "*.LBLX", "*.xml", "*.XML"),
    product_tag=f"{{{PDS_NS}}}Product_Document",
    excluded_tags=_NOT_MEMBERS,
    file_path=".//pds:Document_File/pds:file_name",
    file_suffix=None,
    missing_word="file",
    empty_message="No eligible Product_Document labels were found",
)


@dataclass(frozen=True)
class CollectionResult:
    """What CollectionBuilder.write() produced.
    CollectionBuilder.write() が作ったものの一覧。
    """

    label_path: Path
    inventory_path: Path
    # None when no skip report was requested / スキップ一覧を指定しなかった場合は None
    skip_report_path: Path | None
    labels_found: int
    members: int
    # Labels excluded because their files are missing / ファイルがなく除外したラベル
    skipped: list[tuple[Path, list[Path]]]


class CollectionBuilder:
    """Generate a PDS4 Collection from the product labels in a directory.
    ディレクトリ内の製品ラベルから PDS4 の Collection を作る。

    - CollectionBuilder(...): data collection from .lblx labels; a label is a
      member only when every CDF it references exists beside it.
      データの Collection。参照する CDF がすべてラベルの隣にある .lblx だけをメンバーにする。
    - CollectionBuilder.for_documents(...): document collection from
      Product_Document labels (*.lblx or *.xml).
      Document Collection。Product_Document のラベル（*.lblx か *.xml）をメンバーにする。

    Members whose LID starts with "<collection_lid>:" are primary (P),
    the others secondary (S).
    LID が "<collection_lid>:" で始まるメンバーは primary（P）、それ以外は secondary（S）。
    """

    def __init__(
        self,
        template: Path | str,
        mission: MissionConfig | Path | str,
        dataset: DatasetConfig | Path | str,
        *,
        collection_lid: str,
        publication_year: int,
        version_id: str = "1.0",
        modification_date: date | str | None = None,
        modification_description: str = "Initial version",
    ) -> None:
        text = as_config(DatasetConfig, dataset).collection
        self._setup(
            template,
            mission,
            rule=_DATA_RULE,
            collection_type=text.collection_type,
            title=text.title,
            citation_description=text.citation_description,
            collection_description=text.collection_description,
            instrument_name=None,
            collection_lid=collection_lid,
            publication_year=publication_year,
            version_id=version_id,
            modification_date=modification_date,
            modification_description=modification_description,
        )

    @classmethod
    def for_documents(
        cls,
        template: Path | str,
        mission: MissionConfig | Path | str,
        instrument: InstrumentConfig | Path | str,
        *,
        collection_lid: str,
        publication_year: int,
        version_id: str = "1.0",
        modification_date: date | str | None = None,
        modification_description: str = "Initial version",
    ) -> "CollectionBuilder":
        """Create a builder for the document collection of one instrument.
        1つの機器の Document Collection を作るための builder を作る。

        Texts come from document_collection in instrument_*.json.
        文は instrument_*.json の document_collection から読む。
        """
        instrument = as_config(InstrumentConfig, instrument)
        text = instrument.document_collection
        builder = cls.__new__(cls)
        builder._setup(
            template,
            mission,
            rule=_DOCUMENT_RULE,
            collection_type="Document",
            title=text.title,
            citation_description=text.citation_description,
            collection_description=text.collection_description,
            instrument_name=instrument.instrument.name,
            collection_lid=collection_lid,
            publication_year=publication_year,
            version_id=version_id,
            modification_date=modification_date,
            modification_description=modification_description,
        )
        return builder

    def _setup(
        self, template, mission, *, rule, collection_lid, modification_date, **values
    ) -> None:
        # Shared by both constructors / 2つのコンストラクタで共通の初期化
        template = Path(template).resolve()
        if not template.is_file():
            raise FileNotFoundError(f"Template not found: {template}")
        if not collection_lid.strip():
            raise ValueError("Collection LID is empty")
        self.template_path = template
        self._template = make_jinja_env(template.parent).get_template(template.name)
        self.mission = as_config(MissionConfig, mission)
        self._rule = rule
        self.collection_lid = collection_lid.strip()
        # Today (UTC) unless given / 指定がなければ今日（UTC）
        if modification_date is None:
            modification_date = datetime.now(timezone.utc).date()
        self.modification_date = str(modification_date)
        self._values = values

    def write(
        self,
        label_dir: Path | str,
        output_dir: Path | str,
        output_base: str,
        *,
        skip_report: Path | str | None = None,
    ) -> CollectionResult:
        """Write <output_base>.lblx (label) and .csv (inventory) into output_dir.
        output_dir に <output_base>.lblx（ラベル）と .csv（インベントリ）を書き出す。

        Skipped labels are always logged as warnings. The list is also written
        to skip_report when it is given; keep it outside the archive.
        除外したラベルは毎回警告で知らせる。skip_report を指定した場合は、
        その一覧をファイルにも書く（アーカイブの外の場所を指定すること）。
        """
        label_dir = Path(label_dir).resolve()
        output_dir = Path(output_dir).resolve()
        output_base = output_base.strip()
        if not label_dir.is_dir():
            raise FileNotFoundError(f"Label directory not found: {label_dir}")
        if not output_base:
            raise ValueError("Output base is empty")

        labels, rows, skipped = self._scan(label_dir)
        if not rows:
            raise RuntimeError(self._rule.empty_message)

        inventory_path = output_dir / f"{output_base}.csv"
        label_path = output_dir / f"{output_base}.lblx"
        skip_path = None if skip_report is None else Path(skip_report).resolve()

        # PDS DSV inventory uses CRLF record delimiters, sorted by LID and VID.
        # PDS DSV のインベントリは CRLF 区切りで、LID と VID の順に並べる。
        inventory = "".join(
            f"{status},{lid}::{vid}\r\n"
            for status, lid, vid in sorted(rows, key=lambda row: (row[1], row[2]))
        ).encode("utf-8")
        context = self._context(inventory_path.name, inventory, len(rows))
        xml_text = self._template.render(**context)
        # Check before writing anything / 何かを書き出す前に確認する
        check_well_formed(xml_text, source=label_path.name)

        output_dir.mkdir(parents=True, exist_ok=True)
        inventory_path.write_bytes(inventory)
        label_path.write_text(xml_text, encoding="utf-8", newline="\n")
        if skip_path is not None:
            word = self._rule.missing_word
            skip_path.parent.mkdir(parents=True, exist_ok=True)
            with skip_path.open("w", encoding="utf-8", newline="\n") as stream:
                for label, missing_files in skipped:
                    stream.write(f"SKIP: {label}\n")
                    for missing_file in missing_files:
                        stream.write(f"  Missing {word}: {missing_file}\n")

        return CollectionResult(
            label_path=label_path,
            inventory_path=inventory_path,
            skip_report_path=skip_path,
            labels_found=len(labels),
            members=len(rows),
            skipped=skipped,
        )

    # -- internal ----------------------------------------------------------

    def _scan(self, label_dir: Path):
        """Find member labels / メンバーになるラベルを探す。"""
        rule = self._rule
        candidates = sorted(
            {path for pattern in rule.patterns for path in label_dir.rglob(pattern)}
        )
        labels: list[Path] = []
        rows: list[tuple[str, str, str]] = []
        skipped: list[tuple[Path, list[Path]]] = []
        for label in candidates:
            try:
                root = ET.parse(label).getroot()
            except ET.ParseError as error:
                # Counted as found, even if broken (original behaviour)
                # 壊れたものも「見つかったラベル」として数える（元の動きのまま）
                labels.append(label)
                logger.warning("malformed XML skipped: %s: %s", label, error)
                continue
            if root.tag in rule.excluded_tags or (
                rule.product_tag is not None and root.tag != rule.product_tag
            ):
                continue  # Not a member product type / メンバーの種類ではない
            labels.append(label)

            files = _referenced_files(label, root, rule)
            missing = [path for path in files if not path.is_file()]
            if missing:
                skipped.append((label, missing))
                logger.warning(
                    "missing %s; skipped: %s (%s)",
                    rule.missing_word, label, ", ".join(map(str, missing)),
                )
                continue

            lid = root.findtext(_LID_PATH, namespaces=PDS_NSMAP)
            vid = root.findtext(_VID_PATH, namespaces=PDS_NSMAP)
            if not lid or not vid:
                logger.warning("LID or VID missing; skipped: %s", label)
                continue

            status = "P" if lid.startswith(self.collection_lid + ":") else "S"
            rows.append((status, lid.strip(), vid.strip()))
        return labels, rows, skipped

    def _context(
        self, inventory_name: str, inventory: bytes, records: int
    ) -> dict[str, Any]:
        values = self._values
        investigation = self.mission.investigation
        context = {
            "collection_lid": self.collection_lid,
            "version_id": values["version_id"],
            "collection_title": values["title"],
            "information_model_version": self.mission.information_model_version,
            "publication_year": values["publication_year"],
            "citation_description": values["citation_description"],
            "collection_type": values["collection_type"],
            "collection_description": values["collection_description"],
            "modification_date": self.modification_date,
            "modification_description": values["modification_description"],
            "investigation_name": investigation.name,
            "investigation_type": investigation.type,
            "investigation_lid": investigation.lid,
            "inventory_file": inventory_name,
            "file_size": len(inventory),
            "md5_checksum": md5_of_bytes(inventory),
            "records": records,
        }
        if values["instrument_name"] is not None:
            context["instrument_name"] = values["instrument_name"]
        return context


def _referenced_files(label: Path, root: ET.Element, rule: _MemberRule) -> list[Path]:
    """Files named in the label, resolved beside the label.
    ラベルに書かれたファイル（ラベルと同じ場所にあるもの）。
    """
    files: list[Path] = []
    for element in root.findall(rule.file_path, PDS_NSMAP):
        if element.text:
            name = element.text.strip()
            if rule.file_suffix is None or name.lower().endswith(rule.file_suffix):
                files.append(label.parent / name)
    return files
