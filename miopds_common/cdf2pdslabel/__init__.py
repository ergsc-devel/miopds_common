"""PDS4 observational label generation from CDF files.
CDF ファイルから PDS4 観測ラベルを生成。

Usage / 使い方:
    from miopds_common import cdf2pdslabel

    generator = cdf2pdslabel.CDFLabelGenerator(template, "mission.json", "dataset.json")
    generator.write("data.cdf", "out/")
"""

from .generator import CDFLabelGenerator, parse_internal_reference

__all__ = ["CDFLabelGenerator", "parse_internal_reference"]
