"""Generate PDS4 observational labels (.lblx) for BepiColombo Mio CDF files.
BepiColombo Mio の CDF ファイルに対する PDS4 観測ラベル（.lblx）を作る。
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cdflib
import numpy as np

from miopds_common import cdftool
from miopds_common._common import check_well_formed, make_jinja_env
from miopds_common._config import (
    DatasetConfig,
    InstrumentConfig,
    MissionConfig,
    MissionPhase,
    MissionTimeline,
    Target,
    as_config,
    load_authors,
    parse_utc,
)
from miopds_common.filetool import md5_of_file

# Map CDF data types to PDS4 data type names.
# CDF のデータ型から PDS4 のデータ型名への対応表。
TYPE_MAP = {
    1: "SignedByte",
    2: "SignedMSB2",
    4: "SignedMSB4",
    8: "SignedMSB8",
    11: "UnsignedByte",
    12: "UnsignedMSB2",
    14: "UnsignedMSB4",
    21: "IEEE754MSBSingle",
    22: "IEEE754MSBDouble",
    31: "SignedMSB8",
    32: "SignedMSB8",
    33: "SignedMSB8",
    41: "ASCII_String",
    51: "ASCII_String",
    "CDF_INT1": "SignedByte",
    "CDF_INT2": "SignedMSB2",
    "CDF_INT4": "SignedMSB4",
    "CDF_INT8": "SignedMSB8",
    "CDF_UINT1": "UnsignedByte",
    "CDF_UINT2": "UnsignedMSB2",
    "CDF_UINT4": "UnsignedMSB4",
    "CDF_REAL4": "IEEE754MSBSingle",
    "CDF_FLOAT": "IEEE754MSBSingle",
    "CDF_REAL8": "IEEE754MSBDouble",
    "CDF_DOUBLE": "IEEE754MSBDouble",
    "CDF_TIME_TT2000": "SignedMSB8",
    "CDF_EPOCH": "IEEE754MSBDouble",
    "CDF_CHAR": "ASCII_String",
    "CDF_UCHAR": "ASCII_String",
}

# Keep at most one empty line between XML sections.
# XML のセクション間の空行を最大1行にする。
_BLANK_LINES = re.compile(r"\n[ \t]*\n(?:[ \t]*\n)+")


class CDFLabelGenerator:
    """Generate PDS4 observational labels for CDF files with fixed settings.
    決まった設定（テンプレート、設定ファイル）で CDF の PDS4 観測ラベルを作る。

    Create it once and call write() for each CDF file.
    1回作って、CDF ファイルごとに write() を呼ぶ。

    Mission phase and target are chosen in this order:
    ミッションフェーズとターゲットは次の優先順位で決める。
      1. mission_phase / target given here (e.g. from the command line)
         ここで渡した値（コマンドの引数など）
      2. the timeline, if given / timeline（指定した場合のみ）
      3. the defaults in mission.json / mission.json の既定値

    Only uncompressed CDF files with zVariables are supported (cdftool limit).
    非圧縮で zVariable だけの CDF にのみ対応（cdftool の制約）。
    """

    def __init__(
        self,
        template: Path | str,
        mission: MissionConfig | Path | str,
        dataset: DatasetConfig | Path | str,
        *,
        timeline: MissionTimeline | Path | str | None = None,
        mission_phase: MissionPhase | None = None,
        target: Target | None = None,
        publication_year: int | None = None,
        description: str | None = None,
        modification_description: str = "Initial version",
        header_length: int = 404,
        internal_references: Sequence[Mapping[str, str]] = (),
    ) -> None:
        template = Path(template).resolve()
        if not template.is_file():
            raise FileNotFoundError(f"Template not found: {template}")
        self.template_path = template
        self._template = make_jinja_env(template.parent).get_template(template.name)

        # Accept either loaded objects or file paths / 読み込み済みの値でもパスでもよい
        self.mission = as_config(MissionConfig, mission)
        self.dataset = as_config(DatasetConfig, dataset)
        self.instrument = InstrumentConfig.load(self.dataset.instrument_file)
        self.authors = load_authors(self.dataset.authors_file)
        self.timeline = (
            None if timeline is None else as_config(MissionTimeline, timeline)
        )

        self.mission_phase = mission_phase
        self.target = target
        self.publication_year = publication_year
        self.description = description
        self.modification_description = modification_description
        # Confirm the CDF header length for each product / ヘッダー長は製品ごとに要確認
        self.header_length = header_length
        self.internal_references = [dict(ref) for ref in internal_references]

    def render(self, cdf_path: Path | str) -> str:
        """Return the label for one CDF file as XML text.
        1つの CDF ファイルのラベルを XML 文字列として返す。
        """
        cdf_path = Path(cdf_path).resolve()
        if not cdf_path.is_file():
            raise FileNotFoundError(f"CDF not found: {cdf_path}")
        text = self._template.render(**self._context(cdf_path))
        text = _BLANK_LINES.sub("\n\n", text)
        check_well_formed(text, source=cdf_path.name)
        return text

    def write(self, cdf_path: Path | str, output_dir: Path | str) -> Path:
        """Write <CDF name>.lblx into output_dir and return its path.
        output_dir に <CDF のファイル名>.lblx を書き出し、そのパスを返す。
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{Path(cdf_path).resolve().stem}.lblx"
        output.write_text(self.render(cdf_path), encoding="utf-8", newline="\n")
        return output

    # -- internal ----------------------------------------------------------

    def _context(self, cdf_path: Path) -> dict[str, Any]:
        """Collect every value used by the template.
        テンプレートに渡す値をすべて集める。
        """
        cdf = cdflib.CDF(str(cdf_path))
        globals_ = cdf.globalattsget()
        names = list(cdf.cdf_info().zVariables)
        physical = cdftool.cdfinfo(str(cdf_path))

        time_variable = self.dataset.cdf.time_variable
        start_time, stop_time = _time_bounds(cdf, time_variable)
        time_count = _validate_time_record_counts(
            cdf, names, self.dataset.cdf.epoch_variable, time_variable
        )
        objects = _data_objects(cdf, names, physical, time_count)

        date = _yyyymmdd_from_name(cdf_path.name)
        stat = cdf_path.stat()
        creation = datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        logical_identifier = _attr(globals_, "PDS_LOGICAL_IDENTIFIER").replace(
            "YYYYMMDD", date
        )
        if not logical_identifier:
            raise ValueError("CDF global attribute PDS_LOGICAL_IDENTIFIER is missing")

        phase, target = self._phase_and_target(start_time)
        mission = self.mission
        facets = self.dataset.science_facets
        instrument = self.instrument.instrument

        return {
            "logical_identifier": logical_identifier,
            "version_id": _attr(globals_, "PDS_VERSION_IDENTIFIER", "1.0"),
            "title": _attr(globals_, "TITLE", cdf_path.stem),
            "information_model_version": mission.information_model_version,
            "publication_year": self.publication_year or int(creation[:4]),
            "description": self.description
            or _attr(globals_, "Logical_source_description", _attr(globals_, "TITLE")),
            "authors": [asdict(author) for author in self.authors],
            "modification_date": datetime.now(timezone.utc).date().isoformat(),
            "modification_description": self.modification_description,
            "start_time": start_time,
            "stop_time": stop_time,
            "purpose": self.dataset.purpose,
            "processing_level": self.dataset.processing_level,
            "domains": facets.domains,
            "discipline_name": facets.discipline_name,
            "facet1": facets.facet1,
            "facet2": facets.facet2,
            "investigation_name": mission.investigation.name,
            "investigation_type": mission.investigation.type,
            "investigation_lid": mission.investigation.lid,
            "instrument_host_name": mission.instrument_host.name,
            "instrument_host_lid": mission.instrument_host.lid,
            "instrument_name": instrument.name,
            "instrument_lid": instrument.lid,
            "target_name": target.name,
            "target_type": target.type,
            "target_lid": target.lid,
            "mission_phase_name": phase.name,
            "mission_phase_id": phase.id,
            "sclk_start": _attr(globals_, "PDS_SCLK_START_COUNT"),
            "sclk_stop": _attr(globals_, "PDS_SCLK_STOP_COUNT"),
            "processing_software_title": _attr(globals_, "GENERATION_SOFTWARE"),
            "processing_software_version": _attr(globals_, "SOFTWARE_VERSION"),
            "source_file": _attr(globals_, "SOURCE_FILE"),
            "internal_references": self.internal_references,
            "cdf_file_name": cdf_path.name,
            "cdf_creation_time": creation,
            "cdf_size": stat.st_size,
            "cdf_md5": md5_of_file(cdf_path),
            "cdf_header_length": self.header_length,
            "cdf_parsing_standard_id": mission.cdf_parsing_standard_id,
            "data_objects": objects,
        }

    def _phase_and_target(self, start_time: str) -> tuple[MissionPhase, Target]:
        """Apply the priority: given value -> timeline -> mission.json default.
        優先順位（渡された値 → timeline → mission.json の既定値）を適用する。
        """
        phase, target = self.mission_phase, self.target
        if self.timeline is not None and (phase is None or target is None):
            # The time string is parsed only when the timeline is used.
            # 時刻文字列の解析は timeline を使うときだけ行う。
            when = parse_utc(start_time)
            phase = phase or self.timeline.phase_at(when)
            target = target or self.timeline.target_at(when)
        return (
            phase or self.mission.default_mission_phase,
            target or self.mission.default_target,
        )


def parse_internal_reference(value: str) -> dict[str, str]:
    """Parse "LID_OR_LIDVID|REFERENCE_TYPE" into a reference for the template.
    "LID または LIDVID|reference_type" の形式の文字列を、テンプレート用の参照に変換する。
    """
    identifier, separator, reference_type = value.partition("|")
    identifier = identifier.strip()
    reference_type = reference_type.strip()
    if not separator or not identifier or not reference_type:
        raise ValueError(
            f"Invalid internal reference: {value!r}. "
            "Expected 'LID_OR_LIDVID|REFERENCE_TYPE'."
        )
    # "::" separates LID and VID / "::" は LID と VID の区切り
    key = "lidvid_reference" if "::" in identifier else "lid_reference"
    return {key: identifier, "reference_type": reference_type}


# ---------------------------------------------------------------------------
# Helpers (logic unchanged from the original renderer)
# 補助関数（元のスクリプトから処理は変えていない）
# ---------------------------------------------------------------------------


def _scalar(value, default="") -> str:
    """Convert a CDF value into one normalized string."""
    if value is None:
        return str(default)
    if hasattr(value, "reshape") and hasattr(value, "size"):
        if int(value.size) == 0:
            return str(default)
        value = value.reshape(-1)[0]
    elif isinstance(value, (list, tuple)):
        if not value:
            return str(default)
        value = value[0]
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    text = str(value).strip()
    return text if text else str(default)


def _attr(attributes: dict, name: str, default="") -> str:
    """Read a CDF attribute using a case-insensitive key lookup."""
    for key, value in attributes.items():
        if key.lower() == name.lower():
            return _scalar(value, default)
    return str(default)


def _field(info, *names, default=None):
    """Read a field from a mapping or an object returned by cdflib."""
    for name in names:
        if isinstance(info, dict) and name in info:
            return info[name]
        if hasattr(info, name):
            return getattr(info, name)
    return default


def _yyyymmdd_from_name(name: str) -> str:
    """Extract the observation date from the CDF filename."""
    match = re.search(r"_(\d{8})(?:_|\.)", name)
    if not match:
        raise ValueError(f"Could not extract YYYYMMDD from CDF filename: {name}")
    return match.group(1)


def _time_bounds(cdf, variable_name: str) -> tuple[str, str]:
    """Return the first and last values of the configured time variable."""
    values = np.asarray(cdf.varget(variable_name))
    if values.size == 0:
        raise ValueError(f"Time variable is empty: {variable_name}")
    values = values.reshape(-1)
    return _scalar(values[0]), _scalar(values[-1])


def _variable_record_count(cdf, name: str, record_varying: bool) -> int:
    """Return the logical record count actually readable from the CDF."""
    if not record_varying:
        return 1
    values = np.asarray(cdf.varget(name))
    return 1 if values.ndim == 0 else int(values.shape[0])


def _validate_time_record_counts(cdf, names, epoch_name: str, time_name: str) -> int:
    """Require the epoch and text-time variables to have equal record counts."""
    if epoch_name not in names:
        raise ValueError(f"Epoch variable was not found: {epoch_name}")
    if time_name not in names:
        raise ValueError(f"Time variable was not found: {time_name}")
    epoch_count = _variable_record_count(cdf, epoch_name, True)
    time_count = _variable_record_count(cdf, time_name, True)
    if epoch_count != time_count:
        raise ValueError(
            f"CDF time record count mismatch: {epoch_name}={epoch_count}, "
            f"{time_name}={time_count}"
        )
    return epoch_count


def _data_objects(cdf, names, physical, time_count: int) -> list[dict[str, Any]]:
    """Build one PDS4 object description for each CDF zVariable.
    CDF の zVariable ごとに、PDS4 のデータオブジェクトの記述を作る。
    """
    objects = []
    for name in names:
        inquiry = cdf.varinq(name)
        attributes = cdf.varattsget(name)
        data_type = _field(inquiry, "Data_Type_Description", "Data_Type", default="")
        dimensions = list(_field(inquiry, "Dim_Sizes", default=[]) or [])
        record_varying = bool(_field(inquiry, "Rec_Vary", default=True))
        num_elements = int(_field(inquiry, "Num_Elements", default=1) or 1)
        records = _variable_record_count(cdf, name, record_varying)
        # Byte offset of the data from the top of the file / ファイル先頭からのバイト位置
        offset = int(physical.var_info[name]["offset_for_var"])
        description = _attr(attributes, "CATDESC", _attr(attributes, "FIELDNAM", name))

        if str(data_type).upper() in {"CDF_CHAR", "CDF_UCHAR", "51", "52"}:
            objects.append({
                "kind": "Table_Binary",
                "name": name,
                "offset": offset,
                "records": records,
                "record_length": num_elements,
                "pds_data_type": "ASCII_Date_Time_YMD",
                "description": description,
            })
            continue

        axes = []
        if record_varying:
            if records != time_count:
                raise ValueError(
                    f"Record-varying variable has an inconsistent count: "
                    f"{name}={records}, expected={time_count}"
                )
            axes.append({"name": "time", "elements": time_count})
        for index, size in enumerate(dimensions, start=1):
            size = int(size)
            if size > 1:
                dependency = _attr(attributes, f"DEPEND_{index}")
                axes.append({
                    "name": dependency or f"dimension_{index}",
                    "elements": size,
                })
        if not axes:
            axes.append({"name": "element", "elements": max(num_elements, 1)})

        try:
            type_key = int(data_type)
        except (TypeError, ValueError):
            type_key = str(data_type).upper()
        objects.append({
            "kind": "Array",
            "name": name,
            "offset": offset,
            "axes": axes,
            "pds_data_type": TYPE_MAP.get(type_key, str(data_type)),
            "unit": _attr(attributes, "UNITS"),
            "description": description,
            "fillval": _attr(attributes, "FILLVAL"),
            "validmin": _attr(attributes, "VALIDMIN"),
            "validmax": _attr(attributes, "VALIDMAX"),
        })
    objects.sort(key=lambda item: item["offset"])
    return objects
