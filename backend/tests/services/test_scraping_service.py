import datetime as dt
from unittest.mock import MagicMock, patch

from papercast.services.scraping_service import ArxivPaperScraper, DailyPaperScraper, download_paper


class TestDailyPaperScraper:
    @patch("papercast.services.scraping_service.requests.get")
    def test_get_daily_papers_urls(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <body>
            <a href="/papers/2401.00001">Paper 1</a>
            <a href="/papers/2401.00002">Paper 2</a>
            <a href="/other-link">Other</a>
        </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = DailyPaperScraper(dt.datetime(2024, 1, 15))
        urls = scraper.get_daily_papers_urls()

        assert len(urls) == 2
        assert "https://huggingface.co/papers/2401.00001" in urls
        assert "https://huggingface.co/papers/2401.00002" in urls
        mock_get.assert_called_once_with("https://huggingface.co/papers/date/2024-01-15")

    @patch("papercast.services.scraping_service.requests.get")
    def test_get_papers_with_arxiv_ids(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <body>
            <a href="/papers/2401.00001">Paper 1</a>
            <a href="/papers/2401.00002">Paper 2</a>
            <a href="/papers/2401.00001">Paper 1 Duplicate</a>
        </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = DailyPaperScraper(dt.datetime(2024, 1, 15))
        arxiv_ids = scraper.get_papers_with_arxiv_ids()

        assert len(arxiv_ids) == 2
        assert "2401.00001" in arxiv_ids
        assert "2401.00002" in arxiv_ids


class TestArxivPaperScraper:
    @patch("papercast.services.scraping_service.requests.get")
    def test_scrape_arxiv_info(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <body>
            <h1 class="title">Title:Test Paper Title</h1>
            <div class="authors">
                <a>Alice Smith</a>
                <a>Bob Jones</a>
            </div>
            <blockquote class="abstract">Abstract: This is the abstract of the paper.</blockquote>
        </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = ArxivPaperScraper("https://arxiv.org/abs/2401.00001")
        paper = scraper.scrape_arxiv_info()

        assert paper.title == "Test Paper Title"
        assert paper.authors == ["Alice Smith", "Bob Jones"]
        assert paper.abstract == "This is the abstract of the paper."
        assert paper.url == "https://arxiv.org/abs/2401.00001"
        assert paper.paper_id == "2401.00001"
        assert paper.sections == []
        assert paper.target_date is not None

    @patch("papercast.services.scraping_service.requests.get")
    def test_scrape_arxiv_info_with_empty_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <body>
            <h1 class="title">Title:</h1>
            <div class="authors"></div>
            <blockquote class="abstract">Abstract:</blockquote>
        </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = ArxivPaperScraper("https://arxiv.org/abs/2401.00003")
        paper = scraper.scrape_arxiv_info()

        assert paper.title == ""
        assert paper.authors == []
        assert paper.abstract == ""


class TestDownloadPaper:
    @patch("papercast.services.scraping_service.requests.get")
    def test_download_paper(self, mock_get, tmp_path):
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"PDF content chunk 1", b"PDF content chunk 2"]
        mock_get.return_value = mock_response

        with patch("papercast.services.scraping_service.download_path") as mock_download_path:
            destination = tmp_path / "papers" / "2401.00001.pdf"
            mock_download_path.return_value = destination

            result = download_paper("2401.00001")

            assert result == destination
            assert destination.exists()
            assert destination.read_bytes() == b"PDF content chunk 1PDF content chunk 2"
            mock_get.assert_called_once_with("https://arxiv.org/pdf/2401.00001")
