"""Generate PDS4 Product_Document labels for document files (PDF).
文書ファイル（PDF）に対する PDS4 Product_Document ラベルを作る。
"""

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from miopds_common._common import check_well_formed, make_jinja_env
from miopds_common._config import MissionConfig, as_config


class DocumentLabelGenerator:
    """Generate the Product_Document label of one document.
    1つの文書の Product_Document ラベルを作る。

    The label is written beside the PDF, as <PDF name>.lblx by default.
    ラベルは PDF と同じ場所に、既定では <PDF のファイル名>.lblx として書き出す。
    """

    def __init__(
        self,
        template: Path | str,
        mission: MissionConfig | Path | str,
        *,
        document_lid: str,
        title: str,
        description: str,
        publication_year: int,
        publication_date: str,
        version_id: str = "1.0",
        modification_date: date | str | None = None,
        modification_description: str = "Initial version",
        edition_name: str = "1.0",
        language: str = "English",
    ) -> None:
        template = Path(template).resolve()
        if not template.is_file():
            raise FileNotFoundError(f"Template not found: {template}")
        if not document_lid.strip():
            raise ValueError("Document LID is empty")
        self.template_path = template
        self._template = make_jinja_env(template.parent).get_template(template.name)
        self.mission = as_config(MissionConfig, mission)
        self.document_lid = document_lid.strip()
        self.title = title
        self.description = description
        self.publication_year = publication_year
        self.publication_date = publication_date
        self.version_id = version_id
        # Today (UTC) unless given / 指定がなければ今日（UTC）
        if modification_date is None:
            modification_date = datetime.now(timezone.utc).date()
        self.modification_date = str(modification_date)
        self.modification_description = modification_description
        self.edition_name = edition_name
        self.language = language

    def render(self, pdf_path: Path | str) -> str:
        """Return the label for the document as XML text.
        文書のラベルを XML 文字列として返す。
        """
        pdf_path = _existing_file(pdf_path)
        text = self._template.render(**self._context(pdf_path))
        check_well_formed(text, source=pdf_path.name)
        return text

    def write(self, pdf_path: Path | str, output_name: str | None = None) -> Path:
        """Write the label beside the PDF and return its path.
        ラベルを PDF と同じ場所に書き出し、そのパスを返す。
        """
        pdf_path = _existing_file(pdf_path)
        output = pdf_path.parent / (output_name or f"{pdf_path.stem}.lblx")
        output.write_text(self.render(pdf_path), encoding="utf-8", newline="\n")
        return output

    def _context(self, pdf_path: Path) -> dict[str, Any]:
        return {
            "document_lid": self.document_lid,
            "version_id": self.version_id,
            "title": self.title,
            "information_model_version": self.mission.information_model_version,
            "publication_year": self.publication_year,
            "description": self.description,
            "modification_date": self.modification_date,
            "modification_description": self.modification_description,
            "publication_date": self.publication_date,
            "edition_name": self.edition_name,
            "language": self.language,
            "pdf_file": pdf_path.name,
        }


def _existing_file(path: Path | str) -> Path:
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Document file not found: {path}")
    return path
