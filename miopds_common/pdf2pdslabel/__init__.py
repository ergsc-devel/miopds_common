"""PDS4 Product_Document label generation.
PDS4 Product_Document ラベルの生成。

Usage / 使い方:
    from miopds_common import pdf2pdslabel

    generator = pdf2pdslabel.DocumentLabelGenerator(
        template, "mission.json",
        document_lid="urn:jaxa:darts:bc_mmo_pwi:document:bc_mmo_pwi_data_user_guide",
        title="...", description="...",
        publication_year=2027, publication_date="2027",
    )
    generator.write("document/bc_mmo_pwi_data_user_guide.pdf")

The Document Collection is made with
labels2collection.CollectionBuilder.for_documents().
Document Collection は labels2collection.CollectionBuilder.for_documents() で作る。
"""

from .generator import DocumentLabelGenerator

__all__ = ["DocumentLabelGenerator"]
