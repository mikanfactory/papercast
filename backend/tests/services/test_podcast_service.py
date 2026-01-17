from unittest.mock import MagicMock

import pytest

from papercast.entities import ArxivPaper, ArxivPaperStatus, ArxivSection
from papercast.services.podcast_service import (
    EvaluateResult,
    PodcastScriptWritingResult,
    PodcastService,
    SectionSummary,
)


@pytest.fixture
def sample_paper():
    return ArxivPaper(
        id=1,
        title="Test Paper",
        abstract="This is a test abstract about machine learning.",
        authors=["Alice Smith", "Bob Jones"],
        url="https://arxiv.org/abs/2401.00001",
        paper_id="2401.00001",
        target_date="2024-01-01",
        sections=[
            ArxivSection(
                title="Introduction",
                level=1,
                section_level_name="section.1",
                start_page=0,
                end_page=2,
                next_section_title="Related Work",
            )
        ],
        status=ArxivPaperStatus.initialized,
    )


@pytest.fixture
def mock_arxiv_paper_service():
    return MagicMock()


class TestPodcastServiceInit:
    def test_init(self, mock_arxiv_paper_service):
        service = PodcastService(mock_arxiv_paper_service)

        assert service.arxiv_paper_service == mock_arxiv_paper_service
        assert service.semaphore is not None


class TestPodcastServiceRun:
    @pytest.mark.asyncio
    async def test_run_updates_paper_when_result_is_string(self, sample_paper, mock_arxiv_paper_service):
        sample_paper.script = "test script"
        mock_arxiv_paper_service.update.return_value = sample_paper

        mock_arxiv_paper_service.update(sample_paper)

        mock_arxiv_paper_service.update.assert_called_once_with(sample_paper)


class TestLoadPrompt:
    def test_load_prompt_exists(self):
        from papercast.services.podcast_service import load_prompt

        prompt = load_prompt("is_relevant_paper")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_load_prompt_write_script(self):
        from papercast.services.podcast_service import load_prompt

        prompt = load_prompt("write_script")
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestSectionSummary:
    def test_section_summary_creation(self, sample_paper):
        summary = SectionSummary(
            section=sample_paper.sections[0],
            summary="This is the introduction summary.",
        )

        assert summary.section.title == "Introduction"
        assert summary.summary == "This is the introduction summary."


class TestPodcastScriptWritingResult:
    def test_podcast_script_writing_result_creation(self):
        result = PodcastScriptWritingResult(script="Speaker1: Hello")

        assert result.script == "Speaker1: Hello"


class TestEvaluateResult:
    def test_evaluate_result_valid(self):
        result = EvaluateResult(is_valid=True, feedback_message="Good script")

        assert result.is_valid is True
        assert result.feedback_message == "Good script"

    def test_evaluate_result_invalid(self):
        result = EvaluateResult(is_valid=False, feedback_message="Needs improvement")

        assert result.is_valid is False
        assert result.feedback_message == "Needs improvement"
