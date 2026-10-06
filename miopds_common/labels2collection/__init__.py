"""PDS4 Collection label and inventory generation.
PDS4 Collection ラベルとインベントリの生成。

Usage / 使い方:
    from miopds_common import labels2collection

    builder = labels2collection.CollectionBuilder(
        template, "mission.json", "dataset.json",
        collection_lid="urn:jaxa:darts:bc_mmo_pwi:data_calibrated_efd",
        publication_year=2027,
    )
    result = builder.write("labels/", "out/", "data_calibrated_efd")
"""

from .builder import CollectionBuilder, CollectionResult

__all__ = ["CollectionBuilder", "CollectionResult"]
