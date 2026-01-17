import pytest

from papercast.config import SUPABASE_LOCAL_API_KEY, SUPABASE_LOCAL_PROJECT_URL
from papercast.entities import ArxivPaper, ArxivPaperStatus, ArxivSection
from supabase import create_client


@pytest.fixture(scope="session")
def supabase_client():
    return create_client(SUPABASE_LOCAL_PROJECT_URL, SUPABASE_LOCAL_API_KEY)


@pytest.fixture(scope="session")
def cleanup_tables(supabase_client):
    yield
    try:
        supabase_client.table("arxiv_paper").delete().neq("id", 0).execute()
    except Exception:
        pass


@pytest.fixture
def sample_arxiv_section() -> ArxivSection:
    return ArxivSection(
        title="Introduction",
        level=1,
        section_level_name="section.1",
        start_page=0,
        end_page=2,
        next_section_title="Related Work",
    )


@pytest.fixture
def sample_arxiv_paper(sample_arxiv_section) -> ArxivPaper:
    return ArxivPaper(
        title="Test Paper: A Novel Approach",
        abstract="This paper presents a novel approach to testing.",
        authors=["Alice Smith", "Bob Jones"],
        url="https://arxiv.org/abs/2401.00001",
        paper_id="2401.00001",
        target_date="2024-01-01",
        sections=[sample_arxiv_section],
        script="",
        status=ArxivPaperStatus.initialized,
    )


@pytest.fixture(scope="session")
def initialized_paper(supabase_client) -> ArxivPaper:
    paper_result = (
        supabase_client.table("arxiv_paper")
        .insert(
            [
                {
                    "title": "Initialized Test Paper",
                    "abstract": "This is an abstract for testing.",
                    "authors": ["Test Author"],
                    "url": "https://arxiv.org/abs/2401.99901",
                    "paper_id": "2401.99901",
                    "target_date": "2024-01-01",
                    "sections": [],
                    "script": "",
                    "status": "initialized",
                },
            ]
        )
        .execute()
    )
    paper = ArxivPaper(**paper_result.data[0])
    yield paper


@pytest.fixture(scope="session")
def script_created_paper(supabase_client) -> ArxivPaper:
    paper_result = (
        supabase_client.table("arxiv_paper")
        .insert(
            [
                {
                    "title": "Script Created Test Paper",
                    "abstract": "This is an abstract for testing TTS.",
                    "authors": ["Test Author Two"],
                    "url": "https://arxiv.org/abs/2401.99902",
                    "paper_id": "2401.99902",
                    "target_date": "2024-01-02",
                    "sections": [],
                    "script": "Speaker1: Hello there.\nSpeaker2: Hello back.",
                    "status": "script_created",
                },
            ]
        )
        .execute()
    )
    paper = ArxivPaper(**paper_result.data[0])
    yield paper
