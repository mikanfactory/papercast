from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from papercast.entities import ArxivPaper, ArxivPaperStatus
from papercast.services.text_to_speach_service import TextToSpeechService


@pytest.fixture
def mock_arxiv_paper_service():
    return MagicMock()


@pytest.fixture
def sample_paper_with_script():
    return ArxivPaper(
        id=1,
        title="Test Paper",
        abstract="Test abstract",
        authors=["Author"],
        url="https://arxiv.org/abs/2401.00001",
        paper_id="2401.00001",
        target_date="2024-01-01",
        sections=[],
        script="Speaker1: Hello there.\nSpeaker2: Hello back.",
        status=ArxivPaperStatus.script_created,
    )


class TestSplitScript:
    def test_split_short_script(self):
        short_script = "Speaker1: Hello.\nSpeaker2: Hi there."
        chunks = TextToSpeechService.split_script(short_script)

        assert len(chunks) == 1
        assert chunks[0] == short_script

    def test_split_long_script(self):
        long_script = "Speaker1: " + "Hello world. " * 2000
        chunks = TextToSpeechService.split_script(long_script)

        assert all(isinstance(chunk, str) for chunk in chunks)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "Hello world" in chunk


class TestTextToSpeechService:
    @pytest.mark.asyncio
    async def test_invoke(self, mock_arxiv_paper_service):
        service = TextToSpeechService(mock_arxiv_paper_service)

        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[MagicMock(inline_data=MagicMock(data=b"audio data"))]))
        ]

        with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            result = await service._invoke("Speaker1: Hello")

            assert result == b"audio data"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate(self, mock_arxiv_paper_service, sample_paper_with_script):
        service = TextToSpeechService(mock_arxiv_paper_service)

        with (
            patch.object(service, "_invoke", new_callable=AsyncMock) as mock_invoke,
            patch("papercast.services.text_to_speach_service.TTSFileService") as mock_file_service,
        ):
            mock_invoke.return_value = b"audio data"
            mock_file_service.write.return_value = "/tmp/audio.wav"

            await service._generate(sample_paper_with_script, "Speaker1: Hello", 0)

            mock_invoke.assert_called_once_with("Speaker1: Hello")
            mock_file_service.write.assert_called_once_with(sample_paper_with_script.paper_id, 0, b"audio data")
            mock_file_service.upload_gcs_from_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_arxiv_paper_audio(self, mock_arxiv_paper_service, sample_paper_with_script):
        service = TextToSpeechService(mock_arxiv_paper_service)

        with (
            patch.object(service, "_generate", new_callable=AsyncMock) as mock_generate,
            patch.object(service, "split_script") as mock_split,
        ):
            mock_split.return_value = ["Speaker1: Hello", "Speaker2: Hi"]

            await service._generate_arxiv_paper_audio(sample_paper_with_script)

            assert mock_generate.call_count == 2
            mock_arxiv_paper_service.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_audio_skips_non_script_created(self, mock_arxiv_paper_service):
        service = TextToSpeechService(mock_arxiv_paper_service)

        paper = ArxivPaper(
            id=1,
            title="Test Paper",
            abstract="Test abstract",
            authors=["Author"],
            url="https://arxiv.org/abs/2401.00001",
            paper_id="2401.00001",
            target_date="2024-01-01",
            sections=[],
            script="Speaker1: Hello",
            status=ArxivPaperStatus.tts_completed,
        )

        with patch.object(service, "_generate_arxiv_paper_audio", new_callable=AsyncMock) as mock_generate:
            await service._generate_audio([paper])

            mock_generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_audio_processes_script_created(self, mock_arxiv_paper_service, sample_paper_with_script):
        service = TextToSpeechService(mock_arxiv_paper_service)

        with patch.object(service, "_generate_arxiv_paper_audio", new_callable=AsyncMock) as mock_generate:
            await service._generate_audio([sample_paper_with_script])

            mock_generate.assert_called_once_with(sample_paper_with_script)
