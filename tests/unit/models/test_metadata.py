"""Tests for docx_parser.models.metadata module."""

import pytest

from docx_parser.models.metadata import AppMetadata, CoreMetadata, DocxMetadata


class TestCoreMetadata:
    """Tests for CoreMetadata dataclass."""

    def test_default_creation(self):
        """Test creating CoreMetadata with defaults."""
        meta = CoreMetadata()
        assert meta.title is None
        assert meta.subject is None
        assert meta.creator is None
        assert meta.keywords is None
        assert meta.description is None
        assert meta.last_modified_by is None
        assert meta.revision is None
        assert meta.created is None
        assert meta.modified is None

    def test_full_creation(self):
        """Test creating CoreMetadata with all fields."""
        meta = CoreMetadata(
            title="Annual Report",
            subject="Finance",
            creator="John Doe",
            keywords="report, finance, 2024",
            description="Annual financial report",
            last_modified_by="Jane Smith",
            revision=5,
            created="2024-01-01T10:00:00Z",
            modified="2024-06-15T14:30:00Z"
        )
        assert meta.title == "Annual Report"
        assert meta.creator == "John Doe"
        assert meta.revision == 5

    def test_partial_creation(self):
        """Test creating CoreMetadata with some fields."""
        meta = CoreMetadata(title="Test Doc", creator="Author")
        assert meta.title == "Test Doc"
        assert meta.creator == "Author"
        assert meta.keywords is None

    def test_unicode_fields(self):
        """Test Korean/Unicode values."""
        meta = CoreMetadata(
            title="연간 보고서",
            creator="홍길동",
            keywords="보고서, 재무"
        )
        assert meta.title == "연간 보고서"
        assert meta.creator == "홍길동"


class TestAppMetadata:
    """Tests for AppMetadata dataclass."""

    def test_default_creation(self):
        """Test creating AppMetadata with defaults."""
        meta = AppMetadata()
        assert meta.template is None
        assert meta.total_time is None
        assert meta.pages is None
        assert meta.words is None
        assert meta.characters is None
        assert meta.characters_with_spaces is None
        assert meta.lines is None
        assert meta.paragraphs is None
        assert meta.application is None
        assert meta.app_version is None
        assert meta.company is None

    def test_full_creation(self):
        """Test creating AppMetadata with all fields."""
        meta = AppMetadata(
            template="Normal.dotm",
            total_time=120,
            pages=10,
            words=5000,
            characters=25000,
            characters_with_spaces=30000,
            lines=200,
            paragraphs=50,
            application="Microsoft Office Word",
            app_version="16.0",
            company="Acme Corp"
        )
        assert meta.pages == 10
        assert meta.words == 5000
        assert meta.application == "Microsoft Office Word"

    def test_statistics_fields(self):
        """Test document statistics fields."""
        meta = AppMetadata(
            pages=100,
            words=50000,
            characters=250000,
            paragraphs=1000,
            lines=5000
        )
        assert meta.pages == 100
        assert meta.words == 50000


class TestDocxMetadata:
    """Tests for DocxMetadata dataclass."""

    def test_default_creation(self):
        """Test creating DocxMetadata with defaults."""
        meta = DocxMetadata()
        assert isinstance(meta.core, CoreMetadata)
        assert isinstance(meta.app, AppMetadata)
        assert meta.file_path is None
        assert meta.file_name is None
        assert meta.file_size is None

    def test_with_nested_metadata(self):
        """Test creating DocxMetadata with nested objects."""
        meta = DocxMetadata(
            core=CoreMetadata(title="Report", creator="Author"),
            app=AppMetadata(pages=10, words=5000),
            file_name="report.docx",
            file_size=1024000
        )
        assert meta.core.title == "Report"
        assert meta.app.pages == 10
        assert meta.file_name == "report.docx"

    def test_to_dict_empty(self):
        """Test to_dict with all None values."""
        meta = DocxMetadata()
        result = meta.to_dict()
        assert result == {}

    def test_to_dict_core_only(self):
        """Test to_dict with core metadata only."""
        meta = DocxMetadata(
            core=CoreMetadata(title="Test", creator="Author")
        )
        result = meta.to_dict()

        assert result["title"] == "Test"
        assert result["author"] == "Author"  # Note: creator -> author mapping
        assert "subject" not in result

    def test_to_dict_app_only(self):
        """Test to_dict with app metadata only."""
        meta = DocxMetadata(
            app=AppMetadata(pages=10, words=5000, application="MS Word")
        )
        result = meta.to_dict()

        assert result["total_pages"] == 10  # Note: pages -> total_pages mapping
        assert result["word_count"] == 5000  # Note: words -> word_count mapping
        assert result["application"] == "MS Word"

    def test_to_dict_file_info(self):
        """Test to_dict with file info."""
        meta = DocxMetadata(
            file_path="/docs/report.docx",
            file_name="report.docx",
            file_size=1048576
        )
        result = meta.to_dict()

        assert result["file_path"] == "/docs/report.docx"
        assert result["file_name"] == "report.docx"
        assert result["file_size"] == 1048576

    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        meta = DocxMetadata(
            core=CoreMetadata(
                title="Annual Report",
                creator="John Doe",
                revision=5,
                created="2024-01-01T00:00:00Z",
                modified="2024-06-01T12:00:00Z"
            ),
            app=AppMetadata(
                pages=50,
                words=25000,
                characters=125000,
                paragraphs=500,
                lines=2000,
                application="Microsoft Word",
                app_version="16.0"
            ),
            file_path="/reports/annual.docx",
            file_name="annual.docx",
            file_size=2097152
        )
        result = meta.to_dict()

        # Core fields
        assert result["title"] == "Annual Report"
        assert result["author"] == "John Doe"
        assert result["revision"] == 5
        assert result["created_date"] == "2024-01-01T00:00:00Z"
        assert result["modified_date"] == "2024-06-01T12:00:00Z"

        # App fields
        assert result["total_pages"] == 50
        assert result["word_count"] == 25000
        assert result["character_count"] == 125000
        assert result["paragraph_count"] == 500
        assert result["line_count"] == 2000
        assert result["application"] == "Microsoft Word"
        assert result["app_version"] == "16.0"

        # File info
        assert result["file_path"] == "/reports/annual.docx"
        assert result["file_name"] == "annual.docx"
        assert result["file_size"] == 2097152

    def test_to_dict_langchain_compatible(self):
        """Test that to_dict output is LangChain metadata compatible."""
        meta = DocxMetadata(
            core=CoreMetadata(title="Doc", creator="Author"),
            app=AppMetadata(pages=5)
        )
        result = meta.to_dict()

        # All values should be JSON-serializable primitives
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, (str, int, float, bool, type(None)))

    def test_to_dict_excludes_none_values(self):
        """Test that None values are excluded from to_dict."""
        meta = DocxMetadata(
            core=CoreMetadata(title="Only Title")
        )
        result = meta.to_dict()

        assert "title" in result
        assert "author" not in result
        assert "subject" not in result
