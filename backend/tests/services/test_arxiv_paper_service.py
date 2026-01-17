from unittest.mock import MagicMock, patch

import pytest

from papercast.entities import ArxivPaper, ArxivPaperStatus, ArxivSection
from papercast.services.arxiv_paper_service import ArxivPaperService


def create_mock_arxiv_paper_service():
    mock_repo = MagicMock()
    return ArxivPaperService(mock_repo)


@pytest.fixture
def arxiv_paper_service_mock():
    service = create_mock_arxiv_paper_service()

    sample_section = ArxivSection(
        title="Introduction",
        level=1,
        section_level_name="section.1",
        start_page=0,
        end_page=2,
        next_section_title="Related Work",
    )

    service.arxiv_paper_repo.select_all.return_value = [
        ArxivPaper(
            id=1,
            title="Paper 1",
            abstract="Abstract 1",
            authors=["Author 1"],
            url="https://arxiv.org/abs/2401.00001",
            paper_id="2401.00001",
            target_date="2024-01-01",
            sections=[sample_section],
            status=ArxivPaperStatus.initialized,
        ),
        ArxivPaper(
            id=2,
            title="Paper 2",
            abstract="Abstract 2",
            authors=["Author 2"],
            url="https://arxiv.org/abs/2401.00002",
            paper_id="2401.00002",
            target_date="2024-01-01",
            sections=[],
            status=ArxivPaperStatus.script_created,
        ),
    ]

    service.arxiv_paper_repo.find.return_value = ArxivPaper(
        id=1,
        title="Paper 1",
        abstract="Abstract 1",
        authors=["Author 1"],
        url="https://arxiv.org/abs/2401.00001",
        paper_id="2401.00001",
        target_date="2024-01-01",
        sections=[sample_section],
        status=ArxivPaperStatus.initialized,
    )

    service.arxiv_paper_repo.select_target_papers.return_value = [
        ArxivPaper(
            id=2,
            title="Paper 2",
            abstract="Abstract 2",
            authors=["Author 2"],
            url="https://arxiv.org/abs/2401.00002",
            paper_id="2401.00002",
            target_date="2024-01-01",
            sections=[],
            script="Speaker1: Hello",
            status=ArxivPaperStatus.script_created,
        ),
    ]

    return service


@pytest.fixture
def arxiv_paper_service_empty_mock():
    service = create_mock_arxiv_paper_service()
    service.arxiv_paper_repo.select_all.return_value = []
    service.arxiv_paper_repo.find.side_effect = ValueError("ArxivPaper id 999 not found")
    service.arxiv_paper_repo.select_target_papers.return_value = []
    return service


class TestFetchAllArxivPapers:
    def test_fetch_all_arxiv_papers(self, arxiv_paper_service_mock):
        result = arxiv_paper_service_mock.fetch_all_arxiv_papers()

        assert len(result) == 2
        assert all(isinstance(p, ArxivPaper) for p in result)
        arxiv_paper_service_mock.arxiv_paper_repo.select_all.assert_called_once()

    def test_fetch_all_arxiv_papers_empty(self, arxiv_paper_service_empty_mock):
        result = arxiv_paper_service_empty_mock.fetch_all_arxiv_papers()

        assert len(result) == 0
        arxiv_paper_service_empty_mock.arxiv_paper_repo.select_all.assert_called_once()


class TestFindArxivPaper:
    def test_find_arxiv_paper(self, arxiv_paper_service_mock):
        result = arxiv_paper_service_mock.find_arxiv_paper(1)

        assert result is not None
        assert isinstance(result, ArxivPaper)
        assert result.id == 1
        arxiv_paper_service_mock.arxiv_paper_repo.find.assert_called_once_with(1)

    def test_find_arxiv_paper_not_found(self, arxiv_paper_service_empty_mock):
        with pytest.raises(ValueError, match="ArxivPaper id 999 not found"):
            arxiv_paper_service_empty_mock.find_arxiv_paper(999)

        arxiv_paper_service_empty_mock.arxiv_paper_repo.find.assert_called_once_with(999)


class TestSelectTargetArxivPapers:
    def test_select_target_arxiv_papers(self, arxiv_paper_service_mock):
        result = arxiv_paper_service_mock.select_target_arxiv_papers("2024-01-01")

        assert len(result) == 1
        assert all(p.script != "" for p in result)
        arxiv_paper_service_mock.arxiv_paper_repo.select_target_papers.assert_called_once_with("2024-01-01")

    def test_select_target_arxiv_papers_empty(self, arxiv_paper_service_empty_mock):
        result = arxiv_paper_service_empty_mock.select_target_arxiv_papers("2024-01-01")

        assert len(result) == 0


class TestUpdateStatus:
    def test_update_status(self, arxiv_paper_service_mock):
        paper = ArxivPaper(
            id=1,
            title="Paper 1",
            abstract="Abstract 1",
            authors=["Author 1"],
            url="https://arxiv.org/abs/2401.00001",
            paper_id="2401.00001",
            target_date="2024-01-01",
            sections=[],
            status=ArxivPaperStatus.initialized,
        )
        new_status = ArxivPaperStatus.script_created

        arxiv_paper_service_mock.update_status(paper, new_status)

        assert paper.status == new_status
        arxiv_paper_service_mock.arxiv_paper_repo.update.assert_called_once_with(paper)


class TestCreateArxivPaper:
    @patch("papercast.services.arxiv_paper_service.download_paper")
    @patch("papercast.services.arxiv_paper_service.MarkdownParser")
    @patch("papercast.services.arxiv_paper_service.ArxivPaperScraper")
    def test_create_arxiv_paper(self, mock_scraper_class, mock_parser_class, mock_download, arxiv_paper_service_mock):
        mock_scraper_instance = MagicMock()
        mock_scraper_class.return_value = mock_scraper_instance

        sample_section = ArxivSection(
            title="Introduction",
            level=1,
            section_level_name="section.1",
            start_page=0,
            end_page=2,
            next_section_title="Related Work",
        )

        mock_scraper_instance.scrape_arxiv_info.return_value = ArxivPaper(
            title="New Paper",
            abstract="New Abstract",
            authors=["New Author"],
            url="https://arxiv.org/abs/2401.00003",
            paper_id="2401.00003",
            target_date="2024-01-01",
            sections=[],
        )

        mock_download.return_value = "/tmp/papers/2401.00003.pdf"

        mock_parser_instance = MagicMock()
        mock_parser_class.return_value = mock_parser_instance
        mock_parser_instance.extract_all_sections_by_outline.return_value = [sample_section]

        arxiv_paper_service_mock.arxiv_paper_repo.create.return_value = ArxivPaper(
            id=3,
            title="New Paper",
            abstract="New Abstract",
            authors=["New Author"],
            url="https://arxiv.org/abs/2401.00003",
            paper_id="2401.00003",
            target_date="2024-01-01",
            sections=[sample_section],
        )

        result = arxiv_paper_service_mock.create_arxiv_paper("https://arxiv.org/abs/2401.00003")

        assert result is not None
        assert result.id == 3
        mock_scraper_class.assert_called_once_with("https://arxiv.org/abs/2401.00003")
        mock_download.assert_called_once_with("2401.00003")
        mock_parser_class.assert_called_once()
        arxiv_paper_service_mock.arxiv_paper_repo.create.assert_called_once()
