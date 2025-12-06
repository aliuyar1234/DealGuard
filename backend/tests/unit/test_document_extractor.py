"""
Unit tests for Document Extractor.

Tests cover:
- PDF extraction with PyMuPDF
- DOCX extraction with python-docx
- Table extraction (pdfplumber)
- File validation (size, type)
- OCR fallback behavior
"""
import hashlib
import io
from unittest.mock import MagicMock, patch

import pytest

from dealguard.infrastructure.document.extractor import (
    DocumentExtractor,
    ExtractedDocument,
    ExtractedTable,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_MIME_TYPES,
)
from dealguard.shared.exceptions import UnsupportedFileTypeError, ValidationError


class TestExtractedTable:
    """Tests for ExtractedTable dataclass."""

    def test_table_creation(self):
        """Test creating an extracted table."""
        table = ExtractedTable(
            page_number=1,
            rows=[
                ["Header1", "Header2"],
                ["Value1", "Value2"],
            ],
        )

        assert table.page_number == 1
        assert len(table.rows) == 2

    def test_table_to_markdown(self):
        """Test converting table to markdown."""
        table = ExtractedTable(
            page_number=1,
            rows=[
                ["Name", "Value"],
                ["Test", "123"],
                ["Other", "456"],
            ],
        )

        markdown = table.to_markdown()

        assert "| Name | Value |" in markdown
        assert "| --- | --- |" in markdown
        assert "| Test | 123 |" in markdown
        assert "| Other | 456 |" in markdown

    def test_table_to_markdown_with_explicit_header(self):
        """Test table to markdown with explicit header."""
        table = ExtractedTable(
            page_number=2,
            rows=[
                ["Data1", "Data2"],
                ["Data3", "Data4"],
            ],
            header=["Column A", "Column B"],
        )

        markdown = table.to_markdown()

        assert "| Column A | Column B |" in markdown
        assert "| Data1 | Data2 |" in markdown

    def test_table_to_markdown_empty(self):
        """Test empty table to markdown returns empty string."""
        table = ExtractedTable(page_number=1, rows=[])
        assert table.to_markdown() == ""

    def test_table_to_markdown_pads_short_rows(self):
        """Test that short rows are padded."""
        table = ExtractedTable(
            page_number=1,
            rows=[
                ["A", "B", "C"],
                ["1"],  # Short row
            ],
        )

        markdown = table.to_markdown()

        # Should pad with empty cells
        assert "| 1 |  |  |" in markdown


class TestExtractedDocument:
    """Tests for ExtractedDocument dataclass."""

    def test_document_creation(self):
        """Test creating an extracted document."""
        doc = ExtractedDocument(
            text="Sample document text",
            page_count=5,
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        assert doc.text == "Sample document text"
        assert doc.page_count == 5
        assert doc.file_hash == "abc123"
        assert doc.file_size_bytes == 1024
        assert doc.mime_type == "application/pdf"
        assert doc.tables == []

    def test_document_with_tables(self):
        """Test document with tables."""
        tables = [
            ExtractedTable(page_number=1, rows=[["A", "B"]]),
            ExtractedTable(page_number=2, rows=[["C", "D"]]),
        ]

        doc = ExtractedDocument(
            text="Text with tables",
            page_count=2,
            file_hash="def456",
            file_size_bytes=2048,
            mime_type="application/pdf",
            tables=tables,
        )

        assert len(doc.tables) == 2
        assert doc.tables[0].page_number == 1


class TestDocumentExtractor:
    """Tests for DocumentExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create DocumentExtractor instance."""
        return DocumentExtractor()

    def test_supported_mime_types(self):
        """Test supported MIME types constant."""
        expected = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/msword": "doc",
        }
        assert SUPPORTED_MIME_TYPES == expected

    def test_max_file_size(self):
        """Test max file size is 50 MB."""
        assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024

    def test_extract_rejects_too_large_file(self, extractor):
        """Test extraction rejects files exceeding size limit."""
        # Create content larger than MAX_FILE_SIZE_BYTES
        large_content = b"x" * (MAX_FILE_SIZE_BYTES + 1)

        from dealguard.shared.exceptions import FileTooLargeError

        with pytest.raises(FileTooLargeError):
            extractor.extract(
                content=large_content,
                filename="large.pdf",
                mime_type="application/pdf",
            )

    def test_extract_rejects_unsupported_mime_type(self, extractor):
        """Test extraction rejects unsupported file types."""
        content = b"some content"

        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            extractor.extract(
                content=content,
                filename="file.txt",
                mime_type="text/plain",
            )

        assert "text/plain" in str(exc_info.value)

    def test_extract_calculates_file_hash(self, extractor):
        """Test that file hash is correctly calculated."""
        content = b"test content for hashing"
        expected_hash = hashlib.sha256(content).hexdigest()

        with patch.object(extractor, "_extract_pdf") as mock_pdf:
            mock_pdf.return_value = ("Extracted text content that is long enough", 1, [])

            result = extractor.extract(
                content=content,
                filename="test.pdf",
                mime_type="application/pdf",
            )

        assert result.file_hash == expected_hash

    def test_extract_pdf_calls_extract_pdf_method(self, extractor):
        """Test that PDF extraction uses correct method."""
        content = b"pdf content"

        with patch.object(extractor, "_extract_pdf") as mock_pdf:
            mock_pdf.return_value = ("Long enough text content for validation tests", 3, [])

            result = extractor.extract(
                content=content,
                filename="test.pdf",
                mime_type="application/pdf",
            )

        mock_pdf.assert_called_once_with(content)
        assert result.page_count == 3

    def test_extract_docx_calls_extract_docx_method(self, extractor):
        """Test that DOCX extraction uses correct method."""
        content = b"docx content"
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        with patch.object(extractor, "_extract_docx") as mock_docx:
            mock_docx.return_value = ("Long enough text content for validation tests", 2, [])

            result = extractor.extract(
                content=content,
                filename="test.docx",
                mime_type=mime_type,
            )

        mock_docx.assert_called_once_with(content)
        assert result.page_count == 2

    def test_extract_validates_minimum_text_length(self, extractor):
        """Test extraction fails if extracted text is too short."""
        content = b"pdf content"

        with patch.object(extractor, "_extract_pdf") as mock_pdf:
            mock_pdf.return_value = ("Short", 1, [])  # Less than 50 chars

            with pytest.raises(ValidationError) as exc_info:
                extractor.extract(
                    content=content,
                    filename="test.pdf",
                    mime_type="application/pdf",
                )

            assert "zu wenig Text" in str(exc_info.value)

    def test_extract_validates_empty_text(self, extractor):
        """Test extraction fails if text is empty."""
        content = b"pdf content"

        with patch.object(extractor, "_extract_pdf") as mock_pdf:
            mock_pdf.return_value = ("", 1, [])

            with pytest.raises(ValidationError):
                extractor.extract(
                    content=content,
                    filename="test.pdf",
                    mime_type="application/pdf",
                )


class TestPDFExtraction:
    """Tests for PDF-specific extraction."""

    @pytest.fixture
    def extractor(self):
        """Create DocumentExtractor instance."""
        return DocumentExtractor()

    def test_extract_pdf_uses_pymupdf(self, extractor):
        """Test PDF extraction uses fitz (PyMuPDF)."""
        mock_content = b"mock pdf content"

        with patch("dealguard.infrastructure.document.extractor.fitz") as mock_fitz:
            # Setup mock document
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Page text content"
            mock_page.get_images.return_value = []

            mock_doc = MagicMock()
            mock_doc.__iter__ = lambda self: iter([mock_page])
            mock_doc.__len__ = lambda self: 1

            mock_fitz.open.return_value = mock_doc

            text, page_count, tables = extractor._extract_pdf(mock_content)

        mock_fitz.open.assert_called_once()
        assert "Page text content" in text
        assert page_count == 1

    def test_extract_pdf_handles_multiple_pages(self, extractor):
        """Test PDF extraction handles multiple pages."""
        mock_content = b"mock pdf content"

        with patch("dealguard.infrastructure.document.extractor.fitz") as mock_fitz:
            # Setup multiple pages
            mock_pages = []
            for i in range(3):
                page = MagicMock()
                page.get_text.return_value = f"Content of page {i+1}"
                page.get_images.return_value = []
                mock_pages.append(page)

            mock_doc = MagicMock()
            mock_doc.__iter__ = lambda self: iter(mock_pages)
            mock_doc.__len__ = lambda self: 3

            mock_fitz.open.return_value = mock_doc

            text, page_count, tables = extractor._extract_pdf(mock_content)

        assert page_count == 3
        assert "--- Seite 1 ---" in text
        assert "--- Seite 2 ---" in text
        assert "--- Seite 3 ---" in text

    def test_extract_pdf_handles_exception(self, extractor):
        """Test PDF extraction raises ValidationError on failure."""
        mock_content = b"invalid pdf"

        with patch("dealguard.infrastructure.document.extractor.fitz") as mock_fitz:
            mock_fitz.open.side_effect = Exception("Corrupt PDF")

            with pytest.raises(ValidationError) as exc_info:
                extractor._extract_pdf(mock_content)

            assert "PDF konnte nicht gelesen werden" in str(exc_info.value)


class TestDOCXExtraction:
    """Tests for DOCX-specific extraction."""

    @pytest.fixture
    def extractor(self):
        """Create DocumentExtractor instance."""
        return DocumentExtractor()

    def test_extract_docx_uses_python_docx(self, extractor):
        """Test DOCX extraction uses python-docx."""
        mock_content = b"mock docx content"

        with patch("dealguard.infrastructure.document.extractor.Document") as mock_doc_class:
            # Setup mock document
            mock_para = MagicMock()
            mock_para.text = "Paragraph text"

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para]
            mock_doc.tables = []

            mock_doc_class.return_value = mock_doc

            text, page_count, tables = extractor._extract_docx(mock_content)

        mock_doc_class.assert_called_once()
        assert "Paragraph text" in text

    def test_extract_docx_handles_tables(self, extractor):
        """Test DOCX extraction handles tables."""
        mock_content = b"mock docx content"

        with patch("dealguard.infrastructure.document.extractor.Document") as mock_doc_class:
            # Setup mock cell
            mock_cell = MagicMock()
            mock_cell.text = "Cell value"

            # Setup mock row
            mock_row = MagicMock()
            mock_row.cells = [mock_cell, mock_cell]

            # Setup mock table
            mock_table = MagicMock()
            mock_table.rows = [mock_row]

            mock_doc = MagicMock()
            mock_doc.paragraphs = []
            mock_doc.tables = [mock_table]

            mock_doc_class.return_value = mock_doc

            text, page_count, tables = extractor._extract_docx(mock_content)

        assert len(tables) == 1
        assert tables[0].page_number == 1

    def test_extract_docx_estimates_page_count(self, extractor):
        """Test DOCX extraction estimates page count from text length."""
        mock_content = b"mock docx content"

        with patch("dealguard.infrastructure.document.extractor.Document") as mock_doc_class:
            # Setup paragraphs with long text
            mock_para = MagicMock()
            mock_para.text = "A" * 6000  # ~2 pages

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para]
            mock_doc.tables = []

            mock_doc_class.return_value = mock_doc

            text, page_count, tables = extractor._extract_docx(mock_content)

        assert page_count == 2  # 6000 / 3000 = 2

    def test_extract_docx_handles_exception(self, extractor):
        """Test DOCX extraction raises ValidationError on failure."""
        mock_content = b"invalid docx"

        with patch("dealguard.infrastructure.document.extractor.Document") as mock_doc_class:
            mock_doc_class.side_effect = Exception("Corrupt DOCX")

            with pytest.raises(ValidationError) as exc_info:
                extractor._extract_docx(mock_content)

            assert "DOCX konnte nicht gelesen werden" in str(exc_info.value)


class TestOCRFallback:
    """Tests for OCR fallback behavior."""

    @pytest.fixture
    def extractor(self):
        """Create DocumentExtractor instance."""
        return DocumentExtractor()

    def test_should_try_ocr_when_page_has_images(self, extractor):
        """Test OCR is attempted when page has images but no text."""
        mock_page = MagicMock()
        mock_page.get_images.return_value = [("image1",), ("image2",)]

        assert extractor._should_try_ocr(mock_page) is True

    def test_should_not_try_ocr_when_no_images(self, extractor):
        """Test OCR is not attempted when page has no images."""
        mock_page = MagicMock()
        mock_page.get_images.return_value = []

        assert extractor._should_try_ocr(mock_page) is False

    def test_ocr_page_handles_missing_pytesseract(self, extractor):
        """Test OCR gracefully handles missing pytesseract."""
        mock_page = MagicMock()

        with patch.dict("sys.modules", {"pytesseract": None}):
            # Force ImportError
            with patch("builtins.__import__", side_effect=ImportError):
                result = extractor._ocr_page(mock_page)

        # Should return empty string, not raise
        assert result == ""

    def test_ocr_page_handles_ocr_error(self, extractor):
        """Test OCR gracefully handles OCR errors."""
        mock_page = MagicMock()
        mock_page.get_pixmap.side_effect = Exception("Render failed")

        result = extractor._ocr_page(mock_page)

        # Should return empty string, not raise
        assert result == ""


class TestPDFPlumberIntegration:
    """Tests for pdfplumber table extraction."""

    @pytest.fixture
    def extractor(self):
        """Create DocumentExtractor instance."""
        return DocumentExtractor()

    def test_extract_pdf_tables_with_pdfplumber(self, extractor):
        """Test table extraction with pdfplumber."""
        mock_content = b"pdf content"

        # Mock pdfplumber
        with patch("dealguard.infrastructure.document.extractor.pdfplumber") as mock_plumber:
            with patch("dealguard.infrastructure.document.extractor.PDFPLUMBER_AVAILABLE", True):
                # Setup mock page with table
                mock_table_data = [
                    ["Header1", "Header2"],
                    ["Data1", "Data2"],
                ]

                mock_page = MagicMock()
                mock_page.extract_tables.return_value = [mock_table_data]

                mock_pdf = MagicMock()
                mock_pdf.pages = [mock_page]
                mock_pdf.__enter__ = lambda self: mock_pdf
                mock_pdf.__exit__ = MagicMock(return_value=False)

                mock_plumber.open.return_value = mock_pdf

                tables = extractor._extract_pdf_tables(mock_content)

        assert len(tables) == 1
        assert tables[0].page_number == 1
        assert tables[0].rows[0] == ["Header1", "Header2"]

    def test_extract_pdf_tables_handles_none_cells(self, extractor):
        """Test table extraction handles None cells."""
        mock_content = b"pdf content"

        with patch("dealguard.infrastructure.document.extractor.pdfplumber") as mock_plumber:
            with patch("dealguard.infrastructure.document.extractor.PDFPLUMBER_AVAILABLE", True):
                # Table with None values
                mock_table_data = [
                    ["Header", None],
                    [None, "Value"],
                ]

                mock_page = MagicMock()
                mock_page.extract_tables.return_value = [mock_table_data]

                mock_pdf = MagicMock()
                mock_pdf.pages = [mock_page]
                mock_pdf.__enter__ = lambda self: mock_pdf
                mock_pdf.__exit__ = MagicMock(return_value=False)

                mock_plumber.open.return_value = mock_pdf

                tables = extractor._extract_pdf_tables(mock_content)

        # None should be replaced with empty string
        assert tables[0].rows[0] == ["Header", ""]
        assert tables[0].rows[1] == ["", "Value"]

    def test_extract_pdf_tables_skips_single_row_tables(self, extractor):
        """Test that single-row tables are skipped."""
        mock_content = b"pdf content"

        with patch("dealguard.infrastructure.document.extractor.pdfplumber") as mock_plumber:
            with patch("dealguard.infrastructure.document.extractor.PDFPLUMBER_AVAILABLE", True):
                # Single row table
                mock_table_data = [["Only one row"]]

                mock_page = MagicMock()
                mock_page.extract_tables.return_value = [mock_table_data]

                mock_pdf = MagicMock()
                mock_pdf.pages = [mock_page]
                mock_pdf.__enter__ = lambda self: mock_pdf
                mock_pdf.__exit__ = MagicMock(return_value=False)

                mock_plumber.open.return_value = mock_pdf

                tables = extractor._extract_pdf_tables(mock_content)

        # Single row table should be skipped
        assert len(tables) == 0

    def test_extract_pdf_tables_handles_error_gracefully(self, extractor):
        """Test table extraction doesn't fail completely on error."""
        mock_content = b"pdf content"

        with patch("dealguard.infrastructure.document.extractor.pdfplumber") as mock_plumber:
            with patch("dealguard.infrastructure.document.extractor.PDFPLUMBER_AVAILABLE", True):
                mock_plumber.open.side_effect = Exception("pdfplumber error")

                tables = extractor._extract_pdf_tables(mock_content)

        # Should return empty list, not raise
        assert tables == []
