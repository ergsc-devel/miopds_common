"""PDS4 Bundle label generation.
PDS4 Bundle ラベルの生成。

Usage / 使い方:
    from miopds_common import collections2bundle

    builder = collections2bundle.BundleBuilder(
        template, "mission.json", "instrument.json",
        bundle_lid="urn:jaxa:darts:bc_mmo_pwi",
        publication_year=2027,
    )
    result = builder.write("bc_mmo_pwi/", "bundle_bc_mmo_pwi.xml")
"""

from .builder import BundleBuilder, BundleMember, BundleResult, find_collections

__all__ = ["BundleBuilder", "BundleMember", "BundleResult", "find_collections"]
