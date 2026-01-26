"""
Metadata extraction processor for DOCX files.

Extracts core metadata (Dublin Core) and application metadata from DOCX files.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional

from ..models import AppMetadata, CoreMetadata, DocxMetadata
from ..utils.xml import METADATA_NAMESPACES
from .base import ParsingContext, Processor

logger = logging.getLogger(__name__)


class MetadataProcessor(Processor):
    """
    Processor for extracting metadata from DOCX files.

    Extracts both core metadata (Dublin Core properties like title, author)
    and application metadata (page count, word count, etc.).
    """

    def __init__(self, namespaces: Optional[dict] = None) -> None:
        """
        Initialize metadata processor.

        Args:
            namespaces: Optional custom namespace dictionary.
        """
        self._namespaces = namespaces or METADATA_NAMESPACES

    def process(
        self,
        context: ParsingContext,
        docx_path: Optional[Path] = None,
    ) -> DocxMetadata:
        """
        Extract all metadata from DOCX file.

        Args:
            context: ParsingContext containing the ZipFile.
            docx_path: Path to the DOCX file for file info.

        Returns:
            DocxMetadata containing all extracted metadata.
        """
        if context.zip_file is None:
            logger.warning("No ZipFile in context, returning empty metadata")
            return DocxMetadata()

        core = self._extract_core_metadata(context.zip_file)
        app = self._extract_app_metadata(context.zip_file)

        # File info from path
        file_path = str(docx_path.absolute()) if docx_path else None
        file_name = docx_path.name if docx_path else None
        file_size = (
            docx_path.stat().st_size
            if docx_path and docx_path.exists()
            else None
        )

        return DocxMetadata(
            core=core,
            app=app,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
        )

    def _extract_core_metadata(self, z: zipfile.ZipFile) -> CoreMetadata:
        """
        Extract metadata from docProps/core.xml (Dublin Core).

        Args:
            z: Open ZipFile handle.

        Returns:
            CoreMetadata with extracted properties.
        """
        try:
            core_xml = z.read("docProps/core.xml").decode("utf-8")
        except KeyError:
            logger.debug("No core.xml found in DOCX")
            return CoreMetadata()

        root = ET.fromstring(core_xml)
        ns = self._namespaces

        def get_text(xpath: str) -> Optional[str]:
            elem = root.find(xpath, ns)
            return elem.text.strip() if elem is not None and elem.text else None

        def get_int(xpath: str) -> Optional[int]:
            text = get_text(xpath)
            if text and text.isdigit():
                return int(text)
            return None

        return CoreMetadata(
            title=get_text(".//dc:title"),
            subject=get_text(".//dc:subject"),
            creator=get_text(".//dc:creator"),
            keywords=get_text(".//cp:keywords"),
            description=get_text(".//dc:description"),
            last_modified_by=get_text(".//cp:lastModifiedBy"),
            revision=get_int(".//cp:revision"),
            created=get_text(".//dcterms:created"),
            modified=get_text(".//dcterms:modified"),
        )

    def _extract_app_metadata(self, z: zipfile.ZipFile) -> AppMetadata:
        """
        Extract metadata from docProps/app.xml (Application properties).

        Args:
            z: Open ZipFile handle.

        Returns:
            AppMetadata with extracted properties.
        """
        try:
            app_xml = z.read("docProps/app.xml").decode("utf-8")
        except KeyError:
            logger.debug("No app.xml found in DOCX")
            return AppMetadata()

        root = ET.fromstring(app_xml)
        # app.xml uses extended-properties namespace
        ns = {
            "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
        }

        def get_text(tag: str) -> Optional[str]:
            # Try with namespace first, then without
            elem = root.find(f".//ep:{tag}", ns)
            if elem is None:
                elem = root.find(f".//{tag}")
            return elem.text.strip() if elem is not None and elem.text else None

        def get_int(tag: str) -> Optional[int]:
            text = get_text(tag)
            if text and text.isdigit():
                return int(text)
            return None

        return AppMetadata(
            template=get_text("Template"),
            total_time=get_int("TotalTime"),
            pages=get_int("Pages"),
            words=get_int("Words"),
            characters=get_int("Characters"),
            characters_with_spaces=get_int("CharactersWithSpaces"),
            lines=get_int("Lines"),
            paragraphs=get_int("Paragraphs"),
            application=get_text("Application"),
            app_version=get_text("AppVersion"),
            company=get_text("Company"),
        )


def extract_metadata(
    zip_file: zipfile.ZipFile,
    docx_path: Optional[Path] = None,
) -> DocxMetadata:
    """
    Convenience function to extract metadata from a DOCX file.

    Args:
        zip_file: Open ZipFile handle for the DOCX.
        docx_path: Optional path to the DOCX file.

    Returns:
        DocxMetadata containing extracted metadata.
    """
    processor = MetadataProcessor()
    context = ParsingContext(zip_file=zip_file)
    return processor.process(context, docx_path=docx_path)
