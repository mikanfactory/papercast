from unittest.mock import MagicMock, patch

import pytest

from papercast.entities import ArxivSection
from papercast.services.markdown_parser import MarkdownParser, extract_after, extract_before


class TestExtractLines:
    def test_extract_before(self):
        text = "Line 1\nLine 2\nMarker Line\nLine 4\nLine 5"
        result = extract_before(text, "Marker Line")

        assert result == "Line 1\nLine 2"

    def test_extract_before_marker_not_found(self):
        text = "Line 1\nLine 2\nLine 3"
        result = extract_before(text, "Marker Line")

        assert result == text

    def test_extract_after(self):
        text = "Line 1\nLine 2\nMarker Line\nLine 4\nLine 5"
        result = extract_after(text, "Marker Line")

        assert result == "Line 4\nLine 5"

    def test_extract_after_marker_not_found(self):
        text = "Line 1\nLine 2\nLine 3"
        result = extract_after(text, "Marker Line")

        assert result == text

    def test_extract_before_at_start(self):
        text = "Marker Line\nLine 2\nLine 3"
        result = extract_before(text, "Marker Line")

        assert result == ""

    def test_extract_after_at_end(self):
        text = "Line 1\nLine 2\nMarker Line"
        result = extract_after(text, "Marker Line")

        assert result == ""


class TestMarkdownParser:
    @patch("papercast.services.markdown_parser.pymupdf.open")
    def test_extract_sections_by_outline(self, mock_open):
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_doc.get_toc.return_value = [
            [1, "Introduction", 1, {"nameddest": "section.1", "page": 0}],
            [1, "Related Work", 2, {"nameddest": "section.2", "page": 2}],
            [1, "Methods", 3, {"nameddest": "section.3", "page": 5}],
        ]
        mock_open.return_value = mock_doc

        parser = MarkdownParser("/path/to/paper.pdf")
        sections = parser.extract_sections_by_outline()

        assert len(sections) == 2
        assert sections[0].title == "Introduction"
        assert sections[0].level == 1
        assert sections[0].section_level_name == "section.1"
        assert sections[0].start_page == 0
        assert sections[0].end_page == 2
        assert sections[0].next_section_title == "Related Work"

        assert sections[1].title == "Related Work"
        assert sections[1].start_page == 2
        assert sections[1].end_page == 5

    @patch("papercast.services.markdown_parser.pymupdf.open")
    def test_extract_sections_by_outline_with_level_filter(self, mock_open):
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_doc.get_toc.return_value = [
            [1, "Introduction", 1, {"nameddest": "section.1", "page": 0}],
            [2, "Background", 1, {"nameddest": "section.1.1", "page": 1}],
            [1, "Related Work", 2, {"nameddest": "section.2", "page": 2}],
        ]
        mock_open.return_value = mock_doc

        parser = MarkdownParser("/path/to/paper.pdf")
        sections = parser.extract_sections_by_outline(level=1)

        assert len(sections) == 1
        assert sections[0].title == "Introduction"
        assert sections[0].next_section_title == "Related Work"

    @patch("papercast.services.markdown_parser.pymupdf.open")
    def test_extract_sections_by_outline_empty_toc_raises_error(self, mock_open):
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_doc.get_toc.return_value = []
        mock_open.return_value = mock_doc

        parser = MarkdownParser("/path/to/paper.pdf")

        with pytest.raises(ValueError, match="The document has no outline"):
            parser.extract_sections_by_outline()

    @patch("papercast.services.markdown_parser.pymupdf4llm.to_markdown")
    @patch("papercast.services.markdown_parser.pymupdf.open")
    def test_extract_markdown_text(self, mock_open, mock_to_markdown):
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_open.return_value = mock_doc

        mock_to_markdown.return_value = """
# Introduction

This is the introduction section content.

# Related Work

This is the related work section.
"""

        parser = MarkdownParser("/path/to/paper.pdf")
        section = ArxivSection(
            title="Introduction",
            level=1,
            section_level_name="section.1",
            start_page=0,
            end_page=1,
            next_section_title="Related Work",
        )

        result = parser.extract_markdown_text(section)

        assert "This is the introduction section content." in result
        assert "Related Work" not in result
        mock_to_markdown.assert_called_once()

    @patch("papercast.services.markdown_parser.pymupdf4llm.to_markdown")
    @patch("papercast.services.markdown_parser.pymupdf.open")
    def test_read_all(self, mock_open, mock_to_markdown):
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_open.return_value = mock_doc

        mock_to_markdown.return_value = "Full document markdown content"

        parser = MarkdownParser("/path/to/paper.pdf")
        result = parser.read_all()

        assert result == "Full document markdown content"
        mock_to_markdown.assert_called_once_with(
            mock_doc,
            ignore_graphics=True,
            ignore_images=True,
            ignore_code=True,
        )
