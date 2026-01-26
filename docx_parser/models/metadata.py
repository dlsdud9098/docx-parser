"""
Metadata models for docx_parser.

This module contains metadata dataclasses for DOCX document properties.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CoreMetadata:
    """Dublin Core metadata from docProps/core.xml.

    Attributes:
        title: Document title.
        subject: Document subject.
        creator: Document author.
        keywords: Document keywords.
        description: Document description/comments.
        last_modified_by: Last person who modified the document.
        revision: Revision number.
        created: Creation datetime (ISO 8601).
        modified: Last modified datetime (ISO 8601).

    Example:
        >>> meta = CoreMetadata(title="Report", creator="John Doe")
        >>> meta.creator
        'John Doe'
    """
    title: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    keywords: Optional[str] = None
    description: Optional[str] = None
    last_modified_by: Optional[str] = None
    revision: Optional[int] = None
    created: Optional[str] = None
    modified: Optional[str] = None


@dataclass
class AppMetadata:
    """Application metadata from docProps/app.xml.

    Attributes:
        template: Template used.
        total_time: Editing time in minutes.
        pages: Page count.
        words: Word count.
        characters: Character count.
        characters_with_spaces: Character count including spaces.
        lines: Line count.
        paragraphs: Paragraph count.
        application: Application name (e.g., "Microsoft Office Word").
        app_version: Application version.
        company: Company name.

    Example:
        >>> meta = AppMetadata(pages=10, words=5000, application="Microsoft Office Word")
        >>> meta.pages
        10
    """
    template: Optional[str] = None
    total_time: Optional[int] = None
    pages: Optional[int] = None
    words: Optional[int] = None
    characters: Optional[int] = None
    characters_with_spaces: Optional[int] = None
    lines: Optional[int] = None
    paragraphs: Optional[int] = None
    application: Optional[str] = None
    app_version: Optional[str] = None
    company: Optional[str] = None


@dataclass
class DocxMetadata:
    """Combined DOCX metadata.

    Attributes:
        core: Dublin Core metadata.
        app: Application metadata.
        file_path: Full path to the DOCX file.
        file_name: DOCX filename.
        file_size: File size in bytes.
        year: Document year (user-specified or auto-extracted from filename).

    Example:
        >>> meta = DocxMetadata(
        ...     core=CoreMetadata(title="Report"),
        ...     app=AppMetadata(pages=10),
        ...     file_name="report.docx"
        ... )
        >>> meta.to_dict()
        {'title': 'Report', 'total_pages': 10, 'file_name': 'report.docx'}

        >>> meta = DocxMetadata(file_name="GBCC 2022_결과보고서.docx")
        >>> meta.to_dict()['year']
        2022

        >>> meta = DocxMetadata(file_name="report.docx", year=2023)
        >>> meta.to_dict()['year']
        2023
    """
    core: CoreMetadata = field(default_factory=CoreMetadata)
    app: AppMetadata = field(default_factory=AppMetadata)
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    year: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for LangChain metadata.

        Returns:
            Flat dictionary with all non-None metadata fields.
            Keys are mapped to common names (e.g., creator -> author).
        """
        result: Dict[str, Any] = {}

        # Core metadata
        if self.core:
            if self.core.title:
                result["title"] = self.core.title
            if self.core.subject:
                result["subject"] = self.core.subject
            if self.core.creator:
                result["author"] = self.core.creator
            if self.core.keywords:
                result["keywords"] = self.core.keywords
            if self.core.description:
                result["description"] = self.core.description
            if self.core.last_modified_by:
                result["last_modified_by"] = self.core.last_modified_by
            if self.core.revision:
                result["revision"] = self.core.revision
            if self.core.created:
                result["created_date"] = self.core.created
            if self.core.modified:
                result["modified_date"] = self.core.modified

        # App metadata
        if self.app:
            if self.app.pages:
                result["total_pages"] = self.app.pages
            if self.app.words:
                result["word_count"] = self.app.words
            if self.app.characters:
                result["character_count"] = self.app.characters
            if self.app.paragraphs:
                result["paragraph_count"] = self.app.paragraphs
            if self.app.lines:
                result["line_count"] = self.app.lines
            if self.app.application:
                result["application"] = self.app.application
            if self.app.app_version:
                result["app_version"] = self.app.app_version
            if self.app.company:
                result["company"] = self.app.company

        # File info
        if self.file_path:
            result["file_path"] = self.file_path
        if self.file_name:
            result["file_name"] = self.file_name
        if self.file_size:
            result["file_size"] = self.file_size

        # Year (user-specified takes priority, otherwise auto-extract from filename)
        if self.year:
            result["year"] = self.year
        elif self.file_name:
            year_match = re.search(r'(20\d{2})', self.file_name)
            if year_match:
                result["year"] = int(year_match.group(1))

        return result
