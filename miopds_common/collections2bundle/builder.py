"""Build a PDS4 Bundle label from the Collection labels below a directory.
ディレクトリ以下の Collection ラベルから、PDS4 の Bundle ラベルを作る。
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from miopds_common._common import PDS_NS, PDS_NSMAP, check_well_formed, make_jinja_env
from miopds_common._config import InstrumentConfig, MissionConfig, as_config

_COLLECTION_TAG = f"{{{PDS_NS}}}Product_Collection"
_LID_PATH = "./pds:Identification_Area/pds:logical_identifier"
_TYPE_PATH = "./pds:Collection/pds:collection_type"


@dataclass(frozen=True)
class BundleMember:
    """One Bundle_Member_Entry / Bundle_Member_Entry 1つ分。"""

    lid: str
    member_status: str
    # Lower case, used as bundle_has_<type>_collection / 小文字。参照の種類名に使う
    collection_type: str
    source_label: Path


@dataclass(frozen=True)
class BundleResult:
    """What BundleBuilder.write() produced / BundleBuilder.write() が作ったもの。"""

    label_path: Path
    members: list[BundleMember]


class BundleBuilder:
    """Generate the PDS4 Bundle label of one instrument.
    1つの機器の PDS4 Bundle ラベルを作る。

    Every Product_Collection label (*.lblx) below the bundle directory becomes a
    primary member. A LID that appears twice is used only once.
    Bundle ディレクトリ以下の Product_Collection ラベル（*.lblx）をすべて primary の
    メンバーにする。同じ LID が2回現れた場合は1回だけ使う。
    """

    def __init__(
        self,
        template: Path | str,
        mission: MissionConfig | Path | str,
        instrument: InstrumentConfig | Path | str,
        *,
        bundle_lid: str,
        publication_year: int,
        version_id: str = "1.0",
        modification_date: date | str | None = None,
        modification_description: str = "Initial release of the bundle.",
    ) -> None:
        template = Path(template).resolve()
        if not template.is_file():
            raise FileNotFoundError(f"Template not found: {template}")
        if not bundle_lid.strip():
            raise ValueError("Bundle LID is empty")
        self.template_path = template
        self._template = make_jinja_env(template.parent).get_template(template.name)
        self.mission = as_config(MissionConfig, mission)
        self.instrument = as_config(InstrumentConfig, instrument)
        self.bundle_lid = bundle_lid.strip()
        self.publication_year = publication_year
        self.version_id = version_id
        # Today (UTC) unless given / 指定がなければ今日（UTC）
        if modification_date is None:
            modification_date = datetime.now(timezone.utc).date()
        self.modification_date = str(modification_date)
        self.modification_description = modification_description

    def write(
        self, bundle_dir: Path | str, output_name: str | None = None
    ) -> BundleResult:
        """Write the Bundle label into bundle_dir and return the result.
        Bundle ラベルを bundle_dir に書き出し、結果を返す。

        The default name is <bundle directory name>.lblx (e.g. bc_mmo_pwi.lblx).
        既定のファイル名は <Bundle ディレクトリ名>.lblx（例：bc_mmo_pwi.lblx）。
        """
        bundle_dir = Path(bundle_dir).resolve()
        if not bundle_dir.is_dir():
            raise FileNotFoundError(f"Bundle directory not found: {bundle_dir}")
        members = find_collections(bundle_dir)
        if not members:
            raise RuntimeError(
                f"No Product_Collection labels (*.lblx) were found under {bundle_dir}"
            )

        output = bundle_dir / (output_name or f"{bundle_dir.name}.lblx")
        xml_text = self._template.render(**self._context(members))
        check_well_formed(xml_text, source=output.name)
        output.write_text(xml_text, encoding="utf-8", newline="\n")
        return BundleResult(label_path=output, members=members)

    def _context(self, members: list[BundleMember]) -> dict[str, Any]:
        bundle = self.instrument.bundle
        return {
            "bundle_lid": self.bundle_lid,
            "version_id": self.version_id,
            "bundle_title": bundle.title,
            "information_model_version": self.mission.information_model_version,
            "publication_year": self.publication_year,
            "bundle_description": bundle.description,
            "modification_date": self.modification_date,
            "modification_description": self.modification_description,
            "collections": members,
        }


def find_collections(bundle_dir: Path) -> list[BundleMember]:
    """Find the Product_Collection labels below bundle_dir.
    bundle_dir 以下の Product_Collection ラベルを探す。

    Files that are not XML, or not collections, are ignored.
    XML でないファイルや Collection 以外のラベルは無視する。
    """
    members: list[BundleMember] = []
    seen_lids: set[str] = set()
    bundle_dir = Path(bundle_dir)
    labels = {
        path for pattern in ("*.lblx", "*.LBLX") for path in bundle_dir.rglob(pattern)
    }
    for label_path in sorted(labels):
        try:
            root = ET.parse(label_path).getroot()
        except ET.ParseError:
            continue
        if root.tag != _COLLECTION_TAG:
            continue
        lid = _text(root, _LID_PATH)
        collection_type = _text(root, _TYPE_PATH)
        if not lid or not collection_type or lid in seen_lids:
            continue
        seen_lids.add(lid)
        member = BundleMember(lid, "Primary", collection_type.lower(), label_path)
        members.append(member)
    return members


def _text(root: ET.Element, path: str) -> str | None:
    value = root.findtext(path, namespaces=PDS_NSMAP)
    if value is None:
        return None
    return value.strip() or None
