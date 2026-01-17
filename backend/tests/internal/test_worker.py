from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from papercast.dependencies import get_arxiv_paper_service
from papercast.entities import ArxivPaper, ArxivPaperStatus
from papercast.internal import worker
from papercast.main import app
from papercast.services.arxiv_paper_service import ArxivPaperService


def create_mock_arxiv_paper_service():
    return MagicMock(spec=ArxivPaperService)


@pytest.fixture
def client_with_mock():
    arxiv_paper_service = create_mock_arxiv_paper_service()

    arxiv_paper_service.find_arxiv_paper.return_value = ArxivPaper(
        id=1,
        title="Test Paper",
        abstract="Test abstract",
        authors=["Author"],
        url="https://arxiv.org/abs/2401.00001",
        paper_id="2401.00001",
        target_date="2024-01-01",
        sections=[],
        script="Speaker1: Hello",
        status=ArxivPaperStatus.initialized,
    )

    arxiv_paper_service.select_target_arxiv_papers.return_value = [
        ArxivPaper(
            id=1,
            title="Test Paper",
            abstract="Test abstract",
            authors=["Author"],
            url="https://arxiv.org/abs/2401.00001",
            paper_id="2401.00001",
            target_date="2024-01-01",
            sections=[],
            script="Speaker1: Hello.\nSpeaker2: Hi there.",
            status=ArxivPaperStatus.script_created,
        ),
    ]

    arxiv_paper_service.create_arxiv_paper.return_value = ArxivPaper(
        id=2,
        title="New Paper",
        abstract="New abstract",
        authors=["New Author"],
        url="https://arxiv.org/abs/2401.00002",
        paper_id="2401.00002",
        target_date="2024-01-01",
        sections=[],
        status=ArxivPaperStatus.initialized,
    )

    app.dependency_overrides[get_arxiv_paper_service] = lambda: arxiv_paper_service

    client = TestClient(app)
    yield client, arxiv_paper_service

    app.dependency_overrides.clear()


class TestStartScriptWriting:
    @patch.object(worker, "DailyPaperScraper")
    @patch.object(worker, "PodcastService")
    def test_start_script_writing_success(self, mock_podcast_service_class, mock_scraper_class, client_with_mock):
        client, arxiv_paper_service = client_with_mock

        mock_scraper_instance = MagicMock()
        mock_scraper_class.return_value = mock_scraper_instance
        mock_scraper_instance.get_papers_with_arxiv_ids.return_value = {"2401.00001", "2401.00002"}

        mock_podcast_service_instance = MagicMock()
        mock_podcast_service_class.return_value = mock_podcast_service_instance
        mock_podcast_service_instance.run = AsyncMock(return_value=None)

        response = client.post("/internal/api/v1/workers/start_script_writing/2024-01-01")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["message"] == "Script writing processing completed successfully"
        assert response_data["data"]["target_date"] == "2024-01-01"
        assert response_data["data"]["listed_paper_count"] == 2

        mock_scraper_instance.get_papers_with_arxiv_ids.assert_called_once()
        arxiv_paper_service.create_arxiv_paper.assert_called()

    @patch.object(worker, "DailyPaperScraper")
    @patch.object(worker, "PodcastService")
    def test_start_script_writing_no_papers(self, mock_podcast_service_class, mock_scraper_class, client_with_mock):
        client, arxiv_paper_service = client_with_mock

        mock_scraper_instance = MagicMock()
        mock_scraper_class.return_value = mock_scraper_instance
        mock_scraper_instance.get_papers_with_arxiv_ids.return_value = set()

        response = client.post("/internal/api/v1/workers/start_script_writing/2024-01-01")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["data"]["listed_paper_count"] == 0

        arxiv_paper_service.create_arxiv_paper.assert_not_called()


class TestStartTTS:
    @patch.object(worker, "TextToSpeechService")
    def test_start_tts_success(self, mock_tts_service_class, client_with_mock):
        client, arxiv_paper_service = client_with_mock

        mock_tts_service_instance = MagicMock()
        mock_tts_service_class.return_value = mock_tts_service_instance
        mock_tts_service_instance.generate_audio = AsyncMock(return_value=None)

        response = client.post("/internal/api/v1/workers/start_tts", params={"target_date": "2024-01-01"})

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["message"] == "TTS completed successfully"
        assert response_data["data"]["target_date"] == "2024-01-01"
        assert response_data["data"]["processed_paper_count"] == 1

        arxiv_paper_service.select_target_arxiv_papers.assert_called_once_with("2024-01-01")
        mock_tts_service_instance.generate_audio.assert_called_once()
        arxiv_paper_service.update_status.assert_called()

    @patch.object(worker, "TextToSpeechService")
    def test_start_tts_no_papers(self, mock_tts_service_class, client_with_mock):
        client, arxiv_paper_service = client_with_mock

        arxiv_paper_service.select_target_arxiv_papers.return_value = []

        mock_tts_service_instance = MagicMock()
        mock_tts_service_class.return_value = mock_tts_service_instance
        mock_tts_service_instance.generate_audio = AsyncMock(return_value=None)

        response = client.post("/internal/api/v1/workers/start_tts", params={"target_date": "2024-01-01"})

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["data"]["processed_paper_count"] == 0
