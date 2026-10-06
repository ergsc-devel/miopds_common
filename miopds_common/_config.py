"""Load and check the JSON configuration files.
設定ファイル（JSON）を読み込み、中身を確認する。

Every file is checked strictly: a missing required key, an unknown key (for
example a typo) or a value of the wrong type raises ConfigError.
必須項目の欠落、知らない項目（打ち間違いなど）、型の誤りはすべて ConfigError にする。

See examples/config/README.md for the meaning of each item.
各項目の意味は examples/config/README.md を参照。
"""

import json
import types
import typing
from dataclasses import MISSING, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a configuration file is missing or invalid.
    設定ファイルが見つからない、または内容が正しくないときに出す例外。
    """


# Values in the example files that must be replaced before use.
# 見本ファイルの中で、使う前に必ず書き換える値の目印。
PLACEHOLDER_PREFIX = "REPLACE_"


# ---------------------------------------------------------------------------
# mission.json
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Investigation:
    name: str
    type: str
    lid: str


@dataclass(frozen=True)
class InstrumentHost:
    name: str
    lid: str


@dataclass(frozen=True)
class MissionPhase:
    name: str
    id: str


@dataclass(frozen=True)
class Target:
    name: str
    type: str
    lid: str


@dataclass(frozen=True)
class MissionConfig:
    """Values shared by all Mio instruments (mission.json).
    Mio の全機器で共通の値（mission.json）。
    """

    information_model_version: str
    investigation: Investigation
    instrument_host: InstrumentHost
    cdf_parsing_standard_id: str
    default_mission_phase: MissionPhase
    default_target: Target

    @classmethod
    def load(cls, path: Path | str) -> "MissionConfig":
        return _load_object(cls, path)


# ---------------------------------------------------------------------------
# instrument_*.json
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Instrument:
    name: str
    lid: str


@dataclass(frozen=True)
class BundleText:
    title: str
    description: str


@dataclass(frozen=True)
class CollectionText:
    title: str
    citation_description: str
    collection_description: str


@dataclass(frozen=True)
class InstrumentConfig:
    """Values for one instrument, i.e. one Bundle (instrument_*.json).
    1つの機器（= 1つの Bundle）の値（instrument_*.json）。
    """

    instrument: Instrument
    bundle: BundleText
    document_collection: CollectionText

    @classmethod
    def load(cls, path: Path | str) -> "InstrumentConfig":
        return _load_object(cls, path)


# ---------------------------------------------------------------------------
# dataset_*.json
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScienceFacets:
    domains: list[str]
    discipline_name: str
    # Omit the key when not applicable / 該当しない場合は項目ごと省略する
    facet1: str = ""
    facet2: str = ""


@dataclass(frozen=True)
class CDFVariables:
    time_variable: str
    epoch_variable: str


@dataclass(frozen=True)
class DataCollectionText:
    collection_type: str
    title: str
    citation_description: str
    collection_description: str


@dataclass(frozen=True)
class DatasetConfig:
    """Values for one dataset, i.e. one Data Collection (dataset_*.json).
    1つのデータセット（= 1つの Data Collection）の値（dataset_*.json）。

    Relative paths are resolved against the directory of the JSON file.
    相対パスは、JSON ファイルが置かれているディレクトリを基準に解釈する。
    """

    instrument_file: Path
    authors_file: Path
    purpose: str
    processing_level: str
    science_facets: ScienceFacets
    cdf: CDFVariables
    collection: DataCollectionText

    @classmethod
    def load(cls, path: Path | str) -> "DatasetConfig":
        return _load_object(cls, path)


# ---------------------------------------------------------------------------
# authors_*.json
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Author:
    display_full_name: str
    given_name: str
    family_name: str


def load_authors(path: Path | str) -> list[Author]:
    """Load a non-empty JSON list of authors.
    著者の JSON リスト（空でないこと）を読み込む。
    """
    path = _resolve(path)
    data = _read_json(path)
    if not isinstance(data, list) or not data:
        raise ConfigError(f"{path}: must be a non-empty JSON list of authors")
    return [
        _build(Author, item, f"{path}[{index}]", path.parent)
        for index, item in enumerate(data, start=1)
    ]


# ---------------------------------------------------------------------------
# mission_timeline.json (optional)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhasePeriod:
    start: datetime
    stop: datetime
    name: str
    id: str


@dataclass(frozen=True)
class TargetPeriod:
    start: datetime
    stop: datetime
    name: str
    type: str
    lid: str


@dataclass(frozen=True)
class MissionTimeline:
    """Periods that decide the mission phase and target from the observation time.
    観測時刻からミッションフェーズとターゲットを決めるための期間表。

    Each period covers start <= t < stop. A list that is omitted is not used.
    各期間は start 以上 stop 未満。省略したリストは使わない（既定値が使われる）。
    """

    mission_phases: list[PhasePeriod] | None = None
    targets: list[TargetPeriod] | None = None

    @classmethod
    def load(cls, path: Path | str) -> "MissionTimeline":
        timeline = _load_object(cls, path)
        for name in ("mission_phases", "targets"):
            _check_periods(getattr(timeline, name), f"{path}.{name}")
        return timeline

    def phase_at(self, when: datetime) -> MissionPhase | None:
        """Return the phase at the given time, or None if the list is omitted.
        指定時刻のフェーズを返す。リストが省略されていれば None。
        """
        period = _find_period(self.mission_phases, when, "mission phase")
        return None if period is None else MissionPhase(period.name, period.id)

    def target_at(self, when: datetime) -> Target | None:
        """Return the target at the given time, or None if the list is omitted.
        指定時刻のターゲットを返す。リストが省略されていれば None。
        """
        period = _find_period(self.targets, when, "target")
        return None if period is None else Target(period.name, period.type, period.lid)


def as_config(cls, value):
    """Return value if it is already a cls object, otherwise load it from a path.
    すでに cls のオブジェクトならそのまま返し、そうでなければパスとして読み込む。
    """
    return value if isinstance(value, cls) else cls.load(value)


def parse_utc(text: str) -> datetime:
    """Parse an ISO 8601 date-time; a value without a time zone is taken as UTC.
    ISO 8601 形式の日時を読む。タイムゾーンがなければ UTC とみなす。
    """
    try:
        value = datetime.fromisoformat(text.strip())
    except ValueError as error:
        raise ConfigError(f"Not an ISO 8601 date-time: {text!r}") from error
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _check_periods(periods, where: str) -> None:
    # Periods must be valid and must not overlap / 期間は正しく、重なってはいけない
    if periods is None:
        return
    ordered = sorted(periods, key=lambda period: period.start)
    for period in ordered:
        if period.start >= period.stop:
            raise ConfigError(f"{where}: start must be before stop ({period})")
    for before, after in zip(ordered, ordered[1:]):
        if after.start < before.stop:
            raise ConfigError(f"{where}: periods overlap ({before.name}, {after.name})")


def _find_period(periods, when: datetime, label: str):
    if periods is None:
        return None
    for period in periods:
        if period.start <= when < period.stop:
            return period
    # Do not fall back silently: the table is probably incomplete.
    # 黙って既定値にしない（期間表の書き漏れの可能性が高いため）。
    raise ConfigError(f"No {label} period in the timeline covers {when.isoformat()}")


# ---------------------------------------------------------------------------
# Generic loader / 汎用の読み込み処理
# ---------------------------------------------------------------------------


def _resolve(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except json.JSONDecodeError as error:
        raise ConfigError(f"{path}: invalid JSON: {error}") from error


def _load_object(cls, path: Path | str):
    path = _resolve(path)
    return _build(cls, _read_json(path), str(path), path.parent)


def _build(cls, data: Any, where: str, base_dir: Path):
    """Create a dataclass from a JSON object, checking keys and types.
    JSON オブジェクトから dataclass を作る。項目名と型を確認する。
    """
    if not isinstance(data, dict):
        raise ConfigError(f"{where}: must be a JSON object")
    unknown = sorted(set(data) - {field.name for field in fields(cls)})
    if unknown:
        raise ConfigError(f"{where}: unknown keys {unknown}")
    hints = typing.get_type_hints(cls)
    values = {}
    for field in fields(cls):
        key_where = f"{where}.{field.name}"
        if field.name not in data:
            if field.default is MISSING and field.default_factory is MISSING:
                raise ConfigError(f"{key_where}: required key is missing")
            continue
        values[field.name] = _convert(
            hints[field.name], data[field.name], key_where, base_dir
        )
    return cls(**values)


def _convert(hint, value: Any, where: str, base_dir: Path):
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)

    # "X | None": null is allowed / null を許す
    if origin in (typing.Union, types.UnionType) and type(None) in args:
        if value is None:
            return None
        (hint,) = [arg for arg in args if arg is not type(None)]
        origin, args = typing.get_origin(hint), typing.get_args(hint)

    if is_dataclass(hint):
        return _build(hint, value, where, base_dir)
    if origin is list:
        if not isinstance(value, list) or not value:
            raise ConfigError(f"{where}: must be a non-empty list")
        return [
            _convert(args[0], item, f"{where}[{index}]", base_dir)
            for index, item in enumerate(value, start=1)
        ]
    if hint in (str, Path, datetime):
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"{where}: must be a non-empty string")
        text = value.strip()
        if text.startswith(PLACEHOLDER_PREFIX):
            raise ConfigError(f"{where}: placeholder {text!r} must be replaced")
        if hint is Path:
            # Relative to the JSON file / JSON ファイルの場所を基準にする
            return (base_dir / text).resolve()
        if hint is datetime:
            try:
                return parse_utc(text)
            except ConfigError as error:
                raise ConfigError(f"{where}: {error}") from error
        return text
    raise TypeError(f"Unsupported config type: {hint!r}")  # Programming error / 実装の誤り
